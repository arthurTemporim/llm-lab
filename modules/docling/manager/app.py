"""Docling manager: the front door of docling-serve.

Queues conversion requests, starts the docling-serve container (the worker) when there is work,
restarts it and retries the job when a conversion fails, and stops it when idle to free GPU VRAM.
Clients use the docling-serve API unchanged (sync and async convert, status poll, result).
"""

import asyncio
import logging
import os
import re
import secrets
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name) or default)


WORKER = "docling-worker"  # container name and host name on the lang network
WORKER_URL = f"http://{WORKER}:5001"
IDLE_TIMEOUT = env_int("DOCLING_MANAGER_IDLE_TIMEOUT", 30)
START_TIMEOUT = env_int("DOCLING_MANAGER_START_TIMEOUT", 300)
TASK_TIMEOUT = env_int("DOCLING_MANAGER_TASK_TIMEOUT", 1800)
MAX_RETRIES = env_int("DOCLING_MANAGER_MAX_RETRIES", 2)
CONCURRENCY = env_int("DOCLING_MANAGER_CONCURRENCY", 2)
SYNC_WAIT = env_int("DOCLING_MANAGER_SYNC_WAIT", 1800)
RESULT_TTL = env_int("DOCLING_MANAGER_RESULT_TTL", 3600)
API_KEY = os.environ.get("DOCLING_SERVE_API_KEY") or None
POLL_INTERVAL = 1
STOP_GRACE = 10  # seconds docker waits before killing the worker on stop/restart

# Requests that become jobs: convert or chunk, from an upload or a source, sync or async
JOB_PATH = re.compile(r"^/v1/(convert|chunk/[A-Za-z0-9_-]+)/(file|source)(/async)?$")
# Hop-by-hop headers, not forwarded by the proxy
HOP_HEADERS = {"host", "connection", "keep-alive", "transfer-encoding", "te", "upgrade", "content-length"}

logging.basicConfig(
    level=os.environ.get("DOCLING_MANAGER_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("docling-manager")
logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per request otherwise
spool = Path(tempfile.mkdtemp(prefix="docling-manager-"))


class WorkerError(Exception):
    """The worker failed (crash, unhealthy, task failure, timeout): restart it and retry."""


class Rejected(Exception):
    """The worker refused the request (4xx): retrying will not help."""

    def __init__(self, status: int, body: bytes, content_type: str):
        super().__init__(f"worker rejected the request with {status}")
        self.status, self.body, self.content_type = status, body, content_type


@dataclass
class Job:
    path: str  # worker async endpoint, with the query string
    content_type: str
    body: Path
    id: str
    status: str = "pending"  # pending | started | success | failure, like docling-serve
    created: float = field(default_factory=time.monotonic)
    finished: float | None = None
    result: Path | None = None
    result_type: str = "application/json"
    error: Rejected | str | None = None
    done: asyncio.Event = field(default_factory=asyncio.Event)

    def cleanup(self) -> None:
        for p in (self.body, self.result):
            if p:
                p.unlink(missing_ok=True)


class Worker:
    """Lifecycle of the docling-serve container, through the Docker Engine API."""

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        # Bumped on every (re)start. A job that fails restarts the worker only if nobody did
        # since its attempt began, so one crash seen by several jobs restarts it once.
        self.generation = 0
        self.ready = False
        self.busy = 0  # running jobs and proxied requests
        self.held = False  # POST /manager/start: never stop on idle
        self.last_activity = time.monotonic()

    async def _docker(self, action: str, **params) -> None:
        r = await docker.post(f"/containers/{WORKER}/{action}", params=params)
        if r.status_code not in (204, 304):  # 304: already in that state
            raise WorkerError(f"docker {action} {WORKER}: {r.status_code} {r.text.strip()}")

    async def state(self) -> str:
        r = await docker.get(f"/containers/{WORKER}/json")
        if r.status_code == 404:
            raise WorkerError(f"container {WORKER} not found: run `make docling`")
        r.raise_for_status()
        return r.json()["State"]["Status"]  # created | running | exited | restarting | ...

    async def ensure(self) -> int:
        """Start the worker if needed, wait until it is healthy, return its generation."""
        async with self.lock:
            if self.ready and await self.state() == "running":
                return self.generation
            self.ready = False
            log.info("starting %s", WORKER)
            await self._docker("start")
            self.generation += 1
            deadline = time.monotonic() + START_TIMEOUT
            while True:
                if await self.state() != "running":
                    raise WorkerError(f"{WORKER} exited while starting, see `docker logs {WORKER}`")
                try:
                    if (await worker_http.get("/health", timeout=5)).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() > deadline:
                    raise WorkerError(f"{WORKER} not healthy after {START_TIMEOUT}s")
                await asyncio.sleep(2)
            self.ready = True
            log.info("%s is ready (generation %d)", WORKER, self.generation)
            return self.generation

    async def restart(self, seen: int | None) -> None:
        """Restart the worker, unless it was restarted since generation `seen` (None: always)."""
        async with self.lock:
            if seen is not None and seen != self.generation:
                return
            log.warning("restarting %s", WORKER)
            self.ready = False
            await self._docker("restart", t=STOP_GRACE)
            self.generation += 1

    async def stop_if_idle(self, now: bool = False) -> None:
        def idle() -> bool:
            waited = now or time.monotonic() - self.last_activity >= IDLE_TIMEOUT
            return not self.held and not self.busy and not pending() and waited

        if not idle():
            return
        async with self.lock:
            if not idle():
                return
            if await self.state() != "running":
                self.ready = False
                return
            log.info("idle, stopping %s to free its memory", WORKER)
            self.ready = False
            await self._docker("stop", t=STOP_GRACE)


jobs: dict[str, Job] = {}
queue: asyncio.Queue[Job] = asyncio.Queue()
worker = Worker()
docker: httpx.AsyncClient
worker_http: httpx.AsyncClient


def describe(e: Exception) -> str:
    return str(e) or type(e).__name__  # httpx timeouts have no message


def pending() -> int:
    return sum(1 for j in jobs.values() if j.status == "pending")


def position(job: Job) -> int | None:
    if job.status != "pending":
        return None
    return sum(1 for j in jobs.values() if j.status == "pending" and j.created <= job.created)


async def attempt(job: Job) -> None:
    """Run the job once on the worker: submit, poll until done, save the result."""
    r = await worker_http.post(job.path, content=job.body.read_bytes(), headers={"content-type": job.content_type})
    if 400 <= r.status_code < 500:
        raise Rejected(r.status_code, r.content, r.headers.get("content-type", "application/json"))
    r.raise_for_status()
    task_id = r.json()["task_id"]
    deadline = time.monotonic() + TASK_TIMEOUT
    while True:
        s = await worker_http.get(f"/v1/status/poll/{task_id}")
        s.raise_for_status()
        status = s.json()["task_status"]
        if status == "success":
            break
        if status == "failure":
            raise WorkerError(f"task failed: {s.text.strip()}")
        if time.monotonic() > deadline:
            raise WorkerError(f"task still {status} after {TASK_TIMEOUT}s")
        await asyncio.sleep(POLL_INTERVAL)
    result = spool / f"{job.id}.result"
    async with worker_http.stream("GET", f"/v1/result/{task_id}") as res:
        res.raise_for_status()
        job.result_type = res.headers.get("content-type", job.result_type)
        with result.open("wb") as f:
            async for chunk in res.aiter_bytes():
                f.write(chunk)
    job.result = result


async def run(job: Job) -> None:
    failures = 0
    while True:
        gen = None
        try:
            gen = await worker.ensure()
            await attempt(job)
            job.status = "success"
            return
        except Rejected as e:
            job.status, job.error = "failure", e
            return
        except Exception as e:  # WorkerError, httpx errors, unexpected worker responses
            if gen is not None and gen != worker.generation:
                # Another job restarted the worker under this one: not this job's failure
                log.info("job %s: %s was restarted, retrying", job.id, WORKER)
                continue
            failures += 1
            log.warning("job %s: attempt %d failed: %s", job.id, failures, describe(e))
            if failures > MAX_RETRIES:
                job.status, job.error = "failure", f"failed after {failures} attempts: {describe(e)}"
                return
            try:
                await worker.restart(gen)
            except Exception as re_err:
                log.error("restart of %s failed: %s", WORKER, describe(re_err))


async def runner() -> None:
    while True:
        job = await queue.get()
        job.status = "started"
        worker.busy += 1
        try:
            await run(job)
        except Exception as e:  # never let a runner die
            job.status, job.error = "failure", str(e)
        finally:
            worker.busy -= 1
            worker.last_activity = time.monotonic()
            job.finished = time.monotonic()
            job.body.unlink(missing_ok=True)
            job.done.set()
            log.info("job %s: %s", job.id, job.status)


async def housekeeping() -> None:
    while True:
        await asyncio.sleep(5)
        try:
            await worker.stop_if_idle()
        except Exception as e:
            log.error("idle check failed: %s", e)
        for job in [j for j in jobs.values() if j.finished and time.monotonic() - j.finished > RESULT_TTL]:
            jobs.pop(job.id, None)
            job.cleanup()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global docker, worker_http
    docker = httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(uds="/var/run/docker.sock"),
        base_url="http://docker",
        timeout=STOP_GRACE + 60,
    )
    worker_http = httpx.AsyncClient(
        base_url=WORKER_URL,
        headers={"X-Api-Key": API_KEY} if API_KEY else {},
        timeout=httpx.Timeout(300, connect=5),
    )
    tasks = [asyncio.create_task(runner()) for _ in range(CONCURRENCY)]
    tasks.append(asyncio.create_task(housekeeping()))
    yield
    for t in tasks:
        t.cancel()
    await docker.aclose()
    await worker_http.aclose()


app = FastAPI(title="Docling manager", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


def check_key(request: Request) -> None:
    if API_KEY and not secrets.compare_digest(request.headers.get("x-api-key", ""), API_KEY):
        raise HTTPException(401, "invalid or missing X-Api-Key")


def task_json(job: Job) -> dict:
    data = {"task_id": job.id, "task_status": job.status, "task_position": position(job), "task_meta": None}
    if job.status == "failure":
        data["error"] = str(job.error)
    return data


def take_result(job: Job) -> Response:
    """Return the result once, like docling-serve, then forget the job."""
    jobs.pop(job.id, None)
    if isinstance(job.error, Rejected):
        job.cleanup()
        return Response(job.error.body, job.error.status, media_type=job.error.content_type)
    if job.status != "success":
        job.cleanup()
        return JSONResponse({"detail": str(job.error)}, 502)
    return FileResponse(job.result, media_type=job.result_type, background=BackgroundTask(job.cleanup))


def get_job(task_id: str) -> Job:
    if task_id not in jobs:
        raise HTTPException(404, f"task {task_id} not found")
    return jobs[task_id]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/manager/status")
async def status(request: Request):
    check_key(request)
    try:
        state = await worker.state()
    except Exception as e:
        state = f"unknown ({e})"
    return {
        "worker": state,
        "ready": worker.ready,
        "generation": worker.generation,
        "held": worker.held,
        "pending": pending(),
        "busy": worker.busy,
        "idle_seconds": round(time.monotonic() - worker.last_activity),
        "idle_timeout": IDLE_TIMEOUT,
    }


@app.post("/manager/start")
async def start(request: Request):
    check_key(request)
    worker.held = True
    try:
        await worker.ensure()
    except WorkerError as e:
        raise HTTPException(503, str(e))
    return await status(request)


@app.post("/manager/stop")
async def stop(request: Request):
    check_key(request)
    worker.held = False
    await worker.stop_if_idle(now=True)
    return await status(request)


@app.get("/v1/status/poll/{task_id}")
async def poll(task_id: str, request: Request, wait: float = 0):
    check_key(request)
    job = get_job(task_id)
    if wait > 0 and not job.done.is_set():
        try:
            await asyncio.wait_for(job.done.wait(), wait)
        except TimeoutError:
            pass
    return task_json(job)


@app.get("/v1/result/{task_id}")
async def result(task_id: str, request: Request):
    check_key(request)
    job = get_job(task_id)
    if not job.done.is_set():
        raise HTTPException(404, f"task {task_id} is still {job.status}")
    return take_result(job)


@app.post("/v1/{rest:path}")
async def submit(rest: str, request: Request):
    match = JOB_PATH.match(request.url.path)
    if not match:
        return await proxy(request)
    check_key(request)
    path = request.url.path if match[3] else request.url.path + "/async"
    if request.url.query:
        path += "?" + request.url.query
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        path=path,
        content_type=request.headers.get("content-type", "application/json"),
        body=spool / f"{job_id}.body",
    )
    with job.body.open("wb") as f:
        async for chunk in request.stream():
            f.write(chunk)
    jobs[job.id] = job
    await queue.put(job)
    log.info("job %s queued: %s", job.id, request.url.path)
    if match[3]:
        return task_json(job)
    try:
        await asyncio.wait_for(job.done.wait(), SYNC_WAIT)
    except TimeoutError:
        raise HTTPException(504, f"task {job.id} not done after {SYNC_WAIT}s, poll it with /v1/status/poll/{job.id}")
    return take_result(job)


@app.api_route("/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy(request: Request):
    """Everything else (UI, OpenAPI docs, capabilities...) goes to the worker, started on demand."""
    worker.busy += 1

    def release() -> None:
        worker.busy -= 1
        worker.last_activity = time.monotonic()

    try:
        await worker.ensure()
        req = worker_http.build_request(
            request.method,
            request.url.path,
            params=request.query_params,
            headers={k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS},
            content=await request.body(),
        )
        res = await worker_http.send(req, stream=True)
    except (WorkerError, httpx.HTTPError) as e:
        release()
        return JSONResponse({"detail": f"docling worker unavailable: {e}"}, 503)

    async def body():
        # finally also runs when the client disconnects, so busy never leaks
        try:
            async for chunk in res.aiter_raw():
                yield chunk
        finally:
            await res.aclose()
            release()

    headers = {k: v for k, v in res.headers.items() if k.lower() not in HOP_HEADERS - {"content-length"}}
    return StreamingResponse(body(), res.status_code, headers=headers)

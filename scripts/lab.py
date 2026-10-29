#!/usr/bin/env python3
"""Sets up llm-lab: env files, public host, GPU ids, evals env, module start and Hatchet token.

Wraps the Makefile and the scripts/*.sh helpers; run again at any time (it is idempotent).
Python 3.9+, standard library only.

Ex: ./scripts/lab.py init                          # env files + common-services + ollama + models
    ./scripts/lab.py init --modules all            # every module
    ./scripts/lab.py init --modules litellm,hatchet --host 192.168.15.102
    ./scripts/lab.py configure                     # env files only, nothing is started
    ./scripts/lab.py gpu --dry-run                 # show the GPUs and the card vLLM/Docling would use
    ./scripts/lab.py hatchet-token --force         # new worker token (after changing LAB_PUBLIC_HOST)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = ROOT / "modules"
SCRIPTS_DIR = ROOT / "scripts"
GLOBAL_ENV = MODULES_DIR / "common-services" / ".env"
EVALS_DIR = ROOT / "evals"

# vLLM and Docling's CUDA 12.8 image need compute capability 7.5+ (no Pascal cards like the Tesla P4)
GPU_MIN_COMPUTE = 7.5
GPU_ID_VARS = {"vllm": "VLLM_GPU_ID", "docling": "DOCLING_GPU_ID"}

# Summary: module -> (port variable, URL path, login variables in the module .env or a note)
SUMMARY = {
    "openwebui": ("OPENWEBUI_PORT", "", ("WEBUI_ADMIN_EMAIL", "WEBUI_ADMIN_PASSWORD")),
    "litellm": ("LITELLM_PORT", "/ui", ("UI_USERNAME", "UI_PASSWORD")),
    "langfuse": ("LANGFUSE_PORT", "", ("LANGFUSE_INIT_USER_EMAIL", "LANGFUSE_INIT_USER_PASSWORD")),
    "langflow": ("LANGFLOW_PORT", "", ("LANGFLOW_SUPERUSER", "LANGFLOW_SUPERUSER_PASSWORD")),
    "hatchet": ("HATCHET_PORT", "", ("ADMIN_EMAIL", "ADMIN_PASSWORD")),
    "notebooks": ("NOTEBOOKS_PORT", "", "no login"),
    "docling": ("DOCLING_PORT", "/ui", "no login"),
    "ollama": ("OLLAMA_PORT", "", "API, no login"),
    "localai": ("LOCALAI_PORT", "", ("LOCALAI_API_KEY",)),
    "vllm": ("VLLM_HOST_PORT", "", ("VLLM_API_KEY",)),
}


def log(msg: str) -> None:
    print(f"[lab] {msg}", flush=True)


def fail(msg: str, code: int = 1) -> None:
    print(f"[lab] error: {msg}", file=sys.stderr)
    sys.exit(code)


# =================== env files ===================
def read_env(path: Path) -> dict[str, str]:
    """Raw KEY=value pairs (no ${VAR} expansion), last one wins like docker compose."""
    values: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
            if m:
                values[m.group(1)] = m.group(2)
    return values


def set_env(path: Path, key: str, value: str) -> bool:
    """Sets KEY=value in place (comments and order kept), appends it if missing. True if changed."""
    lines = path.read_text().splitlines()
    new = f"{key}={value}"
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            if line == new:
                return False
            lines[i] = new
            break
    else:
        lines.append(new)
    path.write_text("\n".join(lines) + "\n")
    return True


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


# =================== commands ===================
def run(cmd: list[str]) -> None:
    """Runs a command with live output; stops the whole run when it fails."""
    print("+ " + " ".join(cmd), flush=True)
    code = subprocess.run(cmd, cwd=ROOT).returncode
    if code != 0:
        fail(f"'{' '.join(cmd)}' failed", code)


def make(target: str, gpu: str | None = None) -> None:
    run(["make", "--no-print-directory", "-C", str(ROOT), target] + ([f"GPU={gpu}"] if gpu else []))


def make_var(name: str) -> list[str]:
    """Value of a Makefile variable (MODULES, CORE), the way CI reads it."""
    out = subprocess.run(
        ["make", "-s", "--no-print-directory", "-C", str(ROOT), "--eval", f"print-var: ; @echo $({name})", "print-var"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.split()


# =================== steps ===================
def detect_lan_ip() -> str:
    """IP of the interface on the default route (a UDP connect sends nothing)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 80))
            ip = s.getsockname()[0]
    except OSError:
        return "localhost"
    return "localhost" if ip.startswith("127.") else ip


def query_gpus() -> list[dict] | None:
    """GPUs as listed by nvidia-smi (same indexes Docker's device_ids use), None without nvidia-smi."""
    if not shutil.which("nvidia-smi"):
        return None
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,name,compute_cap,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        log(f"nvidia-smi failed (old driver without compute_cap?): {out.stdout.strip() or out.stderr.strip()}")
        return None
    gpus = []
    for line in out.stdout.strip().splitlines():
        index, name, cap, mem = [p.strip() for p in line.split(",")]
        try:
            compute = float(cap)
        except ValueError:
            compute = 0.0
        gpus.append({"index": index, "name": name, "compute": compute, "memory": int(float(mem))})
    return gpus


def pick_gpu(gpus: list[dict]) -> dict | None:
    eligible = [g for g in gpus if g["compute"] >= GPU_MIN_COMPUTE]
    # Most memory first, lowest index on ties
    return min(eligible, key=lambda g: (-g["memory"], int(g["index"]))) if eligible else None


def apply_gpu(modules: list[str], dry_run: bool = False) -> None:
    gpus = query_gpus()
    if not gpus:
        log("gpu: no NVIDIA GPU found (nvidia-smi missing or failed); GPU ids left unchanged")
        return
    best = pick_gpu(gpus)
    for g in gpus:
        mark = "  <- vllm, docling" if g is best else ""
        print(f"  {g['index']}: {g['name']}  compute {g['compute']}  {g['memory']} MiB{mark}")
    if best is None:
        log(f"gpu: no card with compute capability >= {GPU_MIN_COMPUTE}; GPU ids left unchanged")
        return
    for m in modules:
        env = MODULES_DIR / m / ".env"
        if not env.is_file():
            continue
        if dry_run:
            log(f"gpu: would set {GPU_ID_VARS[m]}={best['index']} in {rel(env)}")
        elif set_env(env, GPU_ID_VARS[m], best["index"]):
            log(f"gpu: {GPU_ID_VARS[m]}={best['index']} in {rel(env)}")


def sync_evals() -> None:
    """evals/.env from its example, with the LiteLLM master key (create-envs does not cover evals/)."""
    env, example = EVALS_DIR / ".env", EVALS_DIR / "example.env"
    litellm = read_env(MODULES_DIR / "litellm" / ".env")
    if not env.is_file():
        shutil.copyfile(example, env)
        set_env(env, "LITELLM_BASE_URL", f"http://localhost:{litellm.get('LITELLM_PORT', '4000')}")
        log(f"evals: created {rel(env)}")
    key = litellm.get("LITELLM_MASTER_KEY", "")
    if key and "CHANGE_ME" not in key and set_env(env, "LITELLM_API_KEY", key):
        log("evals: LITELLM_API_KEY set to LITELLM_MASTER_KEY")


def add_missing_vars(module: str) -> list[str]:
    """Appends the variables of example.env that an older .env lacks (create-envs never touches an
    existing file), then fills their CHANGE_ME* placeholders. Returns the added names."""
    env, example = MODULES_DIR / module / ".env", MODULES_DIR / module / "example.env"
    have = read_env(env)
    added = [line for line in example.read_text().splitlines()
             if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", line) and line.split("=", 1)[0] not in have]
    if not added:
        return []
    with env.open("a") as f:
        f.write("\n# Added by `make configure` from example.env\n" + "\n".join(added) + "\n")
    if any("CHANGE_ME" in line for line in added):
        run([str(SCRIPTS_DIR / "generate_secrets.sh"), str(env)])
    names = [line.split("=", 1)[0] for line in added]
    log(f"{rel(env)}: added {' '.join(names)}")
    return names


def configure(modules: list[str], host: str | None) -> None:
    missing = {m for m in modules if (MODULES_DIR / m / "example.env").is_file() and not (MODULES_DIR / m / ".env").is_file()}
    make("create-envs")
    added = {m: add_missing_vars(m) for m in modules if m not in missing and (MODULES_DIR / m / "example.env").is_file()}

    # Only on a new global env (or when asked): never overwrite a host chosen by hand
    if host or "common-services" in missing or "LAB_PUBLIC_HOST" in added.get("common-services", []):
        public = host or detect_lan_ip()
        if set_env(GLOBAL_ENV, "LAB_PUBLIC_HOST", public):
            log(f"LAB_PUBLIC_HOST={public} in {rel(GLOBAL_ENV)}")

    new_gpu_modules = [m for m in GPU_ID_VARS if m in missing]
    if new_gpu_modules:
        apply_gpu(new_gpu_modules)

    sync_evals()


def wait_until(check, what: str, timeout: int) -> None:
    deadline = time.time() + timeout
    while not check():
        if time.time() > deadline:
            fail(f"timed out after {timeout}s waiting for {what}")
        time.sleep(5)


def ollama_ready() -> bool:
    port = read_env(MODULES_DIR / "ollama" / ".env").get("OLLAMA_PORT", "11434")
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/version", timeout=5) as r:
            return r.status == 200
    except OSError:
        return False


def container_health(name: str) -> str:
    out = subprocess.run(
        ["docker", "inspect", "--format", "{{json .State.Health.Status}}", name], capture_output=True, text=True
    )
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else ""


def hatchet_token(force: bool, timeout: int = 300) -> None:
    if read_env(GLOBAL_ENV).get("HATCHET_CLIENT_TOKEN") and not force:
        log("hatchet: HATCHET_CLIENT_TOKEN already set (--force to replace it)")
        return
    log("hatchet: waiting for hatchet-lite to be healthy")
    wait_until(lambda: container_health("hatchet-lite") == "healthy", "hatchet-lite", timeout)
    # The default tenant is seeded right after the first start: retry until it exists
    token = ""
    deadline = time.time() + 60
    while not token:
        out = subprocess.run([str(SCRIPTS_DIR / "hatchet_token.sh")], capture_output=True, text=True)
        token = out.stdout.strip() if out.returncode == 0 else ""
        if not token:
            if time.time() > deadline:
                fail(f"hatchet token creation failed: {out.stderr.strip()}")
            time.sleep(5)
    set_env(GLOBAL_ENV, "HATCHET_CLIENT_TOKEN", token)
    log(f"hatchet: HATCHET_CLIENT_TOKEN written to {rel(GLOBAL_ENV)}")


def summary(selected: list[str]) -> None:
    global_env = read_env(GLOBAL_ENV)
    host = global_env.get("LAB_PUBLIC_HOST", "localhost")
    print(f"\nDefault login: {global_env.get('LAB_USER', '?')} / {global_env.get('LAB_EMAIL', '?')} "
          "(LAB_USER / LAB_EMAIL); each module has its own password")
    print("Services:")
    for m in selected:
        if m not in SUMMARY:
            continue
        port_var, path, login = SUMMARY[m]
        env_path = MODULES_DIR / m / ".env"
        port = read_env(env_path).get(port_var, "?")
        if isinstance(login, tuple):
            login = f"{', '.join(login)} in {rel(env_path)}"
        print(f"  {m:<10} http://{host}:{port}{path}  ({login})")
    if "hatchet" in selected:
        print(f"  Hatchet workers: HATCHET_CLIENT_* in {rel(GLOBAL_ENV)} "
              f"(outside Docker use HATCHET_CLIENT_HOST_PORT={host}:<HATCHET_GRPC_PORT>)")
    print(f"  evals: {rel(EVALS_DIR / '.env')} is ready (see evals/README.md)")


def select_modules(arg: str, all_modules: list[str], core: list[str]) -> list[str]:
    if arg == "core":
        wanted = set(core)
    elif arg == "all":
        wanted = set(all_modules)
    else:
        wanted = {m.strip() for m in arg.split(",") if m.strip()}
        unknown = wanted - set(all_modules)
        if unknown:
            fail(f"unknown modules: {', '.join(sorted(unknown))} (known: {' '.join(all_modules)})")
    wanted.add("common-services")
    return [m for m in all_modules if m in wanted]


def init(args: argparse.Namespace) -> None:
    all_modules, core = make_var("MODULES"), make_var("CORE")
    selected = select_modules(args.modules, all_modules, core)
    log(f"modules: {' '.join(selected)}")

    configure(all_modules, args.host)
    make("up-common-services", args.gpu)

    # Models first: litellm-init builds its config from the models Ollama has when it starts
    if "ollama" in selected:
        make("up-ollama", args.gpu)
        if not args.no_pull:
            wait_until(ollama_ready, "ollama", 120)
            run([str(SCRIPTS_DIR / "ollama_pull_model.sh")])

    for m in selected:
        if m not in ("common-services", "ollama"):
            make(f"up-{m}", args.gpu)

    if "hatchet" in selected:
        hatchet_token(force=False)

    summary(selected)
    log("init done")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="configure, start modules, pull models, create the Hatchet token")
    p.add_argument("--modules", default="core", help="core (default), all, or a comma-separated list")
    p.add_argument("--host", help="LAB_PUBLIC_HOST (default: detected LAN IP on a new env)")
    p.add_argument("--no-pull", action="store_true", help="skip scripts/ollama_pull_model.sh")
    p.add_argument("--gpu", choices=["0", "1"], help="force GPU=0/1 (default: Makefile auto-detection)")

    p = sub.add_parser("configure", help="create and fill the env files; starts nothing")
    p.add_argument("--host", help="set LAB_PUBLIC_HOST (default: detected LAN IP on a new env only)")

    p = sub.add_parser("gpu", help="pick the GPU for vLLM and Docling and write their GPU ids")
    p.add_argument("--dry-run", action="store_true", help="only show the GPUs and the choice")

    p = sub.add_parser("hatchet-token", help="create a Hatchet worker token in the global env")
    p.add_argument("--force", action="store_true", help="replace an existing token")

    args = parser.parse_args()
    if args.command == "init":
        init(args)
    elif args.command == "configure":
        configure(make_var("MODULES"), args.host)
    elif args.command == "gpu":
        apply_gpu(list(GPU_ID_VARS), args.dry_run)
    elif args.command == "hatchet-token":
        hatchet_token(args.force)


if __name__ == "__main__":
    main()

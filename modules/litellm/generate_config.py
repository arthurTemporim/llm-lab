"""Build the LiteLLM config.yaml from the models Ollama has, plus models.yaml.

Runs in the one-shot `litellm-init` service before `litellm` starts:

1. Lists the models pulled in Ollama (/api/tags).
2. Reads each model's capabilities and context length (/api/show) to pick the
   mode (chat or embedding) and fill model_info.
3. Applies the per-mode `defaults` and the per-model `models` overrides from
   models.yaml, then appends `extra_models` and the *_settings sections.
4. Writes the result atomically to CONFIG_PATH.

If Ollama is unreachable the last generated config is kept, so LiteLLM still
starts. Only the Python standard library and PyYAML (both in the LiteLLM image)
are used.
"""

import copy
import json
import os
import sys
import time
import urllib.request

import yaml

OLLAMA_API_BASE = os.environ.get("OLLAMA_API_BASE", "http://ollama:11434").rstrip("/")
OLLAMA_WAIT_SECONDS = int(os.environ.get("OLLAMA_WAIT_SECONDS", "60"))
MODELS_PATH = os.environ.get("LITELLM_MODELS_PATH", "/opt/llm-lab/models.yaml")
CONFIG_PATH = os.environ.get("LITELLM_CONFIG_PATH", "/config/config.yaml")

SETTINGS_SECTIONS = ("litellm_settings", "general_settings", "router_settings", "environment_variables")


def log(msg):
    print(f"[litellm-init] {msg}", flush=True)


def ollama(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{OLLAMA_API_BASE}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def wait_for_ollama():
    deadline = time.monotonic() + OLLAMA_WAIT_SECONDS
    while True:
        try:
            return [m["name"] for m in ollama("/api/tags").get("models", [])]
        except Exception as exc:
            if time.monotonic() >= deadline:
                log(f"Ollama not reachable at {OLLAMA_API_BASE} after {OLLAMA_WAIT_SECONDS}s: {exc}")
                return None
            time.sleep(3)


def deep_merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def with_tag(name):
    return name if ":" in name else f"{name}:latest"


def arch_value(model_info, suffix):
    for key, value in model_info.items():
        if key.endswith(f".{suffix}"):
            return value
    return None


def build_entry(name, show, defaults, override):
    caps = set(show.get("capabilities") or [])
    info = show.get("model_info") or {}
    ctx = arch_value(info, "context_length")

    mode = (override.get("model_info") or {}).get("mode")
    if not mode:
        mode = "embedding" if "embedding" in caps else "chat"
    mode_defaults = defaults.get(mode, {})
    provider = mode_defaults.get("provider", "ollama_chat" if mode == "chat" else "ollama")

    entry = {
        "model_name": name,
        "litellm_params": deep_merge(deep_merge(
            {"model": f"{provider}/{name}", "api_base": OLLAMA_API_BASE},
            mode_defaults.get("litellm_params"),
        ), override.get("litellm_params")),
        "model_info": {"mode": mode},
    }
    params, model_info = entry["litellm_params"], entry["model_info"]

    if mode == "chat":
        # num_ctx is what Ollama allocates; never ask for more than the model has.
        if ctx and params.get("num_ctx", 0) > ctx:
            params["num_ctx"] = ctx
        if params.get("num_ctx") or ctx:
            model_info["max_input_tokens"] = params.get("num_ctx") or ctx
        if params.get("max_tokens"):
            model_info["max_output_tokens"] = params["max_tokens"]
        for cap, flag in (("vision", "supports_vision"), ("tools", "supports_function_calling"),
                          ("thinking", "supports_reasoning")):
            if cap in caps:
                model_info[flag] = True
    elif mode == "embedding":
        if ctx:
            model_info["max_input_tokens"] = ctx
        dims = arch_value(info, "embedding_length")
        if dims:
            model_info["output_vector_size"] = dims

    entry = deep_merge(entry, {k: v for k, v in override.items() if k not in ("enabled", "litellm_params")})
    return entry, caps


def main():
    with open(MODELS_PATH) as f:
        spec = yaml.safe_load(f) or {}
    defaults = spec.get("defaults") or {}
    overrides = {with_tag(k): (v or {}) for k, v in (spec.get("models") or {}).items()}

    names = wait_for_ollama()
    if names is None:
        if os.path.exists(CONFIG_PATH):
            log(f"Keeping the last generated {CONFIG_PATH}")
            return
        log("No previous config: starting LiteLLM with extra_models only")
        names = []

    model_list = []
    for name in sorted(names):
        override = overrides.get(name, {})
        if override.get("enabled") is False:
            log(f"skip  {name} (enabled: false)")
            continue
        try:
            show = ollama("/api/show", {"model": name})
        except Exception as exc:
            log(f"skip  {name} (/api/show failed: {exc})")
            continue
        entry, caps = build_entry(name, show, defaults, override)
        model_list.append(entry)
        log(f"add   {name} -> {entry['litellm_params']['model']} "
            f"(mode={entry['model_info']['mode']}, caps={','.join(sorted(caps)) or '-'})")

    for name in sorted(set(overrides) - set(names)):
        if overrides[name].get("enabled") is not False:
            log(f"miss  {name} is in models.yaml but not pulled in Ollama")

    extra = spec.get("extra_models") or []
    model_list.extend(extra)

    config = {"model_list": model_list}
    for section in SETTINGS_SECTIONS:
        if spec.get(section):
            config[section] = spec[section]

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp = f"{CONFIG_PATH}.tmp"
    with open(tmp, "w") as f:
        f.write("# Generated by generate_config.py from Ollama and models.yaml. Do not edit.\n")
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
    os.replace(tmp, CONFIG_PATH)
    log(f"Wrote {CONFIG_PATH}: {len(model_list) - len(extra)} Ollama models, {len(extra)} extra")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"ERROR: {exc}")
        sys.exit(1)

from typing import Any, Dict, List
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 1: hardcoded defaults
DEFAULTS: Dict[str, Any] = {
    "port": 8000, "workers": 1, "debug": False,
    "log_level": "info", "api_key": "default-secret-000",
}

# Layer 2: config.development.yaml
YAML_LAYER: Dict[str, Any] = {"port": 8093, "log_level": "debug"}

# Layer 3: .env file (raw contents, parsed below)
DOTENV_TEXT = """
APP_PORT=8697
NUM_WORKERS=5
APP_LOG_LEVEL=debug
APP_API_KEY=key-u55c3n85x3
"""

# Layer 4: OS env vars (APP_* prefix)
OS_ENV: Dict[str, str] = {
    "APP_PORT": "8109",
    "APP_WORKERS": "2",
    "APP_DEBUG": "false",
    "APP_LOG_LEVEL": "debug",
}

ALIASES = {"NUM_WORKERS": "workers"}
INT_KEYS = {"port", "workers"}
BOOL_KEYS = {"debug"}


def coerce(key: str, value: Any) -> Any:
    if key in INT_KEYS:
        return int(value)
    if key in BOOL_KEYS:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "on"}
    return str(value)


def parse_env_layer(items: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in items.items():
        if k in ALIASES:
            key = ALIASES[k]
        elif k.startswith("APP_"):
            key = k[4:].lower()
        else:
            continue
        out[key] = coerce(key, v)
    return out


def parse_dotenv(text: str) -> Dict[str, str]:
    d = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d


@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    cfg: Dict[str, Any] = dict(DEFAULTS)
    for key, val in YAML_LAYER.items():
        cfg[key] = coerce(key, val)
    cfg.update(parse_env_layer(parse_dotenv(DOTENV_TEXT)))
    cfg.update(parse_env_layer(OS_ENV))

    # CLI overrides (highest precedence)
    for item in set:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        k = k.strip().lower()
        try:
            cfg[k] = coerce(k, v.strip())
        except ValueError:
            pass  # ignore un-coercible ints

    cfg["api_key"] = "****"
    return cfg
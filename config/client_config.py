import json
import os

CONFIG_FILE = "config/client_settings.json"

# Client-configurable keys — entered via the Settings UI
CLIENT_KEYS = {
    "anthropic_api_key": "",
    "openai_api_key": "",
    "elevenlabs_api_key": "",
    "elevenlabs_voice_id_male": "",
    "elevenlabs_voice_id_female": "",
    "fish_audio_api_key": "",
    "grok_api_key": "",
    "google_ai_studio_api_key": "",
    "higgsfield_api_key": "",
    "apify_api_token": "",
    "brave_search_api_key": "",
    "deepgram_api_key": "",
}

def _load() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data: dict):
    os.makedirs("config", exist_ok=True)
    existing = _load()
    existing.update({k: v for k, v in data.items() if k in CLIENT_KEYS and v != ""})
    with open(CONFIG_FILE, "w") as f:
        json.dump(existing, f, indent=2)

def get_key(key: str) -> str:
    """Priority: client settings file → .env fallback."""
    stored = _load()
    return stored.get(key) or os.getenv(key.upper(), "")

def get_config_status() -> dict:
    """Which client keys are set — for the settings UI."""
    stored = _load()
    status = {}
    for key in CLIENT_KEYS:
        val = stored.get(key) or os.getenv(key.upper(), "")
        status[key] = {
            "set": bool(val),
            "value": ("*" * 8 + val[-4:]) if val and len(val) > 4 else ("" if not val else val)
        }
    return status

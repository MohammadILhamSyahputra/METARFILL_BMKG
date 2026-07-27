import os
import json
import hashlib

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0"
)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "database_metar.db")


def build_auth_config(auth_state_path: str, user_agent: str | None = None) -> dict:
    with open(auth_state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    access_token = None
    for origin in state.get("origins", []):
        for item in origin.get("localStorage", []):
            if item.get("name") == "accessToken":
                access_token = item.get("value")
                break
        if access_token:
            break

    if not access_token:
        raise Exception(
            f"accessToken tidak ditemukan di '{auth_state_path}'. "
            "Pastikan proses login sudah selesai sebelum menyimpan sesi."
        )

    cookie_str = "; ".join(
        f"{c['name']}={c['value']}" for c in state.get("cookies", [])
    )

    return {
        "bearer_token": access_token,
        "cookie": cookie_str,
        "user_agent": user_agent or DEFAULT_USER_AGENT,
    }


def save_auth_config(auth_state_path: str, config_path: str, user_agent: str | None = None) -> dict:
    config = build_auth_config(auth_state_path, user_agent=user_agent)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return config
from pathlib import Path
import os

DEFAULT_BACKEND_PORT = 18457


def get_data_dir() -> Path:
    override = os.getenv("SMART_MOVE_DATA_DIR")
    data_dir = Path(override).expanduser() if override else Path.cwd()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_env_file() -> Path:
    override = os.getenv("SMART_MOVE_ENV_PATH")
    return Path(override).expanduser() if override else Path(".env")


def get_database_url() -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured

    db_path = get_data_dir() / "smart_move.db"
    return f"sqlite:///{db_path.resolve().as_posix()}"


def get_backend_port() -> int:
    return int(os.getenv("SMART_MOVE_BACKEND_PORT", str(DEFAULT_BACKEND_PORT)))

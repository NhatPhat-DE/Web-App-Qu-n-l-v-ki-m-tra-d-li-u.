import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve from this file, independently of the working directory.
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE, override=False)


def get_database_url() -> str | None:
    return os.getenv("DATABASE_URL")

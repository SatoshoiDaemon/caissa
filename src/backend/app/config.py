import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = PROJECT_ROOT / "src" / "frontend"


@dataclass(frozen=True)
class Settings:
    secret_key: str
    mongo_uri: str
    mongo_database: str
    redis_url: str
    host: str
    port: int
    debug: bool
    environment: str
    allowed_origins: list[str]
    max_content_length: int = 16 * 1024
    testing: bool = False
    template_folder: str = str(FRONTEND_ROOT / "templates")
    static_folder: str = str(FRONTEND_ROOT / "static")

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        environment = os.getenv("ENVIRONMENT", "development").lower()
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            raise RuntimeError("SECRET_KEY must be configured in the environment")
        origins = [
            item.strip()
            for item in os.getenv(
                "ALLOWED_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000"
            ).split(",")
            if item.strip()
        ]
        return cls(
            secret_key=secret_key,
            mongo_uri=os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"),
            mongo_database=os.getenv("MONGO_DATABASE", "chess_web"),
            redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            environment=environment,
            allowed_origins=origins,
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", str(16 * 1024))),
        )

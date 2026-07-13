from pathlib import Path
from pydantic_settings import BaseSettings

# Repo layout: <repo>/ai-report-forge/ai_report_forge/config.py
# Anchor relative artifact paths to the ai-report-forge directory so the
# service loads its Phase 1 artifacts regardless of the working directory
# uvicorn was started from.
_BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: int = 60

    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-8"
    claude_max_tokens: int = 4096

    report_thoughts_path: Path = Path("../ReportThoughts")
    html_reports_path: Path = Path("../HTMLReportsFolder")
    schema_mapping_path: Path = Path("../DataSchemaMapping/schema-mapping.json")
    phi_markers_path: Path = Path("../DataSchemaMapping/phi-markers.json")

    # Bind to loopback by default; this service has no auth and handles PHI.
    brain_host: str = "127.0.0.1"
    brain_port: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def resolve(self, path: Path) -> Path:
        """Resolve a configured artifact path against the package base dir."""
        return path if path.is_absolute() else (_BASE_DIR / path).resolve()


settings = Settings()

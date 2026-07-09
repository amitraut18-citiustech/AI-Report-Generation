from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:3b"
    ollama_timeout: int = 60

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    report_thoughts_path: Path = Path("../ReportThoughts")
    html_reports_path: Path = Path("../HTMLReportsFolder")
    schema_mapping_path: Path = Path("../DataSchemaMapping/schema-mapping.json")
    phi_markers_path: Path = Path("../DataSchemaMapping/phi-markers.json")

    brain_host: str = "0.0.0.0"
    brain_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

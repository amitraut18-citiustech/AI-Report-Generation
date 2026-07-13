import os

os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:3b")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("REPORT_THOUGHTS_PATH", "../ReportThoughts")
os.environ.setdefault("SCHEMA_MAPPING_PATH", "../DataSchemaMapping/schema-mapping.json")
os.environ.setdefault("PHI_MARKERS_PATH", "../DataSchemaMapping/phi-markers.json")

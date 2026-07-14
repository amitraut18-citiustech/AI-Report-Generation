import logging
import math
from contextlib import asynccontextmanager

from ollama import Client as OllamaClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from . import prompt_log
from .claude_fallback import summarize_with_claude
from .config import settings
from .context_loader import AppContext, load_context
from .prompt_decoder import decode_prompt
from .summarizer import summarize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

_ctx: AppContext | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ctx
    log.info("Loading Phase 1 artifacts...")
    _ctx = load_context()
    log.info(
        "Ready — %d reports, %d schema tables, %d PHI markers",
        len(_ctx.reports),
        len(_ctx.schema.tables),
        len(_ctx.phi.columns),
    )
    yield


app = FastAPI(title="AI Report Forge — Brain Service", lifespan=lifespan)


def _get_ctx() -> AppContext:
    if _ctx is None:
        raise HTTPException(status_code=503, detail="Context not loaded")
    return _ctx


class DecodeRequest(BaseModel):
    question: str = Field(..., min_length=1)
    provider: str = Field(
        default="local",
        pattern="^(local|claude)$",
        description="'local' decodes via Ollama (with Claude fallback if configured); 'claude' goes straight to the Claude API",
    )


class QueryFilter(BaseModel):
    table: str
    field: str
    operator: str = "equals"
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_str(cls, v):
        if not isinstance(v, str):
            return str(v)
        return v


class JoinSpec(BaseModel):
    table: str
    localKey: str
    foreignKey: str = "Id"


class QuerySpecModel(BaseModel):
    entity: str = ""
    joins: list[JoinSpec] = []
    filters: list[QueryFilter] = []


class DecodeResponse(BaseModel):
    report: str
    query: QuerySpecModel = QuerySpecModel()
    parameters: dict
    template: str | None = None
    confidence: float = 0.0
    message: str | None = None
    source: str | None = None


class SummarizeRequest(BaseModel):
    question: str = Field(..., min_length=1)
    results: list[dict]
    row_count: int = Field(..., ge=0)
    table: str = Field(default="Patients", description="Primary table name for PHI anonymization lookup")


class ChartSpec(BaseModel):
    type: str = "bar"
    title: str = ""
    labels: list[str] = []
    values: list[float | int] = []

    @model_validator(mode="after")
    def validate_chart(self):
        # The chart spec comes from an LLM; reject shapes the frontend
        # cannot render sensibly instead of passing them through.
        if self.type not in ("bar", "pie", "line"):
            raise ValueError(f"unsupported chart type: {self.type}")
        if len(self.labels) != len(self.values):
            raise ValueError("labels/values length mismatch")
        if not (1 <= len(self.labels) <= 12):
            raise ValueError("chart must have 1-12 categories")
        if any(not math.isfinite(float(v)) for v in self.values):
            raise ValueError("chart values must be finite numbers")
        self.title = self.title[:120]
        self.labels = [str(l)[:80] for l in self.labels]
        return self


class SummarizeResponse(BaseModel):
    summary: str
    source: str
    anonymized: bool = False
    chart: ChartSpec | None = None


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    ollama_model: str
    reports_loaded: int
    schema_tables: int
    phi_markers: int


@app.post("/decode-prompt", response_model=DecodeResponse)
def handle_decode_prompt(req: DecodeRequest):
    ctx = _get_ctx()
    result = decode_prompt(req.question, ctx, provider=req.provider)
    return DecodeResponse(**result)


@app.post("/summarize", response_model=SummarizeResponse)
def handle_summarize(req: SummarizeRequest):
    ctx = _get_ctx()

    # Pass PHI markers so the Ollama summarizer anonymizes data before
    # sending it to the model (same protection as the Claude fallback path).
    result = summarize(
        req.question, req.results, req.row_count,
        phi_markers=ctx.phi, table=req.table,
    )

    if result.get("summary"):
        chart = None
        if result.get("chart") and isinstance(result["chart"], dict):
            try:
                chart = ChartSpec(**result["chart"])
            except Exception:
                pass
        return SummarizeResponse(
            summary=result["summary"],
            source=result["source"],
            anonymized=result.get("anonymized", False),
            chart=chart,
        )

    log.info("Ollama summarization failed (%s), falling back to Claude", result.get("error"))
    fallback = summarize_with_claude(
        question=req.question,
        results=req.results,
        row_count=req.row_count,
        phi_markers=ctx.phi,
        table=req.table,
    )

    if fallback.get("error") and not fallback.get("summary"):
        raise HTTPException(
            status_code=502,
            detail="Both local and cloud LLM failed to produce a summary",
        )

    fallback_chart = None
    if fallback.get("chart") and isinstance(fallback["chart"], dict):
        try:
            fallback_chart = ChartSpec(**fallback["chart"])
        except Exception:
            pass
    return SummarizeResponse(
        summary=fallback["summary"],
        source=fallback["source"],
        anonymized=fallback.get("anonymized", False),
        chart=fallback_chart,
    )


@app.get("/prompt-log")
def handle_prompt_log():
    """What was actually sent to each LLM (newest first, bounded, in-memory).

    Backs the app's Prompt Log transparency page: original question vs. the
    scrubbed question and anonymized row sample that left for the model.
    """
    return {"entries": prompt_log.entries()}


@app.get("/health", response_model=HealthResponse)
def handle_health():
    ctx = _get_ctx()
    ollama_ok = False
    try:
        OllamaClient(host=settings.ollama_base_url).list()
        ollama_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama_connected=ollama_ok,
        ollama_model=settings.ollama_model,
        reports_loaded=len(ctx.reports),
        schema_tables=len(ctx.schema.tables),
        phi_markers=len(ctx.phi.columns),
    )

import logging
from contextlib import asynccontextmanager

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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


class DecodeResponse(BaseModel):
    report: str
    parameters: dict
    template: str | None = None
    confidence: float = 0.0
    message: str | None = None


class SummarizeRequest(BaseModel):
    question: str = Field(..., min_length=1)
    results: list[dict]
    row_count: int = Field(..., ge=0)


class SummarizeResponse(BaseModel):
    summary: str
    source: str
    anonymized: bool = False


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
    result = decode_prompt(req.question, ctx)
    return DecodeResponse(**result)


@app.post("/summarize", response_model=SummarizeResponse)
def handle_summarize(req: SummarizeRequest):
    ctx = _get_ctx()

    result = summarize(req.question, req.results, req.row_count)

    if result.get("summary"):
        return SummarizeResponse(
            summary=result["summary"],
            source=result["source"],
        )

    log.info("Ollama summarization failed (%s), falling back to Claude", result.get("error"))
    fallback = summarize_with_claude(
        question=req.question,
        results=req.results,
        row_count=req.row_count,
        phi_markers=ctx.phi,
    )

    if fallback.get("error") and not fallback.get("summary"):
        raise HTTPException(
            status_code=502,
            detail="Both local and cloud LLM failed to produce a summary",
        )

    return SummarizeResponse(
        summary=fallback["summary"],
        source=fallback["source"],
        anonymized=fallback.get("anonymized", False),
    )


@app.get("/health", response_model=HealthResponse)
def handle_health():
    ctx = _get_ctx()
    ollama_ok = False
    try:
        ollama.list()
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

"""FastAPI routes and static frontend for AutoFlow Python."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules.cleaner import clean_data
from modules.reader import load_file
from modules.report_excel import export_excel
from modules.report_pdf import export_pdf
from modules.stats import generate_stats


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"
INPUT_DIR = Path("/tmp/autoflow_inputs")
OUTPUT_DIR = Path("/tmp/autoflow_outputs")
SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Create runtime directories required by the application."""

    ensure_runtime_dirs()
    yield


app = FastAPI(
    title="AutoFlow Python",
    description="Web interface for uploading datasets and generating automated reports.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a CSV or XLSX file, run the analysis pipeline, and return summary stats."""

    ensure_runtime_dirs()
    session_id = str(uuid4())
    suffix = _validate_extension(file.filename)
    input_path = INPUT_DIR / f"{session_id}{suffix}"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        input_path.write_bytes(content)

        raw_dataframe = load_file(str(input_path))
        cleaned_dataframe = clean_data(raw_dataframe)
        stats = generate_stats(cleaned_dataframe)

        return {
            "row_count": int(cleaned_dataframe.shape[0]),
            "column_count": int(cleaned_dataframe.shape[1]),
            "numeric_stats": stats["numeric"],
            "categorical_stats": stats["categorical"],
            "time_trend": stats["time_trend"],
            "session_id": session_id,
        }
    except HTTPException:
        if input_path.exists():
            input_path.unlink()
        raise
    except Exception as error:
        if input_path.exists():
            input_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {error}") from error


@app.get("/report")
async def generate_report(
    request: Request,
    session_id: str = Query(..., description="The session id returned by /upload."),
    output_format: Literal["excel", "pdf", "both"] = Query(
        "both",
        description="Which report format to generate.",
    ),
) -> dict[str, list[str]]:
    """Generate Excel and/or PDF reports for a previously uploaded session."""

    ensure_runtime_dirs()
    _validate_session_id(session_id)
    input_path = _resolve_session_input_path(session_id)

    try:
        raw_dataframe = load_file(str(input_path))
        cleaned_dataframe = clean_data(raw_dataframe)
        stats = generate_stats(cleaned_dataframe)

        download_urls: list[str] = []
        if output_format in {"excel", "both"}:
            excel_name = f"{session_id}_report.xlsx"
            excel_path = OUTPUT_DIR / excel_name
            export_excel(cleaned_dataframe, stats, str(excel_path))
            download_urls.append(str(request.url_for("download_file", filename=excel_name)))

        if output_format in {"pdf", "both"}:
            pdf_name = f"{session_id}_report.pdf"
            pdf_path = OUTPUT_DIR / pdf_name
            export_pdf(cleaned_dataframe, stats, str(pdf_path))
            download_urls.append(str(request.url_for("download_file", filename=pdf_name)))

        return {"download_urls": download_urls}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {error}") from error


@app.get("/download/{filename}", name="download_file")
async def download_file(filename: str) -> FileResponse:
    """Serve a generated report file from the writable runtime output directory."""

    ensure_runtime_dirs()
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Requested file was not found.")

    return FileResponse(path=file_path, filename=safe_name)


@app.get("/")
async def serve_frontend() -> FileResponse:
    """Serve the single-page frontend application."""

    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="Frontend file is missing.")
    return FileResponse(INDEX_FILE)


def ensure_runtime_dirs() -> None:
    """Create writable runtime directories used for uploads and generated reports."""

    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _validate_extension(filename: str | None) -> str:
    """Validate the uploaded filename and return its supported extension."""

    if not filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Supported formats: {supported}.",
        )
    return suffix


def _validate_session_id(session_id: str) -> None:
    """Validate that the supplied session id is a well-formed UUID string."""

    try:
        UUID(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid session_id supplied.") from error


def _resolve_session_input_path(session_id: str) -> Path:
    """Find the stored input file that belongs to a given session id."""

    matches = [path for path in INPUT_DIR.glob(f"{session_id}.*") if path.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not matches:
        raise HTTPException(status_code=404, detail="No uploaded file found for this session.")
    return matches[0]

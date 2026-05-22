"""Project-wide configuration for AutoFlow Python."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT: Path = Path(__file__).resolve().parent
ENABLE_API: bool = False
MISSING_VALUE_STRATEGY: str = "fill_zero"
OUTPUT_DIR: str = "./output"
REPORT_TITLE: str = "AutoFlow Report"
SUPPORTED_INPUT_EXTENSIONS: tuple[str, ...] = (".csv", ".xlsx")
CSV_ENCODINGS: tuple[str, ...] = ("utf-8", "latin-1")
DATE_FORMAT_CANDIDATES: tuple[str, ...] = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%Y.%m.%d",
)
MISSING_FLAG_SUFFIX: str = "_missing_flag"
API_HOST: str = "127.0.0.1"
API_PORT: int = 8000
CONSOLE_FALLBACKS: dict[str, str] = {
    "✅": "[OK]",
    "❌": "[ERROR]",
    "📊": "[STATS]",
    "📁": "[FILE]",
}


def resolve_output_dir(output_dir: str | None = None) -> Path:
    """Resolve an output directory relative to the project root when needed."""

    candidate = Path(output_dir or OUTPUT_DIR).expanduser()
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()


def configure_console_output() -> None:
    """Prefer UTF-8 console output when the runtime supports it."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except ValueError:
                continue


def safe_print(message: str) -> None:
    """Print status messages without crashing on non-UTF-8 consoles."""

    try:
        print(message)
    except UnicodeEncodeError:
        fallback_message = message
        for icon, replacement in CONSOLE_FALLBACKS.items():
            fallback_message = fallback_message.replace(icon, replacement)
        print(fallback_message)

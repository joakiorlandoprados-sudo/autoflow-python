"""CLI entry point for AutoFlow Python."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal

import config
from modules.cleaner import clean_data
from modules.reader import load_file
from modules.report_excel import export_excel
from modules.report_pdf import export_pdf
from modules.stats import generate_stats


def main() -> int:
    """Run the AutoFlow Python command-line workflow."""

    config.configure_console_output()
    parser = _build_parser()
    args = parser.parse_args()

    if config.ENABLE_API and not args.input:
        return _run_api_server()

    if not args.input:
        config.safe_print("❌ Missing required argument: --input")
        config.safe_print("📁 Example: python main.py --input data/sample_data.csv --format both")
        return 1

    output_dir = _resolve_user_path(args.output_dir)
    input_path = _resolve_user_path(args.input)

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = _process_file(
            input_path=input_path,
            output_dir=output_dir,
            export_format=args.format,
        )

        config.safe_print("✅ AutoFlow process completed successfully.")
        for generated_file in generated_files:
            config.safe_print(f"📁 Generated file: {generated_file}")
        return 0
    except Exception as error:
        config.safe_print(f"❌ AutoFlow failed: {error}")
        return 1


def _build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="AutoFlow Python - Intelligent business report automator."
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Path to the input CSV or XLSX file.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=config.OUTPUT_DIR,
        help="Directory where generated reports will be saved.",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=("excel", "pdf", "both"),
        default="both",
        help="Output report format.",
    )
    return parser


def _process_file(
    input_path: Path, output_dir: Path, export_format: Literal["excel", "pdf", "both"]
) -> list[Path]:
    """Execute the full read-clean-analyze-export workflow."""

    config.safe_print("📁 Step 1/4: Loading input file...")
    dataframe = load_file(str(input_path))
    config.safe_print(
        f"✅ File loaded successfully with {dataframe.shape[0]} rows and "
        f"{dataframe.shape[1]} columns."
    )

    config.safe_print("📊 Step 2/4: Cleaning data...")
    cleaned_dataframe = clean_data(dataframe)

    config.safe_print("📊 Step 3/4: Generating statistics...")
    stats = generate_stats(cleaned_dataframe)
    config.safe_print(
        "✅ Statistics ready for "
        f"{len(stats['numeric'])} numeric columns and "
        f"{len(stats['categorical'])} categorical columns."
    )

    config.safe_print("📁 Step 4/4: Exporting reports...")
    generated_files: list[Path] = []
    file_stem = input_path.stem

    if export_format in {"excel", "both"}:
        excel_path = output_dir / f"{file_stem}_report.xlsx"
        export_excel(cleaned_dataframe, stats, str(excel_path))
        generated_files.append(excel_path)

    if export_format in {"pdf", "both"}:
        pdf_path = output_dir / f"{file_stem}_report.pdf"
        export_pdf(cleaned_dataframe, stats, str(pdf_path))
        generated_files.append(pdf_path)

    return generated_files


def _resolve_user_path(path_value: str) -> Path:
    """Resolve user-provided file system paths from the current working directory."""

    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate
    return (Path.cwd() / candidate).resolve()


def _run_api_server() -> int:
    """Launch the optional FastAPI application when enabled in config."""

    try:
        import uvicorn
    except ImportError as error:
        config.safe_print("❌ FastAPI mode requires 'uvicorn' to be installed.")
        config.safe_print("📁 Run: pip install -r requirements.txt")
        return 1

    config.safe_print(
        f"✅ API mode enabled. Starting server at "
        f"http://{config.API_HOST}:{config.API_PORT}"
    )
    uvicorn.run("api.routes:app", host=config.API_HOST, port=config.API_PORT, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

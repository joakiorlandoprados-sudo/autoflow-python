"""File readers for CSV and Excel sources."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import config


def load_file(path: str) -> pd.DataFrame:
    """Load a CSV or XLSX file into a pandas DataFrame."""

    file_path = Path(path).expanduser()
    if not file_path.is_absolute():
        file_path = (Path.cwd() / file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"Input file was not found: {file_path}")

    if not file_path.is_file():
        raise FileNotFoundError(f"Input path is not a file: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in config.SUPPORTED_INPUT_EXTENSIONS:
        supported = ", ".join(config.SUPPORTED_INPUT_EXTENSIONS)
        raise ValueError(
            f"Unsupported file format '{suffix}'. Supported formats: {supported}."
        )

    try:
        if suffix == ".csv":
            return _load_csv(file_path)
        if suffix == ".xlsx":
            return pd.read_excel(file_path)
    except pd.errors.EmptyDataError as error:
        raise ValueError(f"The file is empty and cannot be processed: {file_path}") from error
    except Exception as error:
        raise RuntimeError(f"Unable to read file '{file_path}': {error}") from error

    raise ValueError(f"Unsupported file format '{suffix}'.")


def _load_csv(file_path: Path) -> pd.DataFrame:
    """Try common encodings until the CSV file loads successfully."""

    last_error: UnicodeDecodeError | None = None
    for encoding in config.CSV_ENCODINGS:
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error

    message = (
        f"Unable to decode CSV file '{file_path}' using the supported encodings: "
        f"{', '.join(config.CSV_ENCODINGS)}."
    )
    raise UnicodeError(message) from last_error

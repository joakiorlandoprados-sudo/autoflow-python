# AutoFlow Python

AutoFlow Python is an intelligent report automator for business teams. It reads CSV or Excel files, cleans and normalizes the data, generates descriptive statistics, and exports polished Excel and PDF reports with minimal manual effort.

## Features

- Reads `.csv` and `.xlsx` files automatically
- Cleans whitespace, duplicates, empty rows and columns, and date fields
- Handles missing numeric values through configurable strategies
- Generates numeric, categorical, and time-trend summaries
- Exports styled Excel workbooks with a chart
- Exports PDF reports with summary tables and a data preview
- Includes an optional FastAPI layer for upload and report generation

## Installation

1. Create and activate a Python 3.11+ virtual environment.
2. Install the project dependencies:

```bash
pip install -r requirements.txt
```

If your Windows environment uses the `py` launcher instead of `python`, you can use:

```bash
py -3.11 -m pip install -r requirements.txt
```

## Usage

Run the CLI from the `autoflow-python` folder:

```bash
python main.py --input data/sample_data.csv --format both
```

Generate only the Excel report:

```bash
python main.py --input data/sample_data.csv --format excel
```

Choose a custom output directory:

```bash
python main.py --input data/sample_data.csv --output-dir ./output --format pdf
```

When the run finishes, the generated files are written to the configured output directory.

## Configuration

Main settings live in `config.py`:

- `ENABLE_API = False`
- `MISSING_VALUE_STRATEGY = "fill_zero"`
- `OUTPUT_DIR = "./output"`
- `REPORT_TITLE = "AutoFlow Report"`

`MISSING_VALUE_STRATEGY` supports these values:

- `fill_zero`: replace missing numeric values with `0`
- `drop`: remove rows that contain missing numeric values
- `flag`: add `*_missing_flag` columns and fill missing numeric values with the column median

## Project Structure

```text
autoflow-python/
├── main.py
├── requirements.txt
├── README.md
├── config.py
├── data/
│   └── sample_data.csv
├── modules/
│   ├── __init__.py
│   ├── reader.py
│   ├── cleaner.py
│   ├── stats.py
│   ├── report_excel.py
│   └── report_pdf.py
├── output/
│   └── .gitkeep
└── api/
    ├── __init__.py
    └── routes.py
```

## Module Overview

- `modules/reader.py`: loads CSV and Excel files with format detection and encoding fallbacks
- `modules/cleaner.py`: normalizes data, converts dates, handles missing numeric values, and removes duplicates
- `modules/stats.py`: builds structured numeric, categorical, and time-trend summaries
- `modules/report_excel.py`: creates a multi-sheet Excel report with formatting and a bar chart
- `modules/report_pdf.py`: creates a PDF report with a title page, stats tables, and top-row preview
- `api/routes.py`: provides upload and report-generation endpoints through FastAPI

## FastAPI Server

The API is optional and disabled by default.

### Option 1: Enable API mode through `config.py`

1. Open `config.py`
2. Set `ENABLE_API = True`
3. Run:

```bash
python main.py
```

This starts the API server at `http://127.0.0.1:8000`.

### Option 2: Launch FastAPI directly

```bash
uvicorn api.routes:app --reload
```

### Available Endpoints

- `POST /upload`: accepts a CSV or XLSX file and returns JSON statistics
- `GET /report?file_path=data/sample_data.csv&output_format=both`: generates reports and returns download links

## Example Workflow

1. Place a business dataset in the `data/` folder or provide any file path with `--input`.
2. Run the CLI command with the desired output format.
3. Review the generated Excel or PDF files in `output/`.

## Sample Data

The repository includes `data/sample_data.csv` with 50 realistic business sales records across six months, four regions, multiple salespeople, and five products.

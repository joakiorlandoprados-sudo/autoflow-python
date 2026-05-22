"""PDF report export utilities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config


def export_pdf(df: pd.DataFrame, stats: dict[str, Any], output_path: str) -> None:
    """Export cleaned data and summary statistics to a PDF report."""

    destination = Path(output_path).expanduser()
    if not destination.is_absolute():
        destination = (Path.cwd() / destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        document = SimpleDocTemplate(
            str(destination),
            pagesize=landscape(A4),
            leftMargin=15 * mm,
            rightMargin=15 * mm,
            topMargin=18 * mm,
            bottomMargin=15 * mm,
        )

        styles = _build_styles()
        story = _build_story(df, stats, styles)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        document.build(
            story,
            onFirstPage=lambda canvas, doc: _draw_footer(canvas, doc, timestamp),
            onLaterPages=lambda canvas, doc: _draw_footer(canvas, doc, timestamp),
        )
        config.safe_print(f"✅ PDF report saved to {destination}")
    except Exception as error:
        raise RuntimeError(f"Failed to export PDF report: {error}") from error


def _build_story(
    df: pd.DataFrame, stats: dict[str, Any], styles: dict[str, ParagraphStyle]
) -> list[Any]:
    """Build the list of ReportLab flowables for the document."""

    generated_at = stats["dataset"]["generated_at"]
    report_date = generated_at.split("T")[0] if "T" in generated_at else generated_at

    story: list[Any] = [
        Spacer(1, 20 * mm),
        Paragraph(config.REPORT_TITLE, styles["title"]),
        Spacer(1, 6 * mm),
        Paragraph(f"Report Date: {report_date}", styles["meta"]),
        Paragraph(
            f"Rows: {stats['dataset']['row_count']} | Columns: {stats['dataset']['column_count']}",
            styles["meta"],
        ),
        Paragraph(
            "This document was generated automatically by AutoFlow Python.",
            styles["body"],
        ),
        PageBreak(),
        Paragraph("Statistics Summary", styles["section"]),
        Spacer(1, 4 * mm),
        _build_numeric_stats_table(stats),
        Spacer(1, 6 * mm),
        _build_categorical_stats_table(stats),
        Spacer(1, 6 * mm),
    ]

    if stats.get("time_trend"):
        time_trend = stats["time_trend"]
        story.extend(
            [
                Paragraph("Time Trend", styles["section"]),
                Spacer(1, 3 * mm),
                Paragraph(time_trend["summary"], styles["body"]),
                Spacer(1, 5 * mm),
            ]
        )

    story.extend(
        [
            Paragraph("Top 10 Rows Preview", styles["section"]),
            Spacer(1, 4 * mm),
            _build_preview_table(df),
        ]
    )

    return story


def _build_styles() -> dict[str, ParagraphStyle]:
    """Create the paragraph styles used by the PDF report."""

    base_styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "AutoFlowTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#1F4E78"),
            alignment=1,
        ),
        "section": ParagraphStyle(
            "AutoFlowSection",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#1F1F1F"),
            spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "AutoFlowMeta",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            alignment=1,
        ),
        "body": ParagraphStyle(
            "AutoFlowBody",
            parent=base_styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
        ),
    }


def _build_numeric_stats_table(stats: dict[str, Any]) -> Table:
    """Create the numeric summary table."""

    rows: list[list[Any]] = [
        ["Column", "Min", "Max", "Mean", "Median", "Std", "Total", "Missing"]
    ]

    if stats["numeric"]:
        for column, values in stats["numeric"].items():
            rows.append(
                [
                    column,
                    values["min"],
                    values["max"],
                    values["mean"],
                    values["median"],
                    values["std"],
                    values["total"],
                    values["missing"],
                ]
            )
    else:
        rows.append(["No numeric data available", "", "", "", "", "", "", ""])

    table = Table(rows, repeatRows=1)
    table.setStyle(_base_table_style())
    return table


def _build_categorical_stats_table(stats: dict[str, Any]) -> Table:
    """Create the categorical summary table."""

    rows: list[list[Any]] = [["Column", "Unique Values", "Top 5 Most Frequent"]]

    if stats["categorical"]:
        for column, values in stats["categorical"].items():
            top_values = ", ".join(
                f"{item['value']} ({item['count']})" for item in values["top_values"]
            )
            rows.append([column, values["unique_values"], top_values])
    else:
        rows.append(["No categorical data available", "", ""])

    table = Table(rows, repeatRows=1, colWidths=[55 * mm, 30 * mm, 155 * mm])
    table.setStyle(_base_table_style())
    return table


def _build_preview_table(df: pd.DataFrame) -> Table:
    """Create a table containing the first ten rows of the dataset."""

    preview_df = df.head(10).copy()
    for column in preview_df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        preview_df[column] = preview_df[column].dt.strftime("%Y-%m-%d")

    preview_df = preview_df.fillna("")
    rows = [list(preview_df.columns)] + preview_df.astype(str).values.tolist()

    if len(rows[0]) > 8:
        col_width = 32 * mm
        widths = [col_width] * len(rows[0])
    else:
        widths = None

    table = Table(rows, repeatRows=1, colWidths=widths)
    table.setStyle(_base_table_style())
    return table


def _base_table_style() -> TableStyle:
    """Return a shared table style for PDF sections."""

    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEADING", (0, 0), (-1, -1), 11),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#EAF2F8")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFC9CA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def _draw_footer(canvas: Any, document: Any, timestamp: str) -> None:
    """Render a footer with the generation timestamp on each page."""

    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    footer_text = f"Generated on {timestamp}"
    canvas.drawRightString(document.pagesize[0] - 15 * mm, 10 * mm, footer_text)
    canvas.restoreState()

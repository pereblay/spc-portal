from __future__ import annotations

from io import BytesIO
import textwrap

import numpy as np


def _finite_xy(x_values, y_values) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x_values, dtype=float).ravel()
    y = np.asarray(y_values, dtype=float).ravel()
    if x.size == 0 or y.size == 0 or x.size != y.size:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    if x.size > 4000:
        step = int(np.ceil(x.size / 4000))
        x = x[::step]
        y = y[::step]
    return x, y


def build_markdown_report(
    *,
    student_name: str,
    course: str,
    spectrum_name: str,
    source_type: str,
    wavelength_range: tuple[float, float],
    normalization_method: str,
    spectral_evidence: str,
    ew_notes: str,
    ew_table: str,
    ratio_table: str,
    spectral_type: str,
    spectral_type_reason: str,
    luminosity_class: str,
    confidence: str,
    luminosity_reason: str,
    comments: str,
) -> str:
    return f"""# Spectral Classification Report

## Student And Spectrum

- Student: {student_name or "Not provided"}
- Course: {course or "Not provided"}
- File: {spectrum_name}
- Input type: {source_type}
- Wavelength range: {wavelength_range[0]:.3f} - {wavelength_range[1]:.3f}
- Normalization method: {normalization_method}

## Spectral Evidence

{spectral_evidence or "No evidence provided."}

## Equivalent Width Measurements

{ew_table or "No equivalent-width measurements recorded."}

## Line Ratios

{ratio_table or "No line ratios recorded."}

## Evidence Comments

{ew_notes or "No comments provided."}

## Classification

- Spectral type: {spectral_type or "Not provided"}
- Luminosity class: {luminosity_class or "Not provided"}
- Confidence: {confidence or "Not provided"}

### Spectral-Type Justification

{spectral_type_reason or "Not provided."}

### Luminosity-Class Justification

{luminosity_reason or "Not provided."}

## General Comments

{comments or "No comments provided."}
"""


def build_pdf_report(
    *,
    student_name: str,
    course: str,
    spectrum_name: str,
    source_type: str,
    wavelength_range: tuple[float, float],
    normalization_method: str,
    spectral_evidence: str,
    ew_notes: str,
    ew_table: str,
    ratio_table: str,
    ew_rows: list[dict],
    ratio_rows: list[dict],
    spectral_type: str,
    spectral_type_reason: str,
    luminosity_class: str,
    confidence: str,
    luminosity_reason: str,
    comments: str,
    original_wavelength,
    original_flux,
    normalized_wavelength,
    normalized_flux,
) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    sections = [
        ("Student And Spectrum", [
            f"Student: {student_name or 'Not provided'}",
            f"Course: {course or 'Not provided'}",
            f"File: {spectrum_name}",
            f"Input type: {source_type}",
            f"Wavelength range: {wavelength_range[0]:.3f} - {wavelength_range[1]:.3f}",
            f"Normalization method: {normalization_method}",
        ]),
        ("Spectral Evidence", [spectral_evidence or "No evidence provided."]),
        ("Evidence Comments", [ew_notes or "No comments provided."]),
        ("Classification", [
            f"Spectral type: {spectral_type or 'Not provided'}",
            f"Luminosity class: {luminosity_class or 'Not provided'}",
            f"Confidence: {confidence or 'Not provided'}",
        ]),
        ("Spectral-Type Justification", [spectral_type_reason or "Not provided."]),
        ("Luminosity-Class Justification", [luminosity_reason or "Not provided."]),
        ("General Comments", [comments or "No comments provided."]),
    ]

    width, height = 1240, 1754
    margin = 90
    content_bottom = height - margin
    usable_height = content_bottom - margin
    line_height = 28
    title_font = ImageFont.load_default(size=34)
    section_font = ImageFont.load_default(size=22)
    body_font = ImageFont.load_default(size=18)
    table_font = ImageFont.load_default(size=14)
    table_header_font = ImageFont.load_default(size=15)
    pages: list[Image.Image] = []
    page = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(page)
    y = margin

    def new_page() -> None:
        nonlocal page, draw, y
        pages.append(page)
        page = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(page)
        y = margin

    def ensure_space(required_height: int) -> None:
        if y > margin and y + required_height > content_bottom:
            new_page()

    def draw_line(text: str, font, fill: str = "#222222", advance: int = line_height) -> None:
        nonlocal y
        if y + advance > content_bottom:
            new_page()
        draw.text((margin, y), text, font=font, fill=fill)
        y += advance

    def wrapped_lines(paragraphs: list[str], width_chars: int = 105) -> list[str]:
        lines: list[str] = []
        for paragraph in paragraphs:
            lines.extend(textwrap.wrap(str(paragraph), width=width_chars) or [""])
        return lines

    def draw_text_section(title: str, paragraphs: list[str]) -> None:
        nonlocal y
        lines = wrapped_lines(paragraphs)
        block_height = 12 + 34 + len(lines) * line_height + 8
        if block_height <= usable_height:
            ensure_space(block_height)
        else:
            ensure_space(34 + 2 * line_height)
        y += 12
        draw_line(title, section_font, fill="#111111", advance=34)
        for line in lines:
            if y + line_height > content_bottom:
                new_page()
                draw_line(f"{title} (continued)", section_font, fill="#111111", advance=34)
            draw_line(line, body_font)
        y += 8

    def axis_value(value: float) -> str:
        if value != 0 and (abs(value) < 1e-3 or abs(value) >= 1e5):
            return f"{value:.2e}"
        return f"{value:.3g}"

    def draw_plot(title: str, x_values, y_values, y_label: str) -> None:
        nonlocal y
        x, values = _finite_xy(x_values, y_values)
        plot_height = 330
        ensure_space(plot_height + 120)
        draw_line(title, section_font, fill="#111111", advance=34)
        left = margin + 92
        top = y + 10
        right = width - margin
        bottom = top + plot_height
        draw.rectangle((left, top, right, bottom), outline="#222222", width=2)
        if x.size < 2:
            draw.text((left + 20, top + 120), "Spectrum not available.", font=body_font, fill="#666666")
        else:
            xmin, xmax = float(np.nanmin(x)), float(np.nanmax(x))
            ymin, ymax = (float(value) for value in np.nanpercentile(values, [1, 99]))
            span = ymax - ymin
            if not np.isfinite(span) or span <= 0:
                span = max(abs(ymax), 1.0)
                ymin = ymax - 0.5 * span
                ymax = ymax + 0.5 * span
            ypad = 0.08 * span
            ymin -= ypad
            ymax += ypad
            for frac in (0.25, 0.5, 0.75):
                gx = left + frac * (right - left)
                gy = top + frac * (bottom - top)
                draw.line((gx, top, gx, bottom), fill="#e1e5ea", width=1)
                draw.line((left, gy, right, gy), fill="#e1e5ea", width=1)
            clipped_values = np.clip(values, ymin, ymax)
            px = left + (x - xmin) / max(xmax - xmin, np.finfo(float).eps) * (right - left)
            py = bottom - (clipped_values - ymin) / (ymax - ymin) * (bottom - top)
            points = [(float(a), float(b)) for a, b in zip(px, py)]
            if len(points) >= 2:
                draw.line(points, fill="#243b53", width=2)
            draw.text((left, bottom + 10), f"{xmin:.1f}", font=body_font, fill="#333333")
            draw.text((right - 85, bottom + 10), f"{xmax:.1f}", font=body_font, fill="#333333")
            draw.text((margin, top), axis_value(ymax), font=table_font, fill="#495057")
            draw.text((margin, bottom - 18), axis_value(ymin), font=table_font, fill="#495057")
            draw.text((margin, top + 145), y_label, font=body_font, fill="#333333")
            draw.text((left + 360, bottom + 38), "Wavelength", font=body_font, fill="#333333")
        y = bottom + 78

    def cell_value(value) -> str:
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.5g}"
        return str(value if value is not None else "")

    def draw_table(
        title: str,
        rows: list[dict],
        columns: list[tuple[str, str, float]],
        empty_message: str,
    ) -> None:
        nonlocal y
        row_height = 32
        total_weight = sum(weight for _, _, weight in columns)
        available_width = width - 2 * margin
        column_widths = [int(available_width * weight / total_weight) for _, _, weight in columns]

        def draw_header() -> None:
            nonlocal y
            x = margin
            for (label, _, _), column_width in zip(columns, column_widths):
                draw.rectangle((x, y, x + column_width, y + row_height), fill="#e9ecef", outline="#adb5bd")
                draw.text((x + 5, y + 7), label, font=table_header_font, fill="#212529")
                x += column_width
            y += row_height

        if not rows:
            draw_text_section(title, [empty_message])
            return

        estimated_height = 12 + 34 + row_height * (len(rows) + 1) + 8
        if estimated_height <= usable_height:
            ensure_space(estimated_height)
        else:
            ensure_space(12 + 34 + 2 * row_height)
        y += 12
        draw_line(title, section_font, fill="#111111", advance=34)
        draw_header()
        for row_index, row in enumerate(rows):
            if y + row_height > content_bottom:
                new_page()
                draw_line(f"{title} (continued)", section_font, fill="#111111", advance=34)
                draw_header()
            x = margin
            fill = "#f8f9fa" if row_index % 2 else "#ffffff"
            for (_, key, _), column_width in zip(columns, column_widths):
                draw.rectangle((x, y, x + column_width, y + row_height), fill=fill, outline="#ced4da")
                value = cell_value(row.get(key, ""))
                max_chars = max(4, int(column_width / 8.5))
                if len(value) > max_chars:
                    value = value[: max_chars - 3] + "..."
                draw.text((x + 5, y + 8), value, font=table_font, fill="#343a40")
                x += column_width
            y += row_height
        y += 8

    draw_line("Spectral Classification Report", title_font, advance=48)
    draw_text_section(*sections[0])
    draw_plot("Original Spectrum", original_wavelength, original_flux, "Flux")
    draw_plot("Normalized Spectrum", normalized_wavelength, normalized_flux, "Normalized flux")
    draw_text_section(*sections[1])
    draw_table(
        "Equivalent Width Measurements",
        ew_rows,
        [
            ("Element", "Element", 0.8),
            ("Line", "Line", 1.5),
            ("Lambda ref", "lambda_ref", 0.9),
            ("Start", "start", 0.9),
            ("End", "end", 0.9),
            ("EW", "EW", 0.9),
        ],
        "No equivalent-width measurements recorded.",
    )
    draw_table(
        "Line Ratios",
        ratio_rows,
        [
            ("Line 1", "Line 1", 1.2),
            ("Center 1", "center_1", 0.9),
            ("I1", "intensity_1", 0.8),
            ("Line 2", "Line 2", 1.2),
            ("Center 2", "center_2", 0.9),
            ("I2", "intensity_2", 0.8),
            ("Ratio", "ratio_1_2", 0.9),
        ],
        "No line ratios recorded.",
    )
    for section in sections[2:]:
        draw_text_section(*section)
    pages.append(page)

    buffer = BytesIO()
    first, rest = pages[0], pages[1:]
    first.save(buffer, format="PDF", save_all=True, append_images=rest, resolution=150)
    buffer.seek(0)
    return buffer.getvalue()


def append_pdf_report(previous_pdf: bytes, current_report_pdf: bytes) -> bytes:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError("Install pypdf to append the current report to an existing PDF.") from exc

    writer = PdfWriter()
    for pdf_bytes in (previous_pdf, current_report_pdf):
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()

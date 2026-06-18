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
    spectral_type: str,
    spectral_type_reason: str,
    luminosity_class: str,
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
        ("Equivalent Width Measurements", [ew_table or "No equivalent-width measurements recorded."]),
        ("Line Ratios", [ratio_table or "No line ratios recorded."]),
        ("Evidence Comments", [ew_notes or "No comments provided."]),
        ("Classification", [
            f"Spectral type: {spectral_type or 'Not provided'}",
            f"Luminosity class: {luminosity_class or 'Not provided'}",
        ]),
        ("Spectral-Type Justification", [spectral_type_reason or "Not provided."]),
        ("Luminosity-Class Justification", [luminosity_reason or "Not provided."]),
        ("General Comments", [comments or "No comments provided."]),
    ]

    width, height = 1240, 1754
    margin = 90
    line_height = 28
    title_font = ImageFont.load_default(size=34)
    section_font = ImageFont.load_default(size=22)
    body_font = ImageFont.load_default(size=18)
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

    def draw_line(text: str, font, fill: str = "#222222", advance: int = line_height) -> None:
        nonlocal y
        if y > height - margin:
            new_page()
        draw.text((margin, y), text, font=font, fill=fill)
        y += advance

    def draw_plot(title: str, x_values, y_values, y_label: str) -> None:
        nonlocal y
        x, values = _finite_xy(x_values, y_values)
        plot_height = 330
        if y + plot_height + 70 > height - margin:
            new_page()
        draw_line(title, section_font, fill="#111111", advance=34)
        left = margin + 70
        top = y + 10
        right = width - margin
        bottom = top + plot_height
        draw.rectangle((left, top, right, bottom), outline="#222222", width=2)
        if x.size < 2:
            draw.text((left + 20, top + 120), "Spectrum not available.", font=body_font, fill="#666666")
        else:
            xmin, xmax = float(np.nanmin(x)), float(np.nanmax(x))
            ymin, ymax = np.nanpercentile(values, [1, 99])
            if np.isclose(ymin, ymax):
                ymin -= 1.0
                ymax += 1.0
            ypad = 0.08 * (ymax - ymin)
            ymin -= ypad
            ymax += ypad
            for frac in (0.25, 0.5, 0.75):
                gx = left + frac * (right - left)
                gy = top + frac * (bottom - top)
                draw.line((gx, top, gx, bottom), fill="#e1e5ea", width=1)
                draw.line((left, gy, right, gy), fill="#e1e5ea", width=1)
            px = left + (x - xmin) / (xmax - xmin) * (right - left)
            py = bottom - (values - ymin) / (ymax - ymin) * (bottom - top)
            points = [(float(a), float(b)) for a, b in zip(px, py)]
            if len(points) >= 2:
                draw.line(points, fill="#243b53", width=2)
            draw.text((left, bottom + 10), f"{xmin:.1f}", font=body_font, fill="#333333")
            draw.text((right - 85, bottom + 10), f"{xmax:.1f}", font=body_font, fill="#333333")
            draw.text((margin, top + 120), y_label, font=body_font, fill="#333333")
            draw.text((left + 360, bottom + 38), "Wavelength", font=body_font, fill="#333333")
        y = bottom + 78

    draw_line("Spectral Classification Report", title_font, advance=48)
    for title, paragraphs in sections[:1]:
        y += 12
        draw_line(title, section_font, fill="#111111", advance=34)
        for paragraph in paragraphs:
            for line in textwrap.wrap(str(paragraph), width=105) or [""]:
                draw_line(line, body_font)
        y += 8
    draw_plot("Original Spectrum", original_wavelength, original_flux, "Flux")
    draw_plot("Normalized Spectrum", normalized_wavelength, normalized_flux, "Normalized flux")
    for title, paragraphs in sections[1:]:
        y += 12
        draw_line(title, section_font, fill="#111111", advance=34)
        for paragraph in paragraphs:
            for line in textwrap.wrap(str(paragraph), width=105) or [""]:
                draw_line(line, body_font)
        y += 8
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

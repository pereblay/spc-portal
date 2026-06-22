from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from spectral_portal.core.click_selector import continuum_click_selector
from spectral_portal.core.dibs import DIBDetection, detect_dib_is_features
from spectral_portal.core.io import Spectrum, inspect_fits_hdus, load_example, load_fits, load_spectrum
from spectral_portal.core.lines import LINE_COLORS, families, nearest_line, selected_lines
from spectral_portal.core.measurements import crop_spectrum, equivalent_width, line_center_and_intensity
from spectral_portal.core.mk_sequence import load_main_sequence
from spectral_portal.core.normalize import fit_continuum, normalize_flux
from spectral_portal.core.report import append_pdf_report, build_markdown_report, build_pdf_report


st.set_page_config(
    page_title="Spectral classification",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
      --portal-dark: #343a40;
      --portal-dark-hover: #212529;
      --primary-color: #343a40;
      --primaryColor: #343a40;
    }
    .stApp {
      --primary-color: #343a40;
      --primaryColor: #343a40;
      --primary-color-light: #495057;
      --primaryColorLight: #495057;
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] {
      background-color: var(--portal-dark) !important;
      border-color: var(--portal-dark) !important;
      color: white !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover {
      background-color: var(--portal-dark-hover) !important;
      border-color: var(--portal-dark-hover) !important;
      color: white !important;
    }
    [data-baseweb="tag"] {
      background-color: var(--portal-dark) !important;
      color: white !important;
    }
    [data-baseweb="tag"] svg {
      color: white !important;
    }
    /* Streamlit/BaseWeb active accents: sliders, toggles, checkboxes, tabs. */
    [data-baseweb="slider"] [role="slider"] {
      background-color: var(--portal-dark) !important;
      border-color: var(--portal-dark) !important;
      box-shadow: none !important;
    }
    [data-testid="stSlider"] [role="slider"] {
      background: var(--portal-dark) !important;
      background-color: var(--portal-dark) !important;
      border-color: var(--portal-dark) !important;
      color: var(--portal-dark) !important;
    }
    [data-baseweb="slider"] div[style*="255, 75, 75"],
    [data-baseweb="slider"] div[style*="rgb(255"],
    [data-baseweb="slider"] div[style*="#ff"],
    [data-testid="stSlider"] div[style*="255, 75, 75"],
    [data-testid="stSlider"] div[style*="rgb(255"],
    [data-testid="stSlider"] div[style*="#ff"] {
      background: var(--portal-dark) !important;
      background-color: var(--portal-dark) !important;
      border-color: var(--portal-dark) !important;
      color: var(--portal-dark) !important;
    }
    [data-testid="stSlider"] div[style*="linear-gradient"] {
      background: linear-gradient(to right, var(--portal-dark), var(--portal-dark)) !important;
    }
    [data-testid="stSlider"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSlider"] label,
    [data-testid="stSlider"] span,
    [data-testid="stSlider"] div {
      color: var(--portal-dark) !important;
    }
    [role="checkbox"][aria-checked="true"],
    [data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"],
    [data-testid="stToggle"] [role="checkbox"][aria-checked="true"] {
      background-color: var(--portal-dark) !important;
      border-color: var(--portal-dark) !important;
    }
    [data-testid="stCheckbox"] [data-baseweb="checkbox"] > div,
    [data-testid="stCheckbox"] label > div:first-child,
    [data-testid="stToggle"] [data-baseweb="checkbox"] > div,
    [data-testid="stToggle"] label > div:first-child {
      border-color: var(--portal-dark) !important;
    }
    [data-testid="stCheckbox"] [aria-checked="true"] div,
    [data-testid="stToggle"] [aria-checked="true"] div {
      background: var(--portal-dark) !important;
      background-color: var(--portal-dark) !important;
      border-color: var(--portal-dark) !important;
    }
    [role="checkbox"][aria-checked="true"] svg,
    [data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"] svg,
    [data-testid="stToggle"] [role="checkbox"][aria-checked="true"] svg {
      color: white !important;
      fill: white !important;
    }
    [data-baseweb="switch"] div[style*="255, 75, 75"],
    [data-testid="stToggle"] div[style*="255, 75, 75"],
    [data-testid="stToggle"] div[style*="rgb(255"],
    [data-testid="stToggle"] div[style*="#ff"] {
      background: var(--portal-dark) !important;
      background-color: var(--portal-dark) !important;
      border-color: var(--portal-dark) !important;
    }
    [data-baseweb="tab-highlight"] {
      background-color: var(--portal-dark) !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
      background: var(--portal-dark) !important;
      background-color: var(--portal-dark) !important;
    }
    [data-baseweb="tab"][aria-selected="true"],
    [data-baseweb="tab"][aria-selected="true"] p,
    button[role="tab"][aria-selected="true"],
    button[role="tab"][aria-selected="true"] p,
    [data-testid="stTabs"] button[aria-selected="true"],
    [data-testid="stTabs"] button[aria-selected="true"] p {
      color: var(--portal-dark) !important;
    }
    [data-baseweb="tab-border"] {
      background-color: #dee2e6 !important;
    }
    [style*="rgb(255, 75, 75)"],
    [style*="rgba(255, 75, 75"],
    [style*="#ff4b4b"],
    [style*="#FF4B4B"] {
      border-color: var(--portal-dark) !important;
      color: var(--portal-dark) !important;
      caret-color: var(--portal-dark) !important;
    }
    .classification-workflow {
      margin: 0.8rem 0 1.2rem;
      padding: 0.85rem 0 0.15rem;
      border-top: 1px solid #ced4da;
      border-bottom: 1px solid #dee2e6;
    }
    .classification-workflow-title {
      margin: 0 0 0.75rem;
      color: #212529;
      font-size: 1rem;
      font-weight: 650;
    }
    .classification-workflow-steps {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1.1rem;
    }
    .classification-workflow-step {
      min-width: 0;
      padding: 0 0 0.85rem;
    }
    .classification-workflow-number {
      display: block;
      margin-bottom: 0.25rem;
      color: #343a40;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
    }
    .classification-workflow-step p {
      margin: 0;
      color: #495057;
      font-size: 0.88rem;
      line-height: 1.45;
    }
    @media (max-width: 780px) {
      .classification-workflow-steps {
        grid-template-columns: 1fr;
        gap: 0.25rem;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    st.session_state.setdefault("show_help", False)
    st.session_state.setdefault("manual_points", [])
    st.session_state.setdefault("manual_selection_active", False)
    st.session_state.setdefault("last_normalization_method", None)
    st.session_state.setdefault("continuum", None)
    st.session_state.setdefault("normalized", None)
    st.session_state.setdefault("normalization_context", None)
    st.session_state.setdefault("last_ew", "")
    st.session_state.setdefault("measurement_mode", None)
    st.session_state.setdefault("ew_clicks", [])
    st.session_state.setdefault("ratio_clicks", [])
    st.session_state.setdefault("ew_results", [])
    st.session_state.setdefault("ratio_results", [])
    st.session_state.setdefault("show_mk_sequence", False)
    st.session_state.setdefault("spectral_evidence", "")
    st.session_state.setdefault("ew_notes", "")
    st.session_state.setdefault("spectral_type", "")
    st.session_state.setdefault("luminosity_class", "")
    st.session_state.setdefault("confidence", "medium")
    st.session_state.setdefault("spectral_type_reason", "")
    st.session_state.setdefault("luminosity_reason", "")
    st.session_state.setdefault("classification_comments", "")


def clear_normalization() -> None:
    st.session_state.continuum = None
    st.session_state.normalized = None
    st.session_state.normalization_context = None


@st.cache_data(show_spinner=False, ttl=7 * 24 * 60 * 60)
def cached_mk_main_sequence() -> list[dict[str, object]]:
    return load_main_sequence()


def interpolated_flux_at(wavelength: np.ndarray, flux: np.ndarray, target_wavelength: float) -> float:
    return float(np.interp(float(target_wavelength), wavelength, flux))


def line_metadata(wavelength: float) -> dict[str, str | float]:
    line = nearest_line(wavelength)
    return {
        "Element": line.family,
        "Line": line.label,
        "lambda_ref": float(line.wavelength),
    }


def point_from_click(clicked) -> tuple[float, float] | None:
    if not clicked:
        return None
    return float(clicked["wavelength"]), float(clicked["flux"])


def format_result_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = [" | ".join(headers), " | ".join(["---"] * len(headers))]
    for row in rows:
        values = []
        for header in headers:
            value = row.get(header, "")
            if isinstance(value, float):
                values.append(f"{value:.5g}")
            else:
                values.append(str(value))
        lines.append(" | ".join(values))
    return "\n".join(lines)


def pdf_file_name(value: str, default: str = "spectral_classification_report.pdf") -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_", ".", " "} else "_" for char in value.strip())
    cleaned = "_".join(cleaned.split())
    if not cleaned:
        cleaned = default
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned


def y_range(values: np.ndarray) -> tuple[float, float]:
    ymin = float(np.nanpercentile(values, 1))
    ymax = float(np.nanpercentile(values, 99))
    span = ymax - ymin
    if span <= 0 or not np.isfinite(span):
        span = max(abs(ymax), 1.0)
    padding = 0.08 * span
    return ymin - padding, ymax + padding


def y_tickformat(values: np.ndarray) -> str | None:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return None
    max_abs = float(np.nanmax(np.abs(finite)))
    if 0 < max_abs < 1e-3 or max_abs >= 1e5:
        return ".2e"
    return None


def show_help() -> None:
    st.session_state.show_help = True


def hide_help() -> None:
    st.session_state.show_help = False


def render_help_page() -> None:
    help_path = Path(__file__).with_name("HELP.md")
    help_text = help_path.read_text(encoding="utf-8")

    st.button("Back to classification", type="primary", on_click=hide_help, key="help_back_top")
    st.markdown(help_text)
    st.button("Back to classification", type="primary", on_click=hide_help, key="help_back_bottom")


def render_classification_workflow() -> None:
    st.markdown(
        """
        <section class="classification-workflow" aria-label="Classification workflow">
          <h3 class="classification-workflow-title">Classification workflow</h3>
          <div class="classification-workflow-steps">
            <div class="classification-workflow-step">
              <span class="classification-workflow-number">Step 0</span>
              <p>Crop the useful wavelength range, fit the continuum, and normalize the spectrum.</p>
            </div>
            <div class="classification-workflow-step">
              <span class="classification-workflow-number">Step 1</span>
              <p>Compare with the MK main sequence and select the most likely spectral type.</p>
            </div>
            <div class="classification-workflow-step">
              <span class="classification-workflow-number">Step 2</span>
              <p>Select the subtype by comparison with the corresponding series in Gray's Digital Atlas, using the indicated line intensities and ratios.</p>
            </div>
            <div class="classification-workflow-step">
              <span class="classification-workflow-number">Step 3</span>
              <p>Assign the luminosity class by comparing with the nearest Gray luminosity sequence, recording the relevant line-intensity and line-ratio evidence.</p>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_original_plot(
    spectrum: Spectrum,
    wl_min: float,
    wl_max: float,
    cropped_wl: np.ndarray,
    continuum: np.ndarray | None,
    manual_points: list[tuple[float, float]],
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=spectrum.wavelength,
            y=spectrum.flux,
            mode="lines+markers",
            name="Original flux",
            line=dict(color="#243b53", width=1.25),
            marker=dict(color="#243b53", size=3, opacity=0.22),
            hovertemplate="Wavelength=%{x:.3f}<br>Flux=%{y:.4e}<extra></extra>",
        )
    )
    if continuum is not None:
        fig.add_trace(
            go.Scatter(
                x=cropped_wl,
                y=continuum,
                mode="lines",
                name="Fitted continuum",
                line=dict(color="#d95f02", width=2.0, dash="dash"),
                hovertemplate="Wavelength=%{x:.3f}<br>Continuum=%{y:.4e}<extra></extra>",
            )
        )
    if manual_points:
        fig.add_trace(
            go.Scatter(
                x=[point[0] for point in manual_points],
                y=[point[1] for point in manual_points],
                mode="markers",
                name="Continuum points",
                marker=dict(color="#d95f02", size=8, symbol="circle-open", line=dict(width=2)),
                hovertemplate="Wavelength=%{x:.3f}<br>Flux=%{y:.4e}<extra></extra>",
            )
        )

    fig.add_vrect(
        x0=min(wl_min, wl_max),
        x1=max(wl_min, wl_max),
        fillcolor="#74c0fc",
        opacity=0.16,
        line_width=0,
        annotation_text="crop",
        annotation_position="top left",
    )
    ymin, ymax = y_range(spectrum.flux)
    fig.update_layout(
        height=390,
        margin=dict(l=20, r=20, t=34, b=18),
        hovermode="x unified",
        clickmode="event+select",
        dragmode="select",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis_title="Wavelength",
        yaxis_title="Flux",
        template="plotly_white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e9ecef", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e9ecef", range=[ymin, ymax], tickformat=y_tickformat(spectrum.flux))
    return fig


def render_normalized_plot(
    wavelength: np.ndarray,
    normalized: np.ndarray | None,
    line_families: list[str],
    show_line_labels: bool,
    dib_detections: list[DIBDetection],
) -> go.Figure:
    fig = go.Figure()
    if normalized is not None:
        fig.add_trace(
            go.Scattergl(
                x=wavelength,
                y=normalized,
                mode="lines",
                name="Normalized spectrum",
                line=dict(color="#006d77", width=1.45),
            )
        )
        fig.add_hline(y=1.0, line_width=1, line_dash="dot", line_color="#6c757d")
        ymin, ymax = y_range(normalized)
    else:
        ymin, ymax = 0.8, 1.2
        fig.add_annotation(
            text="Click Compute normalization to see the result",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=15, color="#6c757d"),
        )

    padding = 0.08 * max(ymax - ymin, 1e-6)
    for detection in dib_detections:
        fig.add_vrect(
            x0=detection.x0,
            x1=detection.x1,
            fillcolor="#2f9e44",
            opacity=0.22,
            line_width=0,
            annotation_text=detection.label,
            annotation_position="top left",
            annotation_font_size=12,
            annotation_font_color="#1b5e20",
        )

    for line in selected_lines(line_families):
        if wavelength.min() <= line.wavelength <= wavelength.max():
            color = LINE_COLORS.get(line.family, "#777777")
            fig.add_vline(x=line.wavelength, line_width=1, line_dash="dot", line_color=color)
            if show_line_labels:
                fig.add_annotation(
                    x=line.wavelength,
                    y=ymax,
                    text=line.label,
                    showarrow=False,
                    textangle=-90,
                    font=dict(size=14, color=color),
                    yanchor="bottom",
                )

    fig.update_layout(
        height=430,
        margin=dict(l=20, r=20, t=34, b=18),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis_title="Wavelength",
        yaxis_title="Normalized flux",
        template="plotly_white",
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#e9ecef",
        zeroline=False,
        range=[float(np.nanmin(wavelength)), float(np.nanmax(wavelength))],
    )
    fig.update_yaxes(showgrid=True, gridcolor="#e9ecef", range=[ymin - padding, ymax + 3 * padding])
    return fig


def render_mk_comparison_plot(
    studied_wavelength: np.ndarray,
    studied_normalized: np.ndarray,
    studied_label: str,
    sequence: list[dict[str, object]],
    wavelength_min: float,
    wavelength_max: float,
) -> go.Figure:
    fig = go.Figure()
    offset = 1.7
    contrast = 1.6
    colors = ["#111827", "#4666e5", "#6688ed", "#8ba7ef", "#adb5bd", "#e59b7c", "#ed775e", "#d94841"]
    entries: list[dict[str, object]] = [
        {
            "spectral_type": "Studied spectrum",
            "star": studied_label,
            "wavelength": np.asarray(studied_wavelength, dtype=float),
            "normalized_flux": np.asarray(studied_normalized, dtype=float),
        },
        *sequence,
    ]
    baselines: list[float] = []
    labels: list[str] = []

    for index, (entry, color) in enumerate(zip(entries, colors)):
        wavelength = np.asarray(entry["wavelength"], dtype=float)
        normalized = np.asarray(entry["normalized_flux"], dtype=float)
        baseline = (len(entries) - 1 - index) * offset
        displayed = baseline + 1.0 + contrast * (normalized - 1.0)
        baselines.append(baseline)
        labels.append(
            f'<b>Studied</b>  {entry["star"]}'
            if index == 0
            else f'{entry["spectral_type"]}  {entry["star"]}'
        )
        fig.add_trace(
            go.Scattergl(
                x=wavelength,
                y=displayed,
                mode="lines",
                name=str(entry["spectral_type"]),
                line=dict(color=color, width=2.0 if index == 0 else 1.4),
                customdata=normalized,
                hovertemplate=(
                    f'{entry["spectral_type"]} · {entry["star"]}'
                    "<br>Wavelength=%{x:.2f} Å<br>Normalized flux=%{customdata:.3f}<extra></extra>"
                ),
            )
        )
        fig.add_hline(y=baseline + 1.0, line_width=0.5, line_color="#ced4da")

    top_features = ((3933.7, "Ca II K"), (4101.7, "Hδ"), (4340.5, "Hγ"), (4861.3, "Hβ"))
    bottom_features = ((3970.0, "Ca II H+Hε"), (4305.0, "CH G"), (4471.5, "He I"), (4481.2, "Mg II"), (4954.0, "TiO"))
    visible_top = tuple(feature for feature in top_features if wavelength_min <= feature[0] <= wavelength_max)
    visible_bottom = tuple(feature for feature in bottom_features if wavelength_min <= feature[0] <= wavelength_max)
    y_min = min(baselines) - 0.7
    y_max = max(baselines) + 1.9
    for wavelength, label in visible_top + visible_bottom:
        color = "#495057" if "Ca" in label else "#6f42c1" if label.startswith("H") else "#2b8a3e" if label in {"CH G", "TiO"} else "#9c4f15"
        fig.add_vline(x=wavelength, line_width=0.8, line_dash="dot", line_color=color, opacity=0.55)
    for wavelength, label in visible_top:
        fig.add_annotation(x=wavelength, y=y_max, text=label, textangle=-90, showarrow=False, yanchor="bottom", font=dict(size=11, color="#343a40"))
    for wavelength, label in visible_bottom:
        fig.add_annotation(x=wavelength, y=y_min, text=label, textangle=-90, showarrow=False, yanchor="top", font=dict(size=11, color="#343a40"))

    fig.update_layout(
        height=820,
        margin=dict(l=115, r=20, t=58, b=60),
        template="plotly_white",
        showlegend=False,
        hovermode="closest",
        title=dict(text="Studied spectrum compared with the JHC main sequence", x=0.5, xanchor="center", font=dict(size=16)),
        xaxis_title="Wavelength (Å)",
        yaxis_title="Normalized flux + vertical offset",
    )
    fig.update_xaxes(range=[float(wavelength_min), float(wavelength_max)], showgrid=True, gridcolor="#e9ecef", zeroline=False)
    fig.update_yaxes(
        range=[y_min - 0.9, y_max + 0.9],
        tickmode="array",
        tickvals=[baseline + 1.0 for baseline in baselines],
        ticktext=labels,
        showgrid=False,
        zeroline=False,
    )
    return fig


def spectrum_summary(spectrum: Spectrum) -> None:
    cols = st.columns(4)
    cols[0].metric("Points", f"{spectrum.size:,}".replace(",", "."))
    cols[1].metric("lambda min", f"{spectrum.wavelength_min:.2f}")
    cols[2].metric("lambda max", f"{spectrum.wavelength_max:.2f}")
    cols[3].metric("Input", spectrum.source_type)
    with st.expander("Detected metadata", expanded=False):
        st.json(spectrum.metadata)


def normalization_context(
    spectrum: Spectrum,
    wl_min: float,
    wl_max: float,
    method: str,
    degree: int,
    spline_smoothing: float,
    manual_points: list[tuple[float, float]],
) -> tuple:
    rounded_points = tuple((round(x, 6), round(y, 6)) for x, y in manual_points)
    return (
        spectrum.source_name,
        round(float(wl_min), 6),
        round(float(wl_max), 6),
        method,
        int(degree),
        round(float(spline_smoothing), 6),
        rounded_points,
    )


def main() -> None:
    init_state()

    st.title("Spectral Classification Portal")
    selected_fits_hdu: int | None = None

    with st.sidebar:
        with st.expander("1. Spectrum upload", expanded=True):
            uploaded = st.file_uploader(
                "Upload FITS or TXT",
                type=["fits", "fit", "fts", "txt", "dat", "csv", "tsv"],
                on_change=clear_normalization,
            )
            if uploaded is not None and Path(uploaded.name).suffix.lower() in {".fits", ".fit", ".fts"}:
                try:
                    hdu_infos = inspect_fits_hdus(uploaded)
                    readable = [info for info in hdu_infos if info.supported]
                    options = readable or hdu_infos
                    labels = [
                        f"HDU {info.index}: {info.name} | {info.data_type} | {info.shape}"
                        for info in options
                    ]
                    selected_label = st.selectbox(
                        "FITS extension",
                        labels,
                        help="Choose the FITS HDU/extension to read. The diagnostic below reports whether wavelength calibration or table columns were found.",
                        on_change=clear_normalization,
                    )
                    selected_info = options[labels.index(selected_label)]
                    selected_fits_hdu = selected_info.index
                    if selected_info.supported:
                        st.success(selected_info.message)
                    else:
                        st.warning(selected_info.message)
                    with st.expander("FITS HDU diagnostics", expanded=False):
                        st.dataframe(
                            [
                                {
                                    "HDU": info.index,
                                    "Name": info.name,
                                    "Type": info.data_type,
                                    "Shape": info.shape,
                                    "Readable": info.supported,
                                    "WCS/Table OK": info.wcs_ok,
                                    "Message": info.message,
                                }
                                for info in hdu_infos
                            ],
                            width="stretch",
                        )
                except Exception as exc:
                    st.warning(f"Could not inspect FITS extensions: {exc}")
            use_example = st.toggle("Use example spectrum", value=False)

    try:
        if uploaded is not None and Path(uploaded.name).suffix.lower() in {".fits", ".fit", ".fts"}:
            spectrum = load_fits(uploaded, hdu_index=selected_fits_hdu)
        else:
            spectrum = load_spectrum(uploaded) if uploaded is not None else load_example() if use_example else None
    except Exception as exc:
        st.error(f"Could not load the spectrum: {exc}")
        return

    if st.session_state.show_help and spectrum is None:
        render_help_page()
        return

    if spectrum is None:
        st.info("Upload a FITS/TXT file or enable the example spectrum.")
        return

    with st.sidebar:
        with st.expander("2. Crop and normalization", expanded=True):
            wavelength_inputs = st.columns(2)
            wl_min = wavelength_inputs[0].number_input(
                "Minimum wavelength",
                min_value=float(spectrum.wavelength_min),
                max_value=float(spectrum.wavelength_max),
                value=float(spectrum.wavelength_min),
                format="%.2f",
                on_change=clear_normalization,
            )
            wl_max = wavelength_inputs[1].number_input(
                "Maximum wavelength",
                min_value=float(spectrum.wavelength_min),
                max_value=float(spectrum.wavelength_max),
                value=float(spectrum.wavelength_max),
                format="%.2f",
                on_change=clear_normalization,
            )
            normalization_method = st.selectbox(
                "Method",
                ["Polynomial", "Legendre", "Cubic spline", "Manual points"],
                on_change=clear_normalization,
            )
            degree = st.slider(
                "Degree",
                min_value=1,
                max_value=10 if normalization_method != "Manual points" else 5,
                value=3,
                disabled=normalization_method == "Cubic spline",
                help="For manual points, this controls the spline degree.",
                on_change=clear_normalization,
            )
            spline_smoothing = st.number_input(
                "Spline smoothing",
                min_value=0.0,
                value=0.0,
                step=0.01,
                disabled=normalization_method not in {"Cubic spline", "Manual points"},
                help="For manual points, 0 interpolates selected points exactly; larger values smooth the continuum.",
                on_change=clear_normalization,
            )
            if normalization_method == "Manual points":
                st.caption("The manual continuum is fitted with a spline through the selected points.")
                continuum_window_size = st.slider(
                    "Nearby points per click",
                    min_value=3,
                    max_value=31,
                    value=15,
                    step=2,
                    help="Each click stores the median wavelength and flux from this nearby-point window.",
                )
                if st.button("Clear manual points"):
                    st.session_state.manual_points = []
                    st.session_state.manual_selection_active = True
                    clear_normalization()
                if st.session_state.manual_selection_active:
                    st.success("Manual selection active")
                elif st.button("Reactivate manual selection"):
                    st.session_state.manual_selection_active = True
            normalize_requested = st.button("Compute normalization", type="primary")

        with st.expander("3. Spectral lines", expanded=False):
            line_families = st.multiselect(
                "Visible families",
                options=families(),
                default=["H", "He I", "Mg/Si/S", "Ca"],
            )
            line_options = st.columns(2)
            show_line_labels = line_options[0].checkbox("Line labels", value=False)
            dib_is_detector = line_options[1].checkbox("DIB/IS detector", value=False)
            dib_sensitivity = st.slider(
                "DIB/IS sensitivity",
                min_value=1.5,
                max_value=6.0,
                value=2.5,
                step=0.5,
                help="Minimum local signal-to-noise required to flag a possible interstellar feature.",
                disabled=not dib_is_detector,
            )
            line_center_half_window = st.number_input(
                "Line-centering window",
                min_value=0.1,
                value=5.0,
                step=0.5,
                help="Half-window used to locate the real minimum of a selected line.",
            )

        with st.expander("4. Generate report", expanded=False):
            st.text_input("Student name", key="report_student_name")
            st.text_input("Course", key="report_course")
            st.text_input(
                "Output PDF file name",
                key="report_output_name",
                value="spectral_classification_report.pdf",
                help="Used for both a new PDF report and an appended PDF report.",
            )
            previous_report_pdf = st.file_uploader(
                "Previous PDF report",
                type=["pdf"],
                help="Optional. If provided, the current report is appended as additional pages.",
            )
            report_download_slot = st.empty()

        st.button("Help", use_container_width=True, on_click=show_help, key="sidebar_help_bottom")

    if st.session_state.show_help:
        render_help_page()
        return

    spectrum_summary(spectrum)

    if normalization_method != st.session_state.last_normalization_method:
        st.session_state.last_normalization_method = normalization_method
        st.session_state.manual_selection_active = normalization_method == "Manual points"
        clear_normalization()
    if normalization_method != "Manual points":
        continuum_window_size = 15

    if wl_min >= wl_max:
        st.warning("Minimum wavelength must be lower than maximum wavelength.")
        return

    cropped_wl, cropped_flux = crop_spectrum(spectrum.wavelength, spectrum.flux, wl_min, wl_max)
    if cropped_wl.size < 3:
        st.warning("The crop contains too few points.")
        return

    current_context = normalization_context(
        spectrum,
        wl_min,
        wl_max,
        normalization_method,
        degree,
        spline_smoothing,
        st.session_state.manual_points,
    )
    if st.session_state.normalization_context != current_context:
        continuum = None
        normalized = None
    else:
        continuum = st.session_state.continuum
        normalized = st.session_state.normalized

    st.subheader("Original spectrum")
    original_fig = render_original_plot(
        spectrum,
        wl_min,
        wl_max,
        cropped_wl,
        continuum,
        st.session_state.manual_points,
    )

    if normalization_method == "Manual points" and st.session_state.manual_selection_active:
        st.caption(
            "Manual selection active: click representative continuum points. "
            "Each click stores wavelength and flux; the continuum fit will use the configured spline."
        )
        click_result = continuum_click_selector(
            cropped_wl,
            cropped_flux,
            st.session_state.manual_points,
            key="continuum_point_selector",
            window_size=continuum_window_size,
            toggle_points=True,
        )
        clicked = getattr(click_result, "clicked", None)
        if clicked:
            if clicked.get("action") == "delete":
                index = int(clicked["index"])
                if 0 <= index < len(st.session_state.manual_points):
                    st.session_state.manual_points.pop(index)
                    clear_normalization()
                    st.rerun()
            else:
                existing = {(round(x, 6), round(y, 6)) for x, y in st.session_state.manual_points}
                point = (float(clicked["wavelength"]), float(clicked["flux"]))
                rounded = (round(point[0], 6), round(point[1], 6))
                if rounded not in existing:
                    st.session_state.manual_points.append(point)
                    clear_normalization()
                    st.rerun()
    else:
        st.plotly_chart(original_fig, width="stretch")

    if uploaded is not None or use_example:
        render_classification_workflow()

    if normalization_method == "Manual points":
        with st.expander("Continuum points", expanded=False):
            st.caption("Manual fallback: enter only the wavelength; flux is interpolated from the spectrum.")
            pcols = st.columns([1, 1])
            manual_wl = pcols[0].number_input(
                "Point wavelength",
                min_value=float(cropped_wl[0]),
                max_value=float(cropped_wl[-1]),
                value=float(cropped_wl[cropped_wl.size // 2]),
            )
            if pcols[1].button("Add point"):
                manual_flux = interpolated_flux_at(cropped_wl, cropped_flux, manual_wl)
                st.session_state.manual_points.append((float(manual_wl), float(manual_flux)))
                st.session_state.manual_selection_active = True
                clear_normalization()
                st.rerun()
            if st.session_state.manual_points:
                st.caption(f"{len(st.session_state.manual_points)} selected points. Minimum required: degree + 1 distinct wavelengths.")
                st.caption("Selected points")
                for index, (point_wl, point_flux) in enumerate(st.session_state.manual_points):
                    row = st.columns([2, 2, 1])
                    row[0].write(f"{point_wl:.4f}")
                    row[1].write(f"{point_flux:.6g}")
                    if row[2].button("Delete", key=f"delete_manual_point_{index}"):
                        st.session_state.manual_points.pop(index)
                        st.session_state.manual_selection_active = True
                        clear_normalization()
                        st.rerun()

    if normalize_requested:
        try:
            continuum = fit_continuum(
                cropped_wl,
                cropped_flux,
                normalization_method,
                degree=degree,
                manual_points=st.session_state.manual_points,
                spline_smoothing=None if spline_smoothing == 0 else spline_smoothing,
                spline_degree=degree if normalization_method == "Manual points" else 3,
            )
            normalized = normalize_flux(cropped_flux, continuum)
            st.session_state.continuum = continuum
            st.session_state.normalized = normalized
            st.session_state.normalization_context = current_context
            if normalization_method == "Manual points":
                st.session_state.manual_selection_active = False
            st.rerun()
        except Exception as exc:
            st.error(f"Could not normalize: {exc}")
    st.caption("The continuum and normalized spectrum are updated only from the Crop and normalization panel.")

    normalized_title, compare_button = st.columns([4.2, 1.3], vertical_alignment="center")
    normalized_title.subheader("Cropped and normalized spectrum")
    comparison_button_label = (
        "Hide MK comparison" if st.session_state.show_mk_sequence else "Compare to MK sequence"
    )
    if compare_button.button(comparison_button_label, use_container_width=True):
        st.session_state.show_mk_sequence = not st.session_state.show_mk_sequence
        st.rerun()
    dib_detections: list[DIBDetection] = []
    if dib_is_detector and normalized is not None:
        dib_detections = detect_dib_is_features(
            cropped_wl,
            normalized,
            min_signal_to_noise=float(dib_sensitivity),
        )
    normalized_fig = render_normalized_plot(
        cropped_wl,
        normalized,
        line_families,
        show_line_labels,
        dib_detections,
    )
    st.plotly_chart(normalized_fig, width="stretch")
    if dib_is_detector and normalized is None:
        st.info("Compute the normalization first to run the DIB/IS detector.")
    elif dib_is_detector and dib_detections:
        st.caption("Possible interstellar absorptions detected. Green bands mark the local integration windows.")
        st.dataframe(
            [
                {
                    "Type": detection.kind,
                    "Feature": detection.label,
                    "lambda_ref": detection.wavelength,
                    "center": detection.center,
                    "depth": detection.depth,
                    "S/N": detection.signal_to_noise,
                    "EW": detection.equivalent_width,
                }
                for detection in dib_detections
            ],
            width="stretch",
        )
    elif dib_is_detector:
        st.caption("No DIB/IS candidate passed the current detection threshold in this wavelength range.")

    if st.session_state.show_mk_sequence and normalized is None:
        st.warning("Compute the normalization before comparing the studied spectrum with the MK sequence.")
    elif st.session_state.show_mk_sequence:
        try:
            with st.spinner("Loading the JHC main-sequence reference from MAST..."):
                mk_sequence = cached_mk_main_sequence()
            mk_left, mk_plot, mk_right = st.columns([0.06, 0.88, 0.06])
            with mk_plot:
                st.plotly_chart(
                    render_mk_comparison_plot(
                        cropped_wl,
                        normalized,
                        spectrum.source_name,
                        mk_sequence,
                        float(cropped_wl[0]),
                        float(cropped_wl[-1]),
                    ),
                    width="stretch",
                )
                st.caption(
                    "Top: studied spectrum. Below: JHC/MAST O5 V, B4 V, A5 V, F4 V, G4 V, K4 V and M5 V. "
                    "All curves share the same wavelength scale and vertical contrast ×1.6."
                )
        except Exception as exc:
            st.error(f"Could not load the online MK reference sequence: {exc}")

    if st.session_state.measurement_mode and normalized is not None:
        mode_label = "equivalent width" if st.session_state.measurement_mode == "ew" else "line ratio"
        st.caption(f"Click mode active for {mode_label}.")
        active_points = (
            st.session_state.ew_clicks
            if st.session_state.measurement_mode == "ew"
            else st.session_state.ratio_clicks
        )
        measure_result = continuum_click_selector(
            cropped_wl,
            normalized,
            active_points,
            key=f"measurement_click_selector_{st.session_state.measurement_mode}",
            window_size=1,
            hint=f"Click on the normalized spectrum to measure {mode_label}.",
        )
        clicked_point = point_from_click(getattr(measure_result, "clicked", None))
        if clicked_point:
            if st.session_state.measurement_mode == "ew":
                st.session_state.ew_clicks.append(clicked_point)
                if len(st.session_state.ew_clicks) >= 2:
                    left, right = st.session_state.ew_clicks[:2]
                    ew = equivalent_width(cropped_wl, normalized, left[0], right[0])
                    center = 0.5 * (left[0] + right[0])
                    line_info = line_metadata(center)
                    st.session_state.ew_results.append(
                        {
                            "Element": line_info["Element"],
                            "Line": line_info["Line"],
                            "lambda_ref": line_info["lambda_ref"],
                            "start": min(left[0], right[0]),
                            "end": max(left[0], right[0]),
                            "EW": ew,
                        }
                    )
                    st.session_state.ew_clicks = []
                    st.session_state.measurement_mode = None
                st.rerun()
            elif st.session_state.measurement_mode == "ratio":
                st.session_state.ratio_clicks.append(clicked_point)
                if len(st.session_state.ratio_clicks) >= 2:
                    first, second = st.session_state.ratio_clicks[:2]
                    c1, f1, i1 = line_center_and_intensity(cropped_wl, normalized, first[0], line_center_half_window)
                    c2, f2, i2 = line_center_and_intensity(cropped_wl, normalized, second[0], line_center_half_window)
                    first_line = line_metadata(c1)
                    second_line = line_metadata(c2)
                    ratio = float(i1 / i2) if abs(i2) > 0 else np.nan
                    st.session_state.ratio_results.append(
                        {
                            "Element 1": first_line["Element"],
                            "Line 1": first_line["Line"],
                            "lambda_ref_1": first_line["lambda_ref"],
                            "center_1": c1,
                            "intensity_1": i1,
                            "Element 2": second_line["Element"],
                            "Line 2": second_line["Line"],
                            "lambda_ref_2": second_line["lambda_ref"],
                            "center_2": c2,
                            "intensity_2": i2,
                            "ratio_1_2": ratio,
                        }
                    )
                    st.session_state.ratio_clicks = []
                    st.session_state.measurement_mode = None
                st.rerun()
    elif st.session_state.measurement_mode and normalized is None:
        st.warning("Compute the normalization first to use click-measurement modes.")

    evidence_tab, classification_tab = st.tabs(["Evidence", "Classification"])

    with evidence_tab:
        ew_block, ratio_block = st.columns(2)

        with ew_block:
            st.subheader("Equivalent width")
            st.caption("Activate click mode and select the integration start and end.")
            if st.button("Measure equivalent width", type="primary"):
                st.session_state.measurement_mode = "ew"
                st.session_state.ew_clicks = []
                st.session_state.ratio_clicks = []
                st.rerun()
            if st.session_state.measurement_mode == "ew":
                st.info(f"Clicks EW: {len(st.session_state.ew_clicks)}/2")
            if st.session_state.ew_results:
                st.dataframe(st.session_state.ew_results, width="stretch")
                if st.button("Clear EW table"):
                    st.session_state.ew_results = []
                    st.rerun()
            else:
                st.write("No EW measurements.")

        with ratio_block:
            st.subheader("Line ratio")
            st.caption("Activate click mode and select the two lines in the ratio order.")
            if st.button("Measure line ratio", type="primary"):
                st.session_state.measurement_mode = "ratio"
                st.session_state.ratio_clicks = []
                st.session_state.ew_clicks = []
                st.rerun()
            if st.session_state.measurement_mode == "ratio":
                st.info(f"Clicks ratio: {len(st.session_state.ratio_clicks)}/2")
            if st.session_state.ratio_results:
                st.dataframe(st.session_state.ratio_results, width="stretch")
                if st.button("Clear ratio table"):
                    st.session_state.ratio_results = []
                    st.rerun()
            else:
                st.write("No measured ratios.")

        spectral_evidence = st.text_area(
            "Commented spectral evidence",
            key="spectral_evidence",
            height=180,
            placeholder="Describe present, absent, or uncertain lines, feature ratios, and continuum quality.",
        )
        ew_notes = st.text_area(
            "Comments",
            key="ew_notes",
            height=120,
            placeholder="Add general comments about the evidence and measurements.",
        )

    with classification_tab:
        st.subheader("Assignment and justification")
        c1, c2 = st.columns(2)
        spectral_type = c1.text_input(
            "Assigned spectral type",
            key="spectral_type",
            placeholder="e.g. A0, B2, G5, M3",
        )
        luminosity_class = c2.text_input(
            "Luminosity class",
            key="luminosity_class",
            placeholder="e.g. V, IV, III, I",
        )
        confidence = c2.select_slider(
            "Confidence",
            options=["low", "medium", "high"],
            key="confidence",
        )
        spectral_type_reason = st.text_area("Spectral-type justification", key="spectral_type_reason", height=130)
        luminosity_reason = st.text_area("Luminosity-class justification", key="luminosity_reason", height=130)
        comments = st.text_area("General comments", key="classification_comments", height=110)
        st.caption(f"Declared confidence: {confidence}")

    ew_table = format_result_table(st.session_state.ew_results)
    ratio_table = format_result_table(st.session_state.ratio_results)

    student_name = st.session_state.get("report_student_name", "")
    course = st.session_state.get("report_course", "")
    output_pdf_name = pdf_file_name(st.session_state.get("report_output_name", ""))

    report = build_markdown_report(
        student_name=student_name,
        course=course,
        spectrum_name=spectrum.source_name,
        source_type=spectrum.source_type,
        wavelength_range=(float(cropped_wl[0]), float(cropped_wl[-1])),
        normalization_method=normalization_method,
        spectral_evidence=spectral_evidence,
        ew_notes=ew_notes,
        ew_table=ew_table,
        ratio_table=ratio_table,
        spectral_type=spectral_type,
        spectral_type_reason=spectral_type_reason,
        luminosity_class=luminosity_class,
        luminosity_reason=luminosity_reason,
        comments=comments,
    )
    pdf_report = build_pdf_report(
        student_name=student_name,
        course=course,
        spectrum_name=spectrum.source_name,
        source_type=spectrum.source_type,
        wavelength_range=(float(cropped_wl[0]), float(cropped_wl[-1])),
        normalization_method=normalization_method,
        spectral_evidence=spectral_evidence,
        ew_notes=ew_notes,
        ew_table=ew_table,
        ratio_table=ratio_table,
        spectral_type=spectral_type,
        spectral_type_reason=spectral_type_reason,
        luminosity_class=luminosity_class,
        luminosity_reason=luminosity_reason,
        comments=comments,
        original_wavelength=spectrum.wavelength,
        original_flux=spectrum.flux,
        normalized_wavelength=cropped_wl,
        normalized_flux=normalized if normalized is not None else [],
    )
    pdf_download = pdf_report
    pdf_button_label = "Generate PDF report"
    if previous_report_pdf is not None:
        try:
            pdf_download = append_pdf_report(previous_report_pdf.getvalue(), pdf_report)
            pdf_button_label = "Generate appended PDF report"
        except Exception as exc:
            st.error(f"Could not append the report to the previous PDF: {exc}")

    with report_download_slot.container():
        st.download_button(
            pdf_button_label,
            data=pdf_download,
            file_name=output_pdf_name,
            mime="application/pdf",
            type="primary",
        )
        st.download_button(
            "Download Markdown",
            data=report,
            file_name="spectral_classification_report.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()

# Streamlit Spectral Classification Portal

Teaching-oriented Streamlit portal for inspecting, normalizing, measuring, and classifying stellar spectra.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Main Features

- FITS spectrum loading with basic WCS/spectral calibration support from headers.
- TXT/CSV loading with two columns: wavelength and flux.
- Scientific interactive visualization with two plots: original spectrum and cropped/normalized spectrum.
- Wavelength cropping shown as a shaded region on the original spectrum.
- Explicit normalization from the sidebar using Polynomial, Legendre, Cubic spline, or Manual points.
- Manual continuum point selection by click, with configurable spline degree and smoothing.
- Spectral-line overlays by family on the normalized spectrum.
- Equivalent-width measurements by two clicks.
- Line-ratio measurements by two clicks, preserving click order.
- Text fields for spectral evidence, classification, justification, and comments.
- PDF and Markdown report generation.
- Appending the current PDF report to a previous report PDF.

## Interface Layout

- Sidebar panel 1: spectrum upload.
- Sidebar panel 2: crop and normalization.
- Sidebar panel 3: spectral-line display and line-centering parameters.
- Sidebar panel 4: student information and report generation.

See [HELP.md](HELP.md) for a detailed explanation of every panel and parameter.

## License

This project is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

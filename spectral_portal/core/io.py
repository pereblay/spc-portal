from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Spectrum:
    wavelength: np.ndarray
    flux: np.ndarray
    source_name: str
    source_type: str
    metadata: dict[str, str]

    @property
    def size(self) -> int:
        return int(self.wavelength.size)

    @property
    def wavelength_min(self) -> float:
        return float(np.nanmin(self.wavelength))

    @property
    def wavelength_max(self) -> float:
        return float(np.nanmax(self.wavelength))


def _clean_arrays(wavelength: np.ndarray, flux: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    wavelength = np.asarray(wavelength, dtype=float).ravel()
    flux = np.asarray(flux, dtype=float).ravel()
    valid = np.isfinite(wavelength) & np.isfinite(flux)
    wavelength = wavelength[valid]
    flux = flux[valid]
    order = np.argsort(wavelength)
    return wavelength[order], flux[order]


def _read_fits_wavelength(header, n_pixels: int) -> tuple[np.ndarray, dict[str, str]]:
    metadata: dict[str, str] = {}
    crval = header.get("CRVAL1")
    cdelt = header.get("CDELT1", header.get("CD1_1"))
    crpix = header.get("CRPIX1", 1.0)
    cunit = header.get("CUNIT1", "")
    ctype = header.get("CTYPE1", "")

    if crval is not None and cdelt is not None:
        pixels = np.arange(n_pixels, dtype=float) + 1.0
        wavelength = float(crval) + (pixels - float(crpix)) * float(cdelt)
        metadata.update(
            {
                "CRVAL1": str(crval),
                "CDELT1/CD1_1": str(cdelt),
                "CRPIX1": str(crpix),
                "CUNIT1": str(cunit),
                "CTYPE1": str(ctype),
            }
        )
        return wavelength, metadata

    try:
        from astropy.wcs import WCS

        wcs = WCS(header)
        pixels = np.arange(n_pixels, dtype=float)
        wavelength = wcs.pixel_to_world_values(pixels)
        if isinstance(wavelength, tuple):
            wavelength = wavelength[0]
        metadata["WCS"] = "pixel_to_world_values"
        return np.asarray(wavelength, dtype=float), metadata
    except Exception as exc:
        raise ValueError(
            "Could not reconstruct the wavelength array from the FITS header."
        ) from exc


def load_fits(uploaded_file) -> Spectrum:
    from astropy.io import fits

    payload = uploaded_file.getvalue()
    with fits.open(BytesIO(payload), memmap=False) as hdul:
        hdu = next((item for item in hdul if item.data is not None), None)
        if hdu is None:
            raise ValueError("The FITS file does not contain spectral data.")

        data = np.asarray(hdu.data)
        header = hdu.header

        if data.ndim > 1:
            data = np.squeeze(data)
        if data.ndim != 1:
            raise ValueError("This version expects 1D FITS spectra.")

        flux = data.astype(float)
        wavelength, metadata = _read_fits_wavelength(header, flux.size)
        wavelength, flux = _clean_arrays(wavelength, flux)
        metadata["HDU"] = hdu.name or "PRIMARY"

    return Spectrum(wavelength, flux, uploaded_file.name, "FITS", metadata)


def load_txt(uploaded_file) -> Spectrum:
    raw = uploaded_file.getvalue().decode("utf-8", errors="replace")
    frame = pd.read_csv(
        StringIO(raw),
        comment="#",
        sep=None,
        engine="python",
        header=None,
    )
    if frame.shape[1] < 2:
        raise ValueError("The TXT file must have at least two columns: wavelength and flux.")
    wavelength, flux = _clean_arrays(frame.iloc[:, 0].to_numpy(), frame.iloc[:, 1].to_numpy())
    return Spectrum(
        wavelength,
        flux,
        uploaded_file.name,
        "TXT",
        {"columns": "0: wavelength, 1: flux"},
    )


def load_example() -> Spectrum:
    wavelength = np.linspace(3800.0, 7200.0, 3500)
    continuum = 1.2 + 0.00007 * (wavelength - 5500.0) + 0.06 * np.sin(wavelength / 360.0)
    flux = continuum.copy()
    for center, depth, sigma in [
        (4101.7, 0.20, 5.0),
        (4340.5, 0.28, 6.0),
        (4861.3, 0.34, 8.0),
        (6562.8, 0.22, 10.0),
        (4471.5, 0.08, 4.0),
        (4481.2, 0.07, 4.0),
        (3933.7, 0.18, 3.0),
    ]:
        flux -= depth * np.exp(-0.5 * ((wavelength - center) / sigma) ** 2)
    rng = np.random.default_rng(42)
    flux += rng.normal(0.0, 0.012, wavelength.size)
    return Spectrum(
        wavelength,
        flux,
        "teaching_example_A-F.txt",
        "Example",
        {"synthetic": "true"},
    )


def load_spectrum(uploaded_file) -> Spectrum:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in {".fits", ".fit", ".fts"}:
        return load_fits(uploaded_file)
    if suffix in {".txt", ".dat", ".csv", ".tsv"}:
        return load_txt(uploaded_file)
    raise ValueError("Unsupported format. Use FITS, TXT, DAT, CSV, or TSV.")

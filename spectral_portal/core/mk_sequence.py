from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import ssl
from urllib.request import urlopen

import certifi
import numpy as np
from astropy.io import fits
from scipy.ndimage import gaussian_filter1d, percentile_filter


MAST_JHC_BASE_URL = "https://archive.stsci.edu/hlsps/reference-atlases/cdbs/grid/jacobi"


@dataclass(frozen=True)
class MKReference:
    spectral_type: str
    star: str
    filename: str

    @property
    def url(self) -> str:
        return f"{MAST_JHC_BASE_URL}/{self.filename}"


MK_MAIN_SEQUENCE: tuple[MKReference, ...] = (
    MKReference("O5 V", "HD 242908", "jc_1.fits"),
    MKReference("B4 V", "FEIGE 40", "jc_15.fits"),
    MKReference("A5 V", "HD 9547", "jc_25.fits"),
    MKReference("F4 V", "HD 23511", "jc_33.fits"),
    MKReference("G4 V", "Tr A14", "jc_47.fits"),
    MKReference("K4 V", "HD 5351", "jc_53.fits"),
    MKReference("M5 V", "YALE 1755", "jc_57.fits"),
)


def _normalize_pseudocontinuum(wavelength: np.ndarray, flux: np.ndarray) -> np.ndarray:
    positive = flux[np.isfinite(flux) & (flux > 0)]
    scale = float(np.nanmedian(positive)) if positive.size else 1.0
    scaled = flux / scale
    sampling = float(np.nanmedian(np.diff(wavelength)))
    percentile_window = max(9, int(round(42.0 / sampling)))
    if percentile_window % 2 == 0:
        percentile_window += 1
    upper_envelope = percentile_filter(scaled, percentile=92, size=percentile_window, mode="nearest")
    continuum = gaussian_filter1d(upper_envelope, sigma=max(2.0, 24.0 / sampling), mode="nearest")
    valid_continuum = continuum[np.isfinite(continuum) & (continuum > 0)]
    fallback = float(np.nanmedian(valid_continuum)) if valid_continuum.size else 1.0
    continuum = np.where(np.isfinite(continuum) & (continuum > 0), continuum, fallback)
    normalized = scaled / continuum
    high_points = normalized[normalized >= np.nanpercentile(normalized, 80)]
    anchor = float(np.nanmedian(high_points)) if high_points.size else 1.0
    return normalized / anchor


def load_mk_reference(
    reference: MKReference,
    wavelength_min: float = 3510.0,
    wavelength_max: float = 7427.0,
) -> dict[str, object]:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(reference.url, timeout=30, context=ssl_context) as response:
        payload = response.read()
    with fits.open(BytesIO(payload), memmap=False) as hdul:
        table = hdul[1].data
        wavelength = np.asarray(table["WAVELENGTH"], dtype=float)
        flux = np.asarray(table["FLUX"], dtype=float)
    valid = (
        np.isfinite(wavelength)
        & np.isfinite(flux)
        & (wavelength >= float(wavelength_min))
        & (wavelength <= float(wavelength_max))
    )
    wavelength = wavelength[valid]
    flux = flux[valid]
    if wavelength.size < 3:
        raise ValueError(f"{reference.filename} has no usable data in the requested wavelength range.")
    return {
        "spectral_type": reference.spectral_type,
        "star": reference.star,
        "wavelength": wavelength,
        "normalized_flux": _normalize_pseudocontinuum(wavelength, flux),
        "source_url": reference.url,
    }


def load_main_sequence() -> list[dict[str, object]]:
    return [load_mk_reference(reference) for reference in MK_MAIN_SEQUENCE]

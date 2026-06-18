from __future__ import annotations

import numpy as np


def crop_spectrum(
    wavelength: np.ndarray, flux: np.ndarray, wavelength_min: float, wavelength_max: float
) -> tuple[np.ndarray, np.ndarray]:
    lo, hi = sorted((float(wavelength_min), float(wavelength_max)))
    mask = (wavelength >= lo) & (wavelength <= hi)
    return wavelength[mask], flux[mask]


def equivalent_width(
    wavelength: np.ndarray,
    normalized_flux: np.ndarray,
    left: float,
    right: float,
) -> float:
    lo, hi = sorted((float(left), float(right)))
    mask = (wavelength >= lo) & (wavelength <= hi)
    if np.count_nonzero(mask) < 2:
        raise ValueError("The selected interval does not contain enough points.")
    return float(np.trapezoid(1.0 - normalized_flux[mask], wavelength[mask]))


def line_center_and_intensity(
    wavelength: np.ndarray,
    normalized_flux: np.ndarray,
    approximate_center: float,
    half_window: float,
) -> tuple[float, float, float]:
    center = float(approximate_center)
    half_window = abs(float(half_window))
    mask = (wavelength >= center - half_window) & (wavelength <= center + half_window)
    if np.count_nonzero(mask) < 2:
        raise ValueError("There are not enough points around the selected line.")
    local_wavelength = wavelength[mask]
    local_flux = normalized_flux[mask]
    min_index = int(np.nanargmin(local_flux))
    real_center = float(local_wavelength[min_index])
    flux_at_center = float(local_flux[min_index])
    intensity = float(1.0 - flux_at_center)
    return real_center, flux_at_center, intensity

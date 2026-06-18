from __future__ import annotations

import numpy as np
from numpy.polynomial import Legendre, Polynomial


def fit_continuum(
    wavelength: np.ndarray,
    flux: np.ndarray,
    method: str,
    degree: int = 3,
    manual_points: list[tuple[float, float]] | None = None,
    spline_smoothing: float | None = None,
    spline_degree: int = 3,
) -> np.ndarray:
    wavelength = np.asarray(wavelength, dtype=float)
    flux = np.asarray(flux, dtype=float)

    if wavelength.size < 2:
        raise ValueError("There are not enough points to fit the continuum.")

    if method == "Manual points":
        points = manual_points or []
        spline_degree = int(np.clip(spline_degree, 1, 5))
        if len(points) <= spline_degree:
            raise ValueError(f"Select at least {spline_degree + 1} continuum points to fit this spline.")
        xp = np.asarray([p[0] for p in points], dtype=float)
        yp = np.asarray([p[1] for p in points], dtype=float)
        order = np.argsort(xp)
        xp = xp[order]
        yp = yp[order]
        unique_xp, unique_idx = np.unique(xp, return_index=True)
        unique_yp = yp[unique_idx]
        if unique_xp.size <= spline_degree:
            raise ValueError(f"Continuum points must include at least {spline_degree + 1} distinct wavelengths.")
        try:
            from scipy.interpolate import UnivariateSpline
        except ImportError as exc:
            raise ValueError("Manual-point fitting requires scipy.") from exc
        smoothing = 0.0 if spline_smoothing is None else float(spline_smoothing)
        spline = UnivariateSpline(unique_xp, unique_yp, k=spline_degree, s=smoothing)
        return spline(wavelength)

    if method == "Cubic spline":
        try:
            from scipy.interpolate import UnivariateSpline
        except ImportError as exc:
            raise ValueError("Spline normalization requires scipy.") from exc
        smoothing = spline_smoothing
        if smoothing is None:
            smoothing = wavelength.size * np.nanvar(flux) * 0.002
        spline = UnivariateSpline(wavelength, flux, k=3, s=smoothing)
        return spline(wavelength)

    degree = max(1, int(degree))
    if method == "Legendre":
        model = Legendre.fit(wavelength, flux, degree)
        return model(wavelength)

    model = Polynomial.fit(wavelength, flux, degree)
    return model(wavelength)


def normalize_flux(flux: np.ndarray, continuum: np.ndarray) -> np.ndarray:
    continuum = np.asarray(continuum, dtype=float)
    normalized = np.full_like(np.asarray(flux, dtype=float), np.nan)
    valid = np.isfinite(continuum) & (np.abs(continuum) > 0)
    normalized[valid] = flux[valid] / continuum[valid]
    return normalized


def parse_manual_points(text: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.replace(",", " ")
        parts = [part for part in line.split() if part]
        if len(parts) < 2:
            continue
        points.append((float(parts[0]), float(parts[1])))
    return points

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class InterstellarFeature:
    kind: str
    label: str
    wavelength: float
    fwhm: float
    note: str = ""


@dataclass(frozen=True)
class DIBDetection:
    kind: str
    label: str
    wavelength: float
    center: float
    depth: float
    signal_to_noise: float
    equivalent_width: float
    x0: float
    x1: float


INTERSTELLAR_FEATURES: tuple[InterstellarFeature, ...] = (
    InterstellarFeature("IS", "Ca II K IS", 3933.66, 0.45, "interstellar Ca II"),
    InterstellarFeature("IS", "Ca II H IS", 3968.47, 0.45, "interstellar Ca II"),
    InterstellarFeature("IS", "CH+ 4232", 4232.55, 0.35, "interstellar CH+"),
    InterstellarFeature("IS", "CH 4300", 4300.31, 0.35, "interstellar CH"),
    InterstellarFeature("DIB", "DIB 4428", 4428.0, 18.0, "very broad DIB"),
    InterstellarFeature("DIB", "DIB 4726", 4726.8, 2.8),
    InterstellarFeature("DIB", "DIB 4762", 4762.6, 2.0),
    InterstellarFeature("DIB", "DIB 4964", 4963.9, 1.1),
    InterstellarFeature("DIB", "DIB 5487", 5487.7, 5.0),
    InterstellarFeature("DIB", "DIB 5705", 5705.1, 2.6),
    InterstellarFeature("DIB", "DIB 5780", 5780.48, 2.1, "strong DIB"),
    InterstellarFeature("DIB", "DIB 5797", 5796.94, 0.9, "strong DIB"),
    InterstellarFeature("DIB", "DIB 5849", 5849.8, 1.2),
    InterstellarFeature("IS", "Na I D2 IS", 5889.95, 0.45, "interstellar sodium"),
    InterstellarFeature("IS", "Na I D1 IS", 5895.92, 0.45, "interstellar sodium"),
    InterstellarFeature("DIB", "DIB 6196", 6196.0, 0.5, "narrow DIB"),
    InterstellarFeature("DIB", "DIB 6203", 6203.6, 1.5),
    InterstellarFeature("DIB", "DIB 6270", 6270.0, 2.0),
    InterstellarFeature("DIB", "DIB 6284", 6283.8, 4.0, "strong DIB"),
    InterstellarFeature("DIB", "DIB 6379", 6379.3, 0.8),
    InterstellarFeature("DIB", "DIB 6614", 6613.64, 0.9, "strong DIB"),
    InterstellarFeature("DIB", "DIB 6661", 6660.7, 0.7),
    InterstellarFeature("DIB", "DIB 6993", 6993.2, 1.0),
    InterstellarFeature("DIB", "DIB 7224", 7224.0, 1.3),
    InterstellarFeature("IS", "K I 7665 IS", 7664.9, 0.45, "interstellar potassium"),
    InterstellarFeature("IS", "K I 7699 IS", 7698.96, 0.45, "interstellar potassium"),
    InterstellarFeature("DIB", "DIB 8620", 8620.4, 5.5, "Gaia/RVS-region DIB"),
)


def candidate_features(wavelength: np.ndarray) -> list[InterstellarFeature]:
    if wavelength.size == 0:
        return []
    wl_min = float(np.nanmin(wavelength))
    wl_max = float(np.nanmax(wavelength))
    return [feature for feature in INTERSTELLAR_FEATURES if wl_min <= feature.wavelength <= wl_max]


def _robust_std(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if values.size < 3:
        return 0.0
    median = np.nanmedian(values)
    mad = np.nanmedian(np.abs(values - median))
    if mad > 0:
        return float(1.4826 * mad)
    return float(np.nanstd(values))


def detect_dib_is_features(
    wavelength: np.ndarray,
    normalized_flux: np.ndarray,
    *,
    min_depth: float = 0.01,
    min_signal_to_noise: float = 2.5,
) -> list[DIBDetection]:
    x = np.asarray(wavelength, dtype=float).ravel()
    y = np.asarray(normalized_flux, dtype=float).ravel()
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    detections: list[DIBDetection] = []

    for feature in candidate_features(x):
        core_half_width = max(feature.fwhm * 0.75, 0.35)
        search_half_width = max(feature.fwhm * 1.8, 1.2)
        side_half_width = max(feature.fwhm * 3.0, 2.5)

        search_mask = (x >= feature.wavelength - search_half_width) & (x <= feature.wavelength + search_half_width)
        core_mask = (x >= feature.wavelength - core_half_width) & (x <= feature.wavelength + core_half_width)
        side_mask = (
            (x >= feature.wavelength - side_half_width)
            & (x <= feature.wavelength + side_half_width)
            & ~core_mask
        )
        if np.count_nonzero(search_mask) < 3 or np.count_nonzero(core_mask) < 2:
            continue

        local_x = x[search_mask]
        local_y = y[search_mask]
        local_min_index = int(np.nanargmin(local_y))
        center = float(local_x[local_min_index])
        local_min_flux = float(local_y[local_min_index])

        if np.count_nonzero(side_mask) >= 4:
            continuum_level = float(np.nanmedian(y[side_mask]))
            noise = _robust_std(y[side_mask] - continuum_level)
        else:
            continuum_level = 1.0
            noise = _robust_std(y[search_mask] - np.nanmedian(y[search_mask]))

        depth = max(0.0, continuum_level - local_min_flux)
        if noise <= 0:
            noise = max(_robust_std(y - np.nanmedian(y)), 1e-6)
        signal_to_noise = depth / max(noise, 1e-6)

        integration_mask = (x >= center - core_half_width) & (x <= center + core_half_width)
        if np.count_nonzero(integration_mask) < 2:
            continue
        equivalent_width = float(np.trapezoid(np.maximum(0.0, continuum_level - y[integration_mask]), x[integration_mask]))

        if depth >= min_depth and signal_to_noise >= min_signal_to_noise and equivalent_width > 0:
            detections.append(
                DIBDetection(
                    kind=feature.kind,
                    label=feature.label,
                    wavelength=feature.wavelength,
                    center=center,
                    depth=depth,
                    signal_to_noise=signal_to_noise,
                    equivalent_width=equivalent_width,
                    x0=max(float(np.nanmin(x)), center - core_half_width),
                    x1=min(float(np.nanmax(x)), center + core_half_width),
                )
            )

    return detections

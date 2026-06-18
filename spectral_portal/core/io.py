from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import Path
import warnings

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


@dataclass
class FitsHduInfo:
    index: int
    name: str
    shape: str
    data_type: str
    supported: bool
    wcs_ok: bool
    message: str


def _clean_arrays(wavelength: np.ndarray, flux: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    wavelength = np.asarray(wavelength, dtype=float).ravel()
    flux = np.asarray(flux, dtype=float).ravel()
    valid = np.isfinite(wavelength) & np.isfinite(flux)
    wavelength = wavelength[valid]
    flux = flux[valid]
    order = np.argsort(wavelength)
    return wavelength[order], flux[order]


def _header_metadata(header, keys: tuple[str, ...]) -> dict[str, str]:
    return {key: str(header[key]) for key in keys if key in header}


def _read_fits_wavelength(header, n_pixels: int) -> tuple[np.ndarray, dict[str, str]]:
    metadata: dict[str, str] = {}
    crval = header.get("CRVAL1")
    cdelt = header.get("CDELT1", header.get("CD1_1"))
    crpix = header.get("CRPIX1", 1.0)
    cunit = header.get("CUNIT1", "")
    ctype = header.get("CTYPE1", header.get("CTYPE", ""))

    if crval is not None and cdelt is not None:
        pixels = np.arange(n_pixels, dtype=float) + 1.0
        wavelength = float(crval) + (pixels - float(crpix)) * float(cdelt)
        if str(header.get("DC-FLAG", "")).strip() == "1" and np.nanmax(wavelength) < 10:
            wavelength = np.power(10.0, wavelength)
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

    w0 = header.get("W0")
    wpc = header.get("WPC")
    if w0 is not None and wpc is not None:
        pixels = np.arange(n_pixels, dtype=float)
        wavelength = float(w0) + pixels * float(wpc)
        metadata.update({"W0": str(w0), "WPC": str(wpc), "CUNIT1": str(cunit), "CTYPE1/CTYPE": str(ctype)})
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


def _table_spectrum(data) -> tuple[np.ndarray, np.ndarray, dict[str, str]] | None:
    names = getattr(data, "names", None)
    if not names:
        return None

    lowered = {name.lower().replace("_", "").replace("-", ""): name for name in names}
    wavelength_candidates = (
        "wavelength",
        "wave",
        "lambda",
        "lam",
        "wl",
        "wavelengthair",
        "wavelengthvac",
        "loglam",
        "loglambda",
    )
    flux_candidates = (
        "flux",
        "flam",
        "intensity",
        "counts",
        "count",
        "spec",
        "spectrum",
        "data",
        "net",
        "science",
    )
    wavelength_name = next((lowered[name] for name in wavelength_candidates if name in lowered), None)
    flux_name = next((lowered[name] for name in flux_candidates if name in lowered), None)
    if wavelength_name is None or flux_name is None:
        return None

    metadata = {"table_columns": f"{wavelength_name}: wavelength, {flux_name}: flux"}
    wavelength = np.asarray(data[wavelength_name], dtype=float)
    flux = np.asarray(data[flux_name], dtype=float)
    if wavelength.ndim > 1:
        wavelength = np.squeeze(wavelength)
        if wavelength.ndim > 1:
            wavelength = wavelength[0]
    if flux.ndim > 1:
        flux = np.squeeze(flux)
        if flux.ndim > 1:
            flux = flux[0]
    if wavelength_name.lower().replace("_", "").replace("-", "") in {"loglam", "loglambda"}:
        wavelength = np.power(10.0, wavelength)
        metadata["wavelength_scale"] = "10**loglam"
    return wavelength, flux, metadata


def _table_length(data) -> int:
    names = getattr(data, "names", None)
    if names:
        return int(len(data[names[0]]))
    return int(len(data))


def _image_flux_array(data: np.ndarray) -> tuple[np.ndarray, dict[str, str]]:
    array = np.asarray(data)
    if array.ndim > 1:
        array = np.squeeze(array)
    if array.ndim == 1:
        return array.astype(float), {"data_shape": str(tuple(np.asarray(data).shape))}
    if array.ndim == 2:
        usable_rows = [
            (index, row)
            for index, row in enumerate(array)
            if np.count_nonzero(np.isfinite(row)) > 1
        ]
        if not usable_rows:
            raise ValueError("The FITS image does not contain a usable spectral row.")
        selected_index, selected_row = usable_rows[0]
        return np.asarray(selected_row, dtype=float), {
            "data_shape": str(tuple(np.asarray(data).shape)),
            "selected_row": str(selected_index),
        }
    raise ValueError("This version expects 1D spectra, spectral tables, or simple 2D FITS spectra.")


def _open_fits_payload(payload: bytes):
    from astropy.io import fits

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fits.open(
            BytesIO(payload),
            memmap=False,
            lazy_load_hdus=False,
            ignore_missing_simple=True,
        )


def _spectrum_from_hdu(hdu) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    header = hdu.header
    table_result = _table_spectrum(hdu.data)
    if table_result is not None:
        return table_result

    flux, metadata = _image_flux_array(np.asarray(hdu.data))
    wavelength, wavelength_metadata = _read_fits_wavelength(header, flux.size)
    metadata.update(wavelength_metadata)
    return wavelength, flux, metadata


def inspect_fits_hdus(uploaded_file) -> list[FitsHduInfo]:
    payload = uploaded_file.getvalue()
    infos: list[FitsHduInfo] = []
    with _open_fits_payload(payload) as hdul:
        for index, hdu in enumerate(hdul):
            data = hdu.data
            if data is None:
                infos.append(
                    FitsHduInfo(
                        index=index,
                        name=hdu.name or "PRIMARY",
                        shape="None",
                        data_type=type(hdu).__name__,
                        supported=False,
                        wcs_ok=False,
                        message="No data in this HDU.",
                    )
                )
                continue

            shape = str(getattr(data, "shape", (_table_length(data),)))
            data_type = type(hdu).__name__
            try:
                wavelength, flux, _ = _spectrum_from_hdu(hdu)
                wavelength, flux = _clean_arrays(wavelength, flux)
                wcs_ok = bool(wavelength.size > 1 and np.nanmax(wavelength) > np.nanmin(wavelength))
                if wcs_ok:
                    message = f"Readable spectrum, {wavelength.size} points, WCS {wavelength[0]:.3f}-{wavelength[-1]:.3f}."
                else:
                    message = "Readable data, but wavelength calibration is not valid."
                infos.append(
                    FitsHduInfo(
                        index=index,
                        name=hdu.name or "PRIMARY",
                        shape=shape,
                        data_type=data_type,
                        supported=wcs_ok and flux.size > 1,
                        wcs_ok=wcs_ok,
                        message=message,
                    )
                )
            except Exception as exc:
                infos.append(
                    FitsHduInfo(
                        index=index,
                        name=hdu.name or "PRIMARY",
                        shape=shape,
                        data_type=data_type,
                        supported=False,
                        wcs_ok=False,
                        message=str(exc),
                    )
                )
    return infos


def load_fits(uploaded_file, hdu_index: int | None = None) -> Spectrum:
    payload = uploaded_file.getvalue()
    hdul = _open_fits_payload(payload)
    with hdul:
        if hdu_index is not None:
            if hdu_index < 0 or hdu_index >= len(hdul):
                raise ValueError(f"The FITS file does not contain HDU {hdu_index}.")
            hdu = hdul[hdu_index]
            if hdu.data is None:
                raise ValueError(f"HDU {hdu_index} does not contain spectral data.")
            wavelength, flux, metadata = _spectrum_from_hdu(hdu)
        else:
            last_error: Exception | None = None
            for candidate in hdul:
                if candidate.data is None:
                    continue
                try:
                    wavelength, flux, metadata = _spectrum_from_hdu(candidate)
                    hdu = candidate
                    break
                except Exception as exc:
                    last_error = exc
            else:
                if last_error is not None:
                    raise ValueError(f"No readable FITS spectrum found: {last_error}") from last_error
                raise ValueError("The FITS file does not contain spectral data.")

        header = hdu.header
        wavelength, flux = _clean_arrays(wavelength, flux)
        if wavelength.size < 2 or flux.size < 2:
            raise ValueError("The selected FITS HDU does not contain enough valid spectral points.")
        metadata["HDU"] = hdu.name or "PRIMARY"
        metadata["HDU_INDEX"] = str(hdu_index if hdu_index is not None else list(hdul).index(hdu))
        metadata.update(
            _header_metadata(
                header,
                ("OBJECT", "SP_TYPE", "BUNIT", "ORIGIN", "DATE", "IRAF-TLM", "DC-FLAG"),
            )
        )

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

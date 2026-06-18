from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpectralLine:
    family: str
    label: str
    wavelength: float
    note: str = ""


POPULAR_LINES: tuple[SpectralLine, ...] = (
    SpectralLine("H", "H alpha", 6562.8, "Balmer"),
    SpectralLine("H", "H beta", 4861.3, "Balmer"),
    SpectralLine("H", "H gamma", 4340.5, "Balmer"),
    SpectralLine("H", "H delta", 4101.7, "Balmer"),
    SpectralLine("H", "H epsilon", 3970.1, "Balmer"),
    SpectralLine("He I", "He I 4026", 4026.2),
    SpectralLine("He I", "He I 4471", 4471.5),
    SpectralLine("He I", "He I 5876", 5875.6),
    SpectralLine("He II", "He II 4200", 4200.0),
    SpectralLine("He II", "He II 4542", 4541.6),
    SpectralLine("He II", "He II 4686", 4685.7),
    SpectralLine("CNO", "C III 4647", 4647.4),
    SpectralLine("CNO", "N III 4640", 4640.6),
    SpectralLine("CNO", "O III 5592", 5592.3),
    SpectralLine("Mg/Si/S", "Mg II 4481", 4481.2),
    SpectralLine("Mg/Si/S", "Si II 4128", 4128.1),
    SpectralLine("Mg/Si/S", "Si III 4553", 4552.6),
    SpectralLine("Mg/Si/S", "Si IV 4089", 4088.9),
    SpectralLine("Mg/Si/S", "S II 5454", 5453.8),
    SpectralLine("Fe", "Fe I 4383", 4383.5),
    SpectralLine("Fe", "Fe I 5270", 5269.5),
    SpectralLine("Fe", "Fe II 4233", 4233.2),
    SpectralLine("Ca", "Ca II K", 3933.7),
    SpectralLine("Ca", "Ca II H", 3968.5),
    SpectralLine("Na", "Na I D2", 5889.9),
    SpectralLine("Na", "Na I D1", 5895.9),
    SpectralLine("TiO", "TiO band 5167", 5167.0, "Molecular bandhead"),
    SpectralLine("TiO", "TiO band 5448", 5448.0, "Molecular bandhead"),
    SpectralLine("TiO", "TiO band 6159", 6159.0, "Molecular bandhead"),
    SpectralLine("TiO", "TiO band 7054", 7054.0, "Molecular bandhead"),
)


LINE_COLORS = {
    "H": "#343a40",
    "He I": "#1f77b4",
    "He II": "#274b8e",
    "CNO": "#2ca02c",
    "Mg/Si/S": "#9467bd",
    "Fe": "#8c564b",
    "Ca": "#ff7f0e",
    "Na": "#bcbd22",
    "TiO": "#17becf",
}


def families() -> list[str]:
    return sorted({line.family for line in POPULAR_LINES})


def selected_lines(selected_families: list[str]) -> list[SpectralLine]:
    selected = set(selected_families)
    return [line for line in POPULAR_LINES if line.family in selected]


def nearest_line(wavelength: float) -> SpectralLine:
    return min(POPULAR_LINES, key=lambda line: abs(line.wavelength - float(wavelength)))

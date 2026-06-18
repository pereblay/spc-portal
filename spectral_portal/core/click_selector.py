from __future__ import annotations

import numpy as np
import streamlit as st


_HTML = """
<div id="selector-root" class="selector-root"></div>
"""

_CSS = """
.selector-root {
  width: 100%;
  min-height: 430px;
  font-family: sans-serif;
}
.selector-root svg {
  width: 100%;
  height: 430px;
  display: block;
  background: #ffffff;
  cursor: crosshair;
}
.selector-root .axis-label {
  font-size: 13px;
  fill: #343a40;
}
.selector-root .tick-label {
  font-size: 12px;
  fill: #495057;
}
.selector-root .minor-tick-label {
  font-size: 11px;
  fill: #6c757d;
}
.selector-root .hint {
  margin-top: 6px;
  color: #495057;
  font-size: 13px;
}
"""

_JS = """
export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component
  const root = parentElement.querySelector("#selector-root")
  if (!root || !data) return

  const width = Math.max(root.clientWidth || 900, 500)
  const height = 430
  const margin = { left: 70, right: 24, top: 22, bottom: 58 }
  const plotW = width - margin.left - margin.right
  const plotH = height - margin.top - margin.bottom
  const x = data.wavelength || []
  const y = data.flux || []
  const points = data.points || []
  const windowSize = Math.max(1, Number(data.window_size || 15))
  const xmin = data.xmin
  const xmax = data.xmax
  const ymin = data.ymin
  const ymax = data.ymax
  const togglePoints = Boolean(data.toggle_points)

  function sx(value) {
    return margin.left + ((value - xmin) / (xmax - xmin)) * plotW
  }
  function sy(value) {
    return margin.top + (1 - ((value - ymin) / (ymax - ymin))) * plotH
  }
  function esc(value) {
    return String(value).replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[ch]))
  }
  function fmt(value) {
    const absValue = Math.abs(value)
    if (absValue >= 1000) return value.toFixed(0)
    if (absValue >= 100) return value.toFixed(1)
    if (absValue >= 10) return value.toFixed(2)
    return value.toFixed(3)
  }

  let polyline = ""
  for (let i = 0; i < x.length; i++) {
    const px = sx(x[i])
    const py = sy(y[i])
    if (Number.isFinite(px) && Number.isFinite(py)) polyline += `${px.toFixed(2)},${py.toFixed(2)} `
  }

  let grid = ""
  let tickLabels = ""
  const xTickCount = plotW > 900 ? 10 : plotW > 650 ? 8 : 6
  const yTickCount = 5
  for (let i = 0; i <= xTickCount; i++) {
    const fraction = i / xTickCount
    const xf = margin.left + fraction * plotW
    const value = xmin + fraction * (xmax - xmin)
    grid += `<line x1="${xf}" y1="${margin.top}" x2="${xf}" y2="${margin.top + plotH}" stroke="#e9ecef" />`
    grid += `<line x1="${xf}" y1="${margin.top + plotH}" x2="${xf}" y2="${margin.top + plotH + 5}" stroke="#495057" />`
    tickLabels += `<text x="${xf}" y="${height - 36}" text-anchor="middle" class="tick-label">${fmt(value)}</text>`
  }
  for (let i = 0; i <= yTickCount; i++) {
    const fraction = i / yTickCount
    const yf = margin.top + fraction * plotH
    const value = ymax - fraction * (ymax - ymin)
    grid += `<line x1="${margin.left}" y1="${yf}" x2="${margin.left + plotW}" y2="${yf}" stroke="#e9ecef" />`
    grid += `<line x1="${margin.left - 5}" y1="${yf}" x2="${margin.left}" y2="${yf}" stroke="#495057" />`
    tickLabels += `<text x="${margin.left - 9}" y="${yf + 4}" text-anchor="end" class="minor-tick-label">${fmt(value)}</text>`
  }

  let selected = ""
  for (const point of points) {
    const px = sx(point[0])
    const py = sy(point[1])
    if (Number.isFinite(px) && Number.isFinite(py)) {
      selected += `<circle cx="${px}" cy="${py}" r="5" fill="#fff" stroke="#d95f02" stroke-width="2" />`
    }
  }

  root.innerHTML = `
    <svg id="continuum-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Continuum selector">
      <rect x="${margin.left}" y="${margin.top}" width="${plotW}" height="${plotH}" fill="#e7f5ff" opacity="0.55" />
      ${grid}
      <polyline points="${polyline}" fill="none" stroke="#243b53" stroke-width="1.4" />
      ${selected}
      <rect x="${margin.left}" y="${margin.top}" width="${plotW}" height="${plotH}" fill="none" stroke="#212529" stroke-width="1.2" />
      ${tickLabels}
      <text x="${margin.left + plotW / 2}" y="${height - 12}" text-anchor="middle" class="axis-label">Wavelength</text>
      <text x="18" y="${margin.top + plotH / 2}" transform="rotate(-90 18 ${margin.top + plotH / 2})" class="axis-label">Flux</text>
    </svg>
    <div class="hint">${esc(data.hint || "")}</div>
  `

  const svg = root.querySelector("#continuum-svg")
  svg.onclick = (event) => {
    const rect = svg.getBoundingClientRect()
    const viewX = (event.clientX - rect.left) * (width / rect.width)
    const viewY = (event.clientY - rect.top) * (height / rect.height)
    if (viewX < margin.left || viewX > margin.left + plotW || viewY < margin.top || viewY > margin.top + plotH) return
    if (togglePoints && points.length > 0) {
      let nearestIndex = -1
      let nearestDistance = Infinity
      for (let i = 0; i < points.length; i++) {
        const px = sx(points[i][0])
        const py = sy(points[i][1])
        if (!Number.isFinite(px) || !Number.isFinite(py)) continue
        const distance = Math.hypot(px - viewX, py - viewY)
        if (distance < nearestDistance) {
          nearestDistance = distance
          nearestIndex = i
        }
      }
      if (nearestIndex >= 0 && nearestDistance <= 14) {
        const payload = { action: "delete", index: nearestIndex, nonce: Date.now() }
        setStateValue("last_clicked", payload)
        setTriggerValue("clicked", payload)
        return
      }
    }
    const wavelength = xmin + ((viewX - margin.left) / plotW) * (xmax - xmin)
    const sorted = x.map((value, index) => ({ index, distance: Math.abs(value - wavelength) }))
      .sort((a, b) => a.distance - b.distance)
      .slice(0, windowSize)
      .map((item) => item.index)
      .sort((a, b) => a - b)
    const xs = sorted.map((index) => x[index]).sort((a, b) => a - b)
    const ys = sorted.map((index) => y[index]).sort((a, b) => a - b)
    function median(values) {
      const mid = Math.floor(values.length / 2)
      if (values.length % 2 === 1) return values[mid]
      return (values[mid - 1] + values[mid]) / 2
    }
    const payload = { action: "add", wavelength: median(xs), flux: median(ys), nonce: Date.now() }
    setStateValue("last_clicked", payload)
    setTriggerValue("clicked", payload)
  }
}
"""


_CONTINUUM_SELECTOR = st.components.v2.component(
    "continuum_click_selector",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


def _decimate(wavelength: np.ndarray, flux: np.ndarray, max_points: int = 2500) -> tuple[np.ndarray, np.ndarray]:
    if wavelength.size <= max_points:
        return wavelength, flux
    step = int(np.ceil(wavelength.size / max_points))
    return wavelength[::step], flux[::step]


def continuum_click_selector(
    wavelength: np.ndarray,
    flux: np.ndarray,
    points: list[tuple[float, float]],
    *,
    key: str,
    window_size: int = 15,
    toggle_points: bool = False,
    hint: str | None = None,
):
    x = np.asarray(wavelength, dtype=float).ravel()
    y = np.asarray(flux, dtype=float).ravel()
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    if x.size == 0:
        raise ValueError("The selector received no finite spectral points.")

    y_for_scale = y
    if points:
        y_for_scale = np.concatenate([y_for_scale, np.asarray([point[1] for point in points], dtype=float)])
        y_for_scale = y_for_scale[np.isfinite(y_for_scale)]
    ymin = float(np.nanmin(y_for_scale))
    ymax = float(np.nanmax(y_for_scale))
    padding = 0.08 * max(ymax - ymin, 1e-6)
    x, y = _decimate(x, y)
    return _CONTINUUM_SELECTOR(
        key=key,
        data={
            "wavelength": x.tolist(),
            "flux": y.tolist(),
            "points": [(float(px), float(py)) for px, py in points],
            "window_size": int(window_size),
            "toggle_points": bool(toggle_points),
            "xmin": float(np.nanmin(x)),
            "xmax": float(np.nanmax(x)),
            "ymin": ymin - padding,
            "ymax": ymax + padding,
            "hint": hint
            or f"Click on the continuum to add a point: the median wavelength and flux of the {int(window_size)} nearest points are stored.",
        },
        on_clicked_change=lambda: None,
        on_last_clicked_change=lambda: None,
    )

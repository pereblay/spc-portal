This portal is designed for classroom spectral classification of stars. The workflow is: load a spectrum, inspect it, crop the useful wavelength range, normalize the continuum, display reference spectral lines, measure diagnostic features, write the classification rationale, and export a report.

## Panel 1: Spectrum Upload

### Upload FITS or TXT
Loads a spectrum from disk.

Supported formats:
- FITS: expects a 1D spectrum and tries to reconstruct the wavelength axis from FITS WCS/header keywords such as `CRVAL1`, `CDELT1`, `CD1_1`, and `CRPIX1`.
- TXT, DAT, CSV, TSV: expects at least two columns. The first column is wavelength and the second column is flux.

### Use Example Spectrum
Loads a synthetic teaching spectrum. This is useful for testing the interface before using real data.

## Panel 2: Crop And Normalization

### Wavelength Range
Selects the wavelength interval used for normalization, line display, equivalent-width measurements, line ratios, and the normalized plot.

The selected region is shown as a shaded band on the original spectrum.

### Method
Selects the continuum fitting method:

- `Polynomial`: fits a standard polynomial.
- `Legendre`: fits a Legendre polynomial.
- `Cubic spline`: fits a smoothing cubic spline to the cropped spectrum.
- `Manual points`: lets the user select continuum points by clicking on the spectrum. The continuum is then fitted with a configurable spline through those points.

### Degree
Controls polynomial degree for `Polynomial` and `Legendre`.

For `Manual points`, it controls the spline degree. The allowed range is 1 to 5. The number of distinct continuum points must be at least `degree + 1`.

### Spline Smoothing
Controls smoothing for `Cubic spline` and `Manual points`.

For manual points:
- `0` forces the spline to pass exactly through selected continuum points.
- Larger values produce a smoother continuum.

### Nearby Points Per Click
Only available for `Manual points`.

When clicking on the continuum selector, the software does not use a single nearest data point. It stores the median wavelength and median flux of the selected number of nearby spectral points. This reduces sensitivity to noise and narrow spectral features.

### Clear Manual Points
Removes all selected continuum points and reactivates manual selection.

### Reactivate Manual Selection
After computing the continuum in manual mode, click selection is disabled. This button enables point selection again.

### Compute Normalization
Fits the continuum and computes the normalized spectrum. The normalized plot updates only when this button is pressed.

## Panel 3: Spectral Lines

### Visible Families
Controls which reference spectral-line families are displayed on the normalized spectrum.

Available families include H, He I, He II, CNO, Mg/Si/S, Fe, Ca, Na, and TiO.

### Line Labels
Shows or hides text labels next to the reference line positions.

### DIB/IS Detector
Runs a simple local detector for possible diffuse interstellar bands (DIBs) and classical interstellar lines.

The detector uses a curated starter list of strong optical DIBs and common IS features such as Ca II, Na I, K I, CH, and CH+. It only evaluates features whose reference wavelength falls inside the cropped wavelength range.

The detector requires a normalized spectrum. Around each candidate wavelength it searches for a local absorption feature, estimates the local noise from nearby side bands, and flags the candidate only if the absorption depth passes the selected signal-to-noise threshold.

Detected regions are shaded in green on the normalized plot and listed in a table below the plot.

This tool is intended as a visual and educational aid. DIB/IS detections can be confused with stellar lines, telluric residuals, poor continuum placement, or low signal-to-noise spectra. Students should inspect the feature before using it as evidence.

### DIB/IS Sensitivity
Minimum local signal-to-noise required to flag a possible interstellar feature. Lower values are more permissive and may show more false positives; higher values are more conservative.

### Line-Centering Window
Used for line-ratio measurements. After the user clicks near a line, the software searches within this half-window and locates the real line center as the local minimum of the normalized flux.

## Panel 4: Generate Report

### Student Name
Student name printed in the exported report.

### Course
Course or group name printed in the exported report.

### Previous PDF Report
Optional PDF upload. If a previous report is provided, the current report is appended as additional pages at the end of that PDF.

This is useful for cumulative submissions where each new spectrum or classification exercise should be added to the same document.

### Generate PDF Report
Exports a standardized PDF report including:
- student name,
- course,
- original spectrum plot,
- normalized spectrum plot,
- spectral evidence,
- equivalent-width table,
- line-ratio table,
- spectral type and luminosity class,
- student justifications,
- comments.

### Download Markdown
Exports the same report content as Markdown.

## Original Spectrum Plot

The original spectrum plot shows the full loaded spectrum. The current crop range is highlighted. In manual continuum mode, a custom click selector appears here and allows continuum points to be selected directly.

## Continuum Points

Visible in `Manual points` mode.

Each selected point stores both wavelength and flux. Points can be added by clicking the spectrum or by entering a wavelength in the fallback input. The fallback computes flux by interpolation from the cropped spectrum.

Individual points can be removed with the `Delete` button.

## Cropped And Normalized Spectrum Plot

This plot shows the final normalized spectrum after `Compute normalization` has been pressed. Reference line overlays are shown here, not on the original spectrum.

## Evidence Tab

### Equivalent Width
Click `Measure equivalent width`, then click the start and end of the integration interval on the normalized spectrum. The software computes EW and stores it in a table. The associated line is identified using the closest known reference line to the midpoint of the interval.

### Line Ratio
Click `Measure line ratio`, then click two spectral lines on the normalized spectrum. The order matters: the ratio is always first selected line divided by second selected line.

For each clicked line, the software locates the real center using the line-centering window and measures line intensity as `1 - normalized_flux_at_center`.

### Commented Spectral Evidence
Free text for describing relevant spectral evidence: present lines, absent lines, uncertain features, diagnostic ratios, continuum quality, and caveats.

### Comments
Additional comments about the evidence and measurements.

## Classification Tab

### Assigned Spectral Type
Student-assigned spectral type, for example `A0`, `B2`, `G5`, or `M3`.

### Luminosity Class
Student-assigned luminosity class, for example `V`, `IV`, `III`, or `I`.

### Confidence
Qualitative confidence level: low, medium, or high.

### Spectral-Type Justification
Explanation of why the chosen spectral type is supported by the observed evidence.

### Luminosity-Class Justification
Explanation of why the chosen luminosity class is supported by the observed evidence.

### General Comments
Additional classification notes.

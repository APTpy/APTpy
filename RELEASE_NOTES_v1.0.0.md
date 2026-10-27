# APTpy v1.0.0 — Integrated toolbox

APTpy brings candidate-ion exploration, range-file creation, and isotope-overlap
analysis together in a graphical desktop toolbox for atom-probe tomography.

## Included tools

- Candidate List Maker / Spectrum Analyser.
- Range File Maker with project persistence and range-file exports.
- Isotope Deconvolution with isotope-constrained fitting and analysis-table exports.

Developed by Roohallah Surki Aliabad as an independent companion project built
on APAV. The initial candidate workflow focuses on Fe–C–Mn–Al–Si-based alloys
and related advanced high-strength steels.

## Downloads and requirements

`APTpy-v1.0.0-macOS-arm64.zip` contains the macOS app for Apple Silicon.
The supplied executable declares macOS 12 or later and requires external Python
environments at the paths documented in `docs/INSTALLATION.md`.
It is not a self-contained installer.

The available Python/notebook/web resources are included in the repository.
The native launcher source/build project is not included in this preparation.
Clean-machine compatibility and a reproducible native build remain to be verified.

## Interpretation

Candidate assignments and fitted overlap contributions require scientific review.
Read the README and user guide for model assumptions, unresolved ranges, and
counting limitations. Please cite APAV separately when used in your analysis.

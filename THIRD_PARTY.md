# Attribution and third-party resources

APTpy is developed by Roohallah Surki Aliabad. The integrated toolbox builds on
the author's earlier Spectrum Analyser work and uses third-party software.

## APAV

- Repository: <https://gitlab.com/jesseds/apav>
- Documentation: <https://apav.readthedocs.io/>
- Publication: <https://doi.org/10.21105/joss.04862>

Retain APAV's attribution and license notices when redistributing its code.
APAV is an independent project; its authors do not necessarily endorse APTpy.

## Python ecosystem

The supplied sources use NumPy, pandas, SciPy, periodictable, Plotly,
IPython, ipywidgets, Voilà, and the Python standard library, as well as APAV.
These packages retain their own licenses. `requirements.txt` lists direct
dependencies inferred from imports; installed dependency code is not vendored
in this source folder.

## Bundled UI resources

The candidate interface includes a customized Voilà/Jupyter template directory.
Preserve any upstream notices in those files. This folder preserves the resources
found in the supplied app; no complete provenance or license audit of those
resources has been performed.

## Scientific data and references

The candidate notebook records links to NIST isotope/physical-constant resources
and literature references. Preserve those references. Cite the original scientific
sources used to justify ion assignments in your analysis.

## Native executable

The macOS launcher executable is supplied inside the app distribution. Its Swift
or other native source and build project were not present in the supplied bundle.
Include that source and build instructions before describing the whole native app
as reproducibly buildable or distributing a complete corresponding-source release.

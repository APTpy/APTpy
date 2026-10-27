# Installation and portability

## Supplied app

The app was copied intact from the developer's `APTpy V1.0.0.app`.
Its metadata declares version 1.0.0 and macOS 12 as the minimum OS.
The native executable is Apple Silicon (`arm64`).

The app does not bundle Python. `source/runtime.py` records these interpreter
paths used by the supplied launcher:

| Module | Interpreter |
| --- | --- |
| Candidate / Spectrum Analyser | `/opt/anaconda3/bin/python3` |
| Range File Maker | `/opt/anaconda3/bin/python3` |
| Isotope Deconvolution | `/opt/anaconda3/envs/xrd_env/bin/python` |

These paths must exist with the appropriate packages for the supplied app to
work as configured. Installing requirements into an arbitrary virtual environment
does not change the native application's interpreter selection. Portable runtime
selection needs a later application update.

Logs are written to `~/Library/Logs/APTpy/` as `candidate.log`, `ranges.log`, and
`isotope.log`. The Python services bind to `127.0.0.1` on dynamically selected ports.

## Run available sources on macOS

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Then start the desired module:

```bash
JUPYTER_PATH="$PWD/source/candidate/jupyter" python -m voila "source/candidate/1- APTpy-Spectrum Analyser-V1.0.2.ipynb"
```

```bash
python source/ranges/server.py
```

```bash
python source/isotope/server.py
```

The web servers open local browser interfaces. File/folder chooser code uses
macOS facilities; cross-platform behavior has not been verified. Install package
versions in a dedicated environment and record versions used for research.

## Verification scope

Repository preparation checks resource consistency, Python syntax, notebook JSON,
metadata, and archive integrity. It does not establish clean-machine installation,
end-to-end GUI behavior, numerical validation, commercial software compatibility,
or a reproducible native build.

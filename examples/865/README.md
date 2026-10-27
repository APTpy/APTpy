# Example project 865

Two user-supplied experimental project snapshots demonstrate successive workflow
stages:

| File | Contents |
| --- | --- |
| `865.apt-project_candidate list.json` | Candidate-stage project with 26 selected ions and a cached mass spectrum. |
| `865.apt-project_range file.json` | Ranged project with 26 selected ions, a cached mass spectrum, and 51 integration ranges. |

## Using the examples

1. Copy the desired example to a working folder before editing: the range editor
   saves changes and creates backups next to the loaded project.
2. Open the candidate-stage project with the candidate interface to explore saved
   selections and spectrum information. Operations that read or recompute from
   raw EPOS require you to select the corresponding original EPOS file.
3. Open the ranged project in Range File Maker to inspect range boundaries and
   checked assignments.
4. Use the ranged project in Isotope Deconvolution to explore the saved assignments
   and cached spectrum, subject to the method's assumptions.

No raw EPOS file or previously exported TXT, CSV, HTML, or RRNG files are supplied.
The `epos_file` and `save_folder` fields are empty. Cached spectra are included;
these files therefore contain experimental spectrum data, not just GUI settings.
Cached-bin integration is approximate and may differ from exact event-level counts.

The saved range-export metadata records 30 resolved ranges and 21 unresolved ranges
at the time of that export. This is historical metadata, not a fresh validation or
a guarantee that every assignment is scientifically correct.

## Preparation and attribution

The repository copies preserve the candidate selections, spectrum arrays, ranges,
and analysis metadata. Developer-specific absolute output paths were replaced with
their filenames so the public copies do not point into a private Desktop folder.
Choose your own export folder in the interface. The original files were not changed.

Examples were supplied by Roohallah Surki Aliabad for use with APTpy. Do not treat
them as a certified reference dataset or use their assignments as universal ion
identifications. Review assignments against the experimental conditions and
appropriate scientific sources.

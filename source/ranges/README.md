# APTpy — Range File maker 1.3.0

Load project opens a file chooser. The full project path is displayed. Choose output folder opens a folder chooser; exports default to the project folder. Hold Shift and drag to pan temporarily while editing ranges.

Every candidate and checked/unchecked state is saved in the project JSON. Ranges save automatically. Export writes only selected assignments. No separate assignments JSON is created.

## APAV-compatible range exports

Resolved ranges export elemental stoichiometry: Fe:1 for Fe²⁺ or Fe⁺, and Fe:1 C:2 for FeC₂. Charge and isotope identities remain in the project JSON.

A range whose selected candidates have different chemical compositions is unresolved. RRNG preserves its boundaries as a Name:Shared_... entry. A range with no checked ions is a Name:Unassigned_... entry. The installed APAV reader skips these entries when loading and quantifying, so they do not contribute to elemental counts or the percentage denominator. Their peaks remain part of the complete input spectrum. Export completion reports how many ranges were left unresolved. A shared entry is not deconvolved and must not be interpreted as a molecule composed of all alternatives.

RNG exports require every range to have a single resolved chemical composition. Use RRNG to preserve unresolved named ranges. APAV's tested RangeCollection.from_rrng reader handles RRNG; its RNG reader may be unimplemented.

All file exports get a new filename. Export metadata is stored under range_editor.last_export in the main project JSON. No existing range export is overwritten.

## Project backups

The initial .before-ranging.bak is a pre-edit snapshot. The .ranges-backup.json is an independent latest-range backup. If another app removes the range_editor section, reopening restores this backup only when spectrum mass/count arrays match. Keep the backup next to the project. Candidate and checkbox states are retained.

## Validation

The corrected 51-range user file loaded successfully in the user's xrd_env Python 3.10 APAV installation: 30 resolved ranges loaded and 21 shared entries were skipped. A synthetic test dataset passed elemental quantification. Unit checks cover atomic/molecular stoichiometry, shared and unassigned entries, boundary validation, selected-only assignments, JSON round trips, metadata, independent backup restoration, and Shift panning. Import into a particular IVAS/AP Suite version has not been tested.

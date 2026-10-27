# APTpy workflow guide

## 1. Candidate exploration

Open the candidate interface and load your EPOS data. Review atomic and molecular
ion candidates, isotope fingerprints, and spectrum overlays. Save a project JSON
for the subsequent tools and export candidate information as needed. The initial
scientific scope is Fe–C–Mn–Al–Si-based alloys and related steels.

## 2. Ranging

Open the saved project in Range File Maker, define integration boundaries, and
review the checked candidate assignments in each range. Keep the project and its
range backups together. Review every export for resolved and unresolved entries.

RRNG exports use elemental stoichiometry for resolved ions. A shared range is
preserved as a named unresolved entry; it does not represent a molecule composed
of all its alternative assignments. RNG export requires a single resolved chemical
composition in every exported range. See `source/ranges/README.md` for details
recorded with the supplied module.

## 3. Isotope-overlap analysis

Load the ranged project in Isotope Deconvolution. Inspect selected candidates,
isotope constraints, excluded-candidate conflicts, and fit diagnostics before
using fitted contributions or composition tables.

The custom model assumes fixed isotope fingerprints, specified candidate species,
equal isotope-window capture efficiency, and any supplied fixed background.
Inspect whether those assumptions are appropriate for the dataset. Non-identifiable
mixtures cannot support unique species estimates.

Prefer exact EPOS or event-mass counts when available. Cached-bin results are
approximate because integration boundaries can cross histogram bins. Save the
project and exported tables alongside a record of version and analysis settings.

## Research reporting

Cite the software release actually used, APAV, and the scientific sources relevant
to your selected ions. Report range boundaries, candidate selection, treatment
of unresolved overlaps, count source, and model assumptions when they affect
your conclusions.

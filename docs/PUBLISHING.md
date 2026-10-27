# Publishing the main APTpy repository

This is a local preparation folder. No GitHub repository, release, or Zenodo record
was created as part of preparing it.

## Repository identity

Suggested organization: **APTpy**

Suggested repository name: **APTpy**

Suggested description:

> A graphical Python toolbox for atom-probe tomography data analysis, integrating
> candidate-ion exploration, range-file creation, and isotope-overlap analysis.
> An independent companion project built on APAV.

Suggested topics: `atom-probe-tomography`, `materials-science`, `mass-spectrometry`,
`python`, `gui`, `isotope-analysis`.

## Before a public release

- Locate and add the native launcher source and build instructions. The supplied
  app contains the executable but not its native source project.
- Address or prominently retain the machine-specific Python requirements.
- Confirm the new repository URL and add it as `repository-code` in CITATION.cff.
- Add the actual public release date to CITATION.cff when the release is made.
- Check third-party notices and keep GPL attribution intact.
- Test installation and all three modules on a second Mac, recording the dependency
  versions and results. This preparation does not claim that test has passed.

## Upload the source repository

Create an empty repository under your APTpy organization. If you choose the name
APTpy, its expected URL is `https://github.com/APTpy/APTpy`.
Then run:

```bash
cd "/Users/rsurkial23/Desktop/APTpy-repository"
git init -b main
git add .
git status
git commit -m "Prepare APTpy integrated toolbox v1.0.0"
git remote add origin https://github.com/APTpy/APTpy.git
git push -u origin main
```

Inspect `git status` before committing. The distribution directory is intentionally
ignored except for its README, so app binaries are not added to source history.

## Publish the app download

Create a GitHub release tagged `v1.0.0` for the main toolbox when ready.
Use `RELEASE_NOTES_v1.0.0.md` for the release description. Attach:

- `distribution/APTpy-v1.0.0-macOS-arm64.zip`
- `distribution/SHA256SUMS.txt`

The ZIP preserves the app bundle for downloading; the repository's source archive
is a separate download. Do not treat GitHub's automatically generated source ZIP
as the macOS app installer.

## Zenodo

Connect this new repository separately to Zenodo before publishing a release you
want archived. The prior DOI `10.5281/zenodo.23296361` identifies Spectrum Analyser
v1.0.1 and must not be presented as the integrated toolbox DOI.
Once the new toolbox has its own DOI, add it to the README and CITATION.cff.
There is no need to create a new release for every minor README edit.

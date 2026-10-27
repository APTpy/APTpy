APTpy — Candidate List Maker

Load project opens a native file chooser. The full project path appears after loading.
Choose save folder opens a native folder chooser. The full folder path appears below it.

Loaded projects save automatically after element/ion checkbox changes and manual peak text edits (after a brief typing pause). Unknown peak additions/deletions save immediately. Plot/display setting changes also save.

The project JSON preserves additional data such as Range File maker ranges, checkbox states, and export metadata. Saved candidate selections, unknown peaks, and manual text return when reloading.

A new project can still be created from an EPOS file by plotting; its project JSON is saved beside the EPOS file. Existing projects must be loaded before automatic overwriting is enabled.

The separate candidate-list/spectrum/plot exports retain their existing export behavior; automatic project saving does not regenerate large HTML/CSV exports on every keystroke.

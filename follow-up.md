# Follow-up (next session)

## Open points
- Encoding cleanup: multiple files contain mojibake (e.g. "ü"); decide whether to normalize to UTF-8 content across `project-tasks.md`, `pyproject.toml` comments, and any UI strings.
- Notification behavior: current reminder triggers only on app start and only if last training > 24h. If you want true 24h background reminders, we need an Android scheduled job/service.
- iOS target: Android-first is done; iOS build specifics (permissions, notification strategy, packaging) are still open.
- Backup/import UX: current import expects a manual file path. For Android SAF file picker integration, we need additional pyjnius wiring.
- Training evaluation: current near-correct logic is a simple Levenshtein threshold; confirm if this is good enough or should handle accents separately.
- Calendar view: currently a simple rolling list (30 days). Confirm if you want a real grid calendar UI.
- Assets: icon/presplash are still from the base project; decide if/when to replace.
- Documentation: README/usage notes are still missing.

## Open questions
- Should we normalize all app strings to ASCII-only (current approach), or allow UTF-8 and fix encoding everywhere?
- For backups: should we keep only YAML, or also offer a compressed/secured option later?
- For notifications: is "on app start" acceptable, or do you require background reminders?
- For training: should introduced words be tracked separately from review (e.g. a "new" stage), or is the current progress map sufficient?
- Should the seed vocab be editable in-app or kept as a reference sample only?

## Quick sanity checks to run
- `uv sync` (or install deps) and run the app locally.
- Buildozer Android build to confirm `pyyaml` + `plyer` packaging.


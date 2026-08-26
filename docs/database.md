# ResolveX Database

SQLite stores the normalized operational data.

## Core tables

- `users`: reporter, technician, and admin accounts.
- `departments`: operational support teams.
- `categories` and `subcategories`: structured issue classification.
- `locations`: verified campus landmarks and facility types.
- `issues`: report details, location, priority, status, assignment, dates, and optional `specific_area`.
- `issue_history`: append-only workflow and assignment audit events.

Foreign keys are enabled for every connection. Frequent issue fields have indexes. Existing databases receive the nullable `specific_area` column through a backward-compatible startup migration.

Exact SRM room, floor, and laboratory data is not fabricated; it can be added when verified.

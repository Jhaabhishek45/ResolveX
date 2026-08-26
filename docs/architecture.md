# ResolveX Architecture

ResolveX uses a simple layered Flask architecture:

```text
Browser -> Flask routes -> Services -> DatabaseManager -> SQLite
```

## Layers

- `app.py`: HTTP routes, sessions, role checks, and request validation.
- `services.py`: rule-based triage, assignment, analytics, and workflow rules.
- `models.py`: typed domain objects for users, issues, locations, and history.
- `database.py`: SQLite schema, connections, parameterized queries, and migration.
- `templates/`: Jinja HTML views.
- `static/`: responsive CSS and JavaScript.

The design keeps business decisions out of templates and keeps database access centralized.

# ResolveX Workflow

```text
REPORTED -> TRIAGED -> ASSIGNED -> IN_PROGRESS -> RESOLVED -> VERIFIED -> CLOSED
```

A resolved issue may be reopened when the reporter confirms the problem is still present:

```text
RESOLVED -> REOPENED -> IN_PROGRESS
```

## Demo flow

1. Reporter signs in and submits a categorized issue with a verified campus location.
2. `TriageEngine` suggests a department, calculates priority and due time, and detects recurring patterns.
3. An admin assigns a department and technician; the action records the admin actor.
4. The assigned technician starts work and adds a resolution note.
5. The technician marks the issue resolved.
6. The reporter verifies the fix or reopens the issue.
7. Every important transition is preserved in `issue_history` and reflected in dashboard analytics.

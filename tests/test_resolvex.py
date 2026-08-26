from datetime import datetime, timedelta
import re

import pytest

from app import app
from database import DatabaseManager
from services import AnalyticsService, AssignmentManager, TriageEngine


@pytest.fixture
def database(tmp_path):
    db = DatabaseManager(tmp_path / "test.sqlite")
    admin_id = db.execute_insert(
        "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
        ("Admin", "admin@test", "admin"),
    )
    reporter_id = db.execute_insert(
        "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
        ("Reporter", "reporter@test", "reporter"),
    )
    technician_id = db.execute_insert(
        "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
        ("Technician", "technician@test", "technician"),
    )
    second_technician_id = db.execute_insert(
        "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
        ("Second Technician", "second@test", "technician"),
    )
    department_id = db.execute_insert(
        "INSERT INTO departments (name) VALUES (?)", ("IT Support",)
    )
    category_id = db.execute_insert(
        "INSERT INTO categories (name) VALUES (?)", ("IT & Network",)
    )
    subcategory_id = db.execute_insert(
        """
        INSERT INTO subcategories (category_id, name)
        VALUES (?, ?)
        """,
        (category_id, "Wi-Fi"),
    )
    location_id = db.execute_insert(
        "INSERT INTO locations (building) VALUES (?)", ("Main Block",)
    )
    return locals()


def create_issue(database, status="TRIAGED", priority="MEDIUM", **overrides):
    values = {
        "title": "Wi-Fi unavailable",
        "description": "Campus network is unavailable.",
        "category_id": database["category_id"],
        "subcategory_id": database["subcategory_id"],
        "location_id": database["location_id"],
        "priority": priority,
        "status": status,
        "department_id": database["department_id"],
        "reporter_id": database["reporter_id"],
        "due_at": None,
    }
    values.update(overrides)
    return database["db"].execute_insert(
        """
        INSERT INTO issues (
            title, description, category_id, subcategory_id, location_id,
            priority, status, department_id, reporter_id, due_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        tuple(values.values()),
    )


def test_triage_routes_wifi_and_calculates_priority(database):
    result = TriageEngine(database["db"]).triage(
        database["category_id"],
        database["subcategory_id"],
        database["location_id"],
        "HIGH",
    )
    assert result.department_name == "IT Support"
    assert result.priority == "HIGH"
    assert result.due_at > datetime.now()


def test_triage_rejects_invalid_subcategory(database):
    with pytest.raises(ValueError, match="Invalid subcategory"):
        TriageEngine(database["db"]).triage(
            database["category_id"],
            999999,
            database["location_id"],
            "LOW",
        )


def test_assignment_and_reassignment_record_admin_actor(database):
    issue_id = create_issue(database)
    manager = AssignmentManager(database["db"])
    manager.assign(issue_id, database["technician_id"], database["admin_id"])
    manager.assign(issue_id, database["second_technician_id"], database["admin_id"])
    issue = database["db"].fetch_one(
        "SELECT assigned_to, status FROM issues WHERE id = ?", (issue_id,)
    )
    history = database["db"].fetch_all(
        "SELECT user_id, action, note FROM issue_history WHERE issue_id = ? ORDER BY id",
        (issue_id,),
    )
    assert issue["assigned_to"] == database["second_technician_id"]
    assert issue["status"] == "ASSIGNED"
    assert [row["user_id"] for row in history] == [database["admin_id"]] * 2
    assert [row["action"] for row in history] == [
        "TECHNICIAN_ASSIGNED",
        "TECHNICIAN_REASSIGNED",
    ]
    assert "Technician" in history[1]["note"]


def test_assignment_rejects_non_admin_actor(database):
    issue_id = create_issue(database)
    with pytest.raises(ValueError, match="authenticated admin"):
        AssignmentManager(database["db"]).assign(
            issue_id,
            database["technician_id"],
            database["reporter_id"],
        )


def test_analytics_counts_overdue_and_reopened(database):
    create_issue(database, priority="CRITICAL", due_at="2000-01-01 00:00:00")
    create_issue(database, status="REOPENED")
    summary = AnalyticsService(database["db"]).summary()
    assert summary["open"] == 2
    assert summary["critical"] == 1
    assert summary["overdue"] == 1
    assert summary["reopened"] == 1


def test_reporter_cannot_access_admin_workspace():
    client = app.test_client()
    login_page = client.get("/login")
    token = re.search(
        rb'name="csrf_token" value="([^"]+)"', login_page.data
    ).group(1).decode()
    client.post(
        "/login",
        data={
            "email": "abhishek@resolvex.local",
            "csrf_token": token,
        },
    )
    assert client.get("/dashboard").status_code == 403
    report_page = client.get("/report")
    token = re.search(
        rb'name="csrf_token" value="([^"]+)"', report_page.data
    ).group(1).decode()
    assert client.post(
        "/issues/1/assign",
        data={"technician_id": "2", "csrf_token": token},
    ).status_code == 403

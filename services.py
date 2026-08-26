from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from config import (
    PRIORITY_TARGET_HOURS,
    RECURRING_ISSUE_THRESHOLD,
    RECURRING_ISSUE_WINDOW_DAYS,
)


@dataclass(frozen=True)
class TriageResult:
    """
    Result produced by the ResolveX rule-based triage engine.
    """

    department_id: Optional[int]
    department_name: Optional[str]
    priority: str
    due_at: datetime
    recurring: bool
    related_issue_count: int


class TriageEngine:
    """
    Rule-based issue triage engine.

    Responsibilities:
    - Suggest responsible department
    - Determine priority
    - Calculate target resolution time
    - Detect repeated issues at the same location
    """

    CATEGORY_DEPARTMENT_MAP = {
        "IT & Network": "IT Support",
        "Classroom & Academic": "AV & Technical Support",
        "Electrical & Power": "Electrical Maintenance",
        "Water & Sanitation": "Water & Sanitation",
        "Facilities & Maintenance": "Facilities & Maintenance",
        "Library": "Library Support",
        "Sports & Recreation": "Sports Facilities",
        "Safety & Security": "Safety & Security",
    }

    SUBCATEGORY_DEPARTMENT_MAP = {
        "Projector": "AV & Technical Support",
        "Smart Classroom Equipment": "AV & Technical Support",
        "Wi-Fi": "IT Support",
        "Internet": "IT Support",
        "Computer / Desktop": "IT Support",
        "Printer": "IT Support",
        "Network Port": "IT Support",
        "Power Failure": "Electrical Maintenance",
        "Light": "Electrical Maintenance",
        "Switch": "Electrical Maintenance",
        "Electrical Socket": "Electrical Maintenance",
        "Emergency Light": "Electrical Maintenance",
        "Water Leakage": "Water & Sanitation",
        "Drinking Water": "Water & Sanitation",
        "Washroom": "Water & Sanitation",
        "Wash Basin": "Water & Sanitation",
        "Drainage": "Water & Sanitation",
        "Air Conditioning": "Facilities & Maintenance",
        "Furniture": "Facilities & Maintenance",
        "Lift / Elevator": "Facilities & Maintenance",
        "Door / Lock": "Facilities & Maintenance",
        "Window": "Facilities & Maintenance",
    }

    def __init__(self, database):
        self.database = database

    def triage(
        self,
        category_id: int,
        subcategory_id: Optional[int],
        location_id: int,
        impact: str,
    ) -> TriageResult:
        """
        Produce the complete triage result for a new issue.
        """

        category = self.database.fetch_one(
            """
            SELECT id, name
            FROM categories
            WHERE id = ?
            """,
            (category_id,),
        )

        if not category:
            raise ValueError("Invalid category.")

        subcategory_name = None

        if subcategory_id:
            subcategory = self.database.fetch_one(
                """
                SELECT id, name
                FROM subcategories
                WHERE id = ?
                  AND category_id = ?
                """,
                (
                    subcategory_id,
                    category_id,
                ),
            )

            if not subcategory:
                raise ValueError(
                    "Invalid subcategory for the selected category."
                )

            subcategory_name = subcategory["name"]

        department_name = self._suggest_department(
            category_name=category["name"],
            subcategory_name=subcategory_name,
        )

        department_id = self._get_department_id(
            department_name
        )

        related_issue_count = self._count_related_open_issues(
            category_id=category_id,
            location_id=location_id,
        )

        recurring = (
            related_issue_count
            >= RECURRING_ISSUE_THRESHOLD
        )

        priority = self._calculate_priority(
            impact=impact,
            recurring=recurring,
        )

        due_at = datetime.now() + timedelta(
            hours=PRIORITY_TARGET_HOURS[priority]
        )

        return TriageResult(
            department_id=department_id,
            department_name=department_name,
            priority=priority,
            due_at=due_at,
            recurring=recurring,
            related_issue_count=related_issue_count,
        )

    def _suggest_department(
        self,
        category_name: str,
        subcategory_name: Optional[str],
    ) -> Optional[str]:
        """
        Prefer a specific subcategory rule over a category rule.
        """

        if subcategory_name:
            department = self.SUBCATEGORY_DEPARTMENT_MAP.get(
                subcategory_name
            )

            if department:
                return department

        return self.CATEGORY_DEPARTMENT_MAP.get(
            category_name
        )

    def _get_department_id(
        self,
        department_name: Optional[str],
    ) -> Optional[int]:
        """
        Convert department name into its database ID.
        """

        if not department_name:
            return None

        department = self.database.fetch_one(
            """
            SELECT id
            FROM departments
            WHERE name = ?
            """,
            (department_name,),
        )

        return (
            department["id"]
            if department
            else None
        )

    def _count_related_open_issues(
        self,
        category_id: int,
        location_id: int,
    ) -> int:
        """
        Count similar non-closed issues reported recently
        at the same location.
        """

        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS issue_count
            FROM issues
            WHERE category_id = ?
              AND location_id = ?
              AND status NOT IN (
                  'RESOLVED',
                  'VERIFIED',
                  'CLOSED'
              )
              AND created_at >= datetime(
                  'now',
                  ?
              )
            """,
            (
                category_id,
                location_id,
                f"-{RECURRING_ISSUE_WINDOW_DAYS} days",
            ),
        )

        return int(row["issue_count"]) if row else 0

    @staticmethod
    def _calculate_priority(
        impact: str,
        recurring: bool,
    ) -> str:
        """
        Convert reported impact into a ResolveX priority.

        Recurring problems receive an escalation where appropriate.
        """

        normalized = impact.upper()

        priority_order = {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
            "CRITICAL": 3,
        }

        if normalized not in priority_order:
            raise ValueError("Invalid impact level.")

        current_priority = normalized

        if recurring and normalized == "MEDIUM":
            current_priority = "HIGH"

        elif recurring and normalized == "LOW":
            current_priority = "MEDIUM"

        return current_priority


class AnalyticsService:
    """Provide database-backed metrics for the operations dashboard."""

    def __init__(self, database):
        self.database = database

    def _count(self, where="", parameters=()):
        row = self.database.fetch_one(
            f"SELECT COUNT(*) AS count FROM issues {where}",
            parameters,
        )
        return int(row["count"])

    def summary(self):
        active = "WHERE status NOT IN ('RESOLVED', 'VERIFIED', 'CLOSED')"
        period = "datetime('now', '-30 days')"
        return {
            "open": self._count(active),
            "high_priority": self._count(
                f"{active} AND priority IN ('HIGH', 'CRITICAL')"
            ),
            "critical": self._count(
                f"{active} AND priority = 'CRITICAL'"
            ),
            "overdue": self._count(
                f"{active} AND due_at IS NOT NULL "
                "AND datetime(due_at) < datetime('now')"
            ),
            "in_progress": self._count(
                "WHERE status = 'IN_PROGRESS'"
            ),
            "resolved": self._count(
                "WHERE status IN ('RESOLVED', 'VERIFIED', 'CLOSED')"
            ),
            "resolved_period": self._count(
                "WHERE resolved_at IS NOT NULL AND datetime(resolved_at) >= "
                f"{period}"
            ),
            "closed_period": self._count(
                "WHERE closed_at IS NOT NULL AND datetime(closed_at) >= "
                f"{period}"
            ),
            "reopened": self._count("WHERE status = 'REOPENED'"),
            "unassigned": self._count(
                f"{active} AND assigned_to IS NULL"
            ),
            "high_unassigned": self._count(
                f"{active} AND assigned_to IS NULL "
                "AND priority IN ('HIGH', 'CRITICAL')"
            ),
            "awaiting_verification": self._count(
                "WHERE status = 'RESOLVED'"
            ),
        }

    def resolution_metrics(self):
        row = self.database.fetch_one(
            """
            SELECT
                AVG((julianday(resolved_at) - julianday(created_at)) * 24) AS mttr_hours,
                COUNT(CASE WHEN status IN ('RESOLVED', 'VERIFIED', 'CLOSED') THEN 1 END) AS resolved_count,
                COUNT(*) AS total_count,
                COUNT(CASE WHEN due_at IS NOT NULL AND datetime(due_at) < datetime('now')
                           AND status NOT IN ('RESOLVED', 'VERIFIED', 'CLOSED') THEN 1 END) AS overdue_count
            FROM issues
            """
        )
        total = int(row["total_count"] or 0)
        return {
            "mttr_hours": round(float(row["mttr_hours"] or 0), 1),
            "resolution_rate": round((row["resolved_count"] or 0) / total * 100, 1) if total else 0,
            "overdue_rate": round((row["overdue_count"] or 0) / total * 100, 1) if total else 0,
        }

    def category_breakdown(self):
        return self.database.fetch_all(
            """
            SELECT categories.name, COUNT(issues.id) AS issue_count
            FROM issues
            JOIN categories ON categories.id = issues.category_id
            GROUP BY categories.id, categories.name
            ORDER BY issue_count DESC, categories.name
            """
        )

    def building_breakdown(self):
        return self.database.fetch_all(
            """
            SELECT locations.building AS name, COUNT(issues.id) AS issue_count
            FROM issues
            JOIN locations ON locations.id = issues.location_id
            GROUP BY locations.building
            ORDER BY issue_count DESC, name
            """
        )

    def new_vs_resolved(self):
        return self.database.fetch_all(
            """
            SELECT report_day AS day,
                   SUM(new_count) AS new_count,
                   SUM(resolved_count) AS resolved_count
            FROM (
                SELECT date(created_at) AS report_day, 1 AS new_count, 0 AS resolved_count
                FROM issues WHERE datetime(created_at) >= datetime('now', '-14 days')
                UNION ALL
                SELECT date(resolved_at) AS report_day, 0 AS new_count, 1 AS resolved_count
                FROM issues WHERE resolved_at IS NOT NULL
                  AND datetime(resolved_at) >= datetime('now', '-14 days')
            )
            GROUP BY report_day
            ORDER BY report_day
            """
        )

    def recurring_issues(self):
        return self.database.fetch_all(
            """
            SELECT locations.building AS name,
                   categories.name AS category_name,
                   COUNT(issues.id) AS issue_count
            FROM issues
            JOIN locations ON locations.id = issues.location_id
            JOIN categories ON categories.id = issues.category_id
            WHERE datetime(issues.created_at) >= datetime('now', '-14 days')
            GROUP BY locations.id, locations.building, categories.id, categories.name
            HAVING COUNT(issues.id) >= 3
            ORDER BY issue_count DESC, name
            """
        )

    def department_workload(self):
        return self.database.fetch_all(
            """
            SELECT departments.name, COUNT(issues.id) AS issue_count
            FROM issues
            JOIN departments ON departments.id = issues.department_id
            WHERE issues.status NOT IN ('RESOLVED', 'VERIFIED', 'CLOSED')
            GROUP BY departments.id, departments.name
            ORDER BY issue_count DESC, departments.name
            """
        )

    def attention_items(self):
        summary = self.summary()
        items = []
        if summary["high_unassigned"]:
            items.append({"text": f"{summary['high_unassigned']} high-priority issue(s) need assignment", "query": "high_priority=1"})
        elif summary["unassigned"]:
            items.append({"text": f"{summary['unassigned']} open issue(s) need assignment", "query": ""})
        if summary["overdue"]:
            items.append({"text": f"{summary['overdue']} open issue(s) are overdue", "query": "overdue=1"})
        if summary["reopened"]:
            items.append({"text": f"{summary['reopened']} issue(s) were reopened", "query": "status=REOPENED"})
        if summary["awaiting_verification"]:
            items.append({"text": f"{summary['awaiting_verification']} issue(s) await verification", "query": "status=RESOLVED"})
        return items


class AssignmentManager:
    """Assign active issues to verified technician accounts."""

    def __init__(self, database):
        self.database = database

    def assign(
        self,
        issue_id: int,
        technician_id: int,
        actor_id: int,
        department_id: Optional[int] = None,
    ):
        issue = self.database.fetch_one(
            """
            SELECT issues.id, issues.status, issues.assigned_to,
                   previous.name AS previous_technician_name
            FROM issues
            LEFT JOIN users AS previous
                ON previous.id = issues.assigned_to
            WHERE issues.id = ?
            """,
            (issue_id,),
        )
        actor = self.database.fetch_one(
            "SELECT id FROM users WHERE id = ? AND role = 'admin'",
            (actor_id,),
        )
        technician = self.database.fetch_one(
            "SELECT id, name FROM users WHERE id = ? AND role = 'technician'",
            (technician_id,),
        )
        department = None
        if department_id is not None:
            department = self.database.fetch_one(
                "SELECT id, name FROM departments WHERE id = ?",
                (department_id,),
            )
        if not issue:
            raise ValueError("Issue not found.")
        if not actor:
            raise ValueError("Only an authenticated admin can assign issues.")
        if not technician:
            raise ValueError("Select a valid technician.")
        if department_id is not None and not department:
            raise ValueError("Select a valid department.")
        if issue["status"] in {"RESOLVED", "VERIFIED", "CLOSED"}:
            raise ValueError("Closed work cannot be assigned.")

        is_reassignment = (
            issue["assigned_to"] is not None
            and issue["assigned_to"] != technician_id
        )
        action = (
            "TECHNICIAN_REASSIGNED"
            if is_reassignment
            else "TECHNICIAN_ASSIGNED"
        )
        note = (
            f"Reassigned from {issue['previous_technician_name']} "
            f"to {technician['name']}."
            if is_reassignment
            else f"Assigned to {technician['name']}."
        )

        self.database.execute(
            """
            UPDATE issues
            SET assigned_to = ?,
                department_id = COALESCE(?, department_id),
                status = 'ASSIGNED',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (technician_id, department_id, issue_id),
        )
        self.database.execute(
            """
            INSERT INTO issue_history (issue_id, user_id, action, note)
            VALUES (?, ?, ?, ?)
            """,
            (
                issue_id,
                actor_id,
                action,
                note,
            )
        )
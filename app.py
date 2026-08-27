from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from datetime import datetime
from functools import wraps
import secrets

from config import APP_NAME, SECRET_KEY
from database import DatabaseManager
from services import AssignmentManager, AnalyticsService, TriageEngine


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["APP_NAME"] = APP_NAME

    # ---------------------------------------------------------
    # CORE SERVICES
    # ---------------------------------------------------------

    database = DatabaseManager()
    triage_engine = TriageEngine(database)
    analytics = AnalyticsService(database)
    assignment_manager = AssignmentManager(database)

    @app.before_request
    def validate_csrf_token():
        if request.method != "POST":
            return None
        submitted_token = request.form.get("csrf_token", "")
        session_token = session.get("csrf_token", "")
        if not session_token or not submitted_token or not secrets.compare_digest(
            submitted_token,
            session_token,
        ):
            return (
                render_template(
                    "error.html",
                    message="This form has expired. Please try again.",
                ),
                400,
            )
        return None

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Sign in to continue.", "error")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def role_required(*roles):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                if "user_id" not in session:
                    flash("Sign in to continue.", "error")
                    return redirect(url_for("login", next=request.path))
                if session.get("role") not in roles:
                    return render_template("error.html", message="You do not have permission to access this workspace."), 403
                return view(*args, **kwargs)
            return wrapped
        return decorator

    @app.context_processor
    def inject_current_user():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {
            "current_user": session,
            "csrf_token": session["csrf_token"],
        }

    @app.get("/login")
    def login():
        return render_template("login.html")

    @app.post("/login")
    def sign_in():
        email = request.form.get("email", "").strip().lower()
        user = database.fetch_one(
            "SELECT id, name, email, role FROM users WHERE lower(email) = ?",
            (email,),
        )
        if not user:
            flash("Use one of the seeded ResolveX demo accounts.", "error")
            return redirect(url_for("login"))
        session.clear()
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]
        destination = request.args.get("next") or request.form.get("next")
        if destination and destination.startswith("/"):
            return redirect(destination)
        return redirect(url_for("home"))

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("home"))

    # ---------------------------------------------------------
    # HOME
    # ---------------------------------------------------------

    @app.get("/")
    def home():
        return render_template("home.html")

    # ---------------------------------------------------------
    # REPORT ISSUE — FORM
    # ---------------------------------------------------------

    @app.get("/report")
    @role_required("reporter")
    def report_issue():

        categories = database.fetch_all(
            """
            SELECT
                id,
                name,
                description
            FROM categories
            ORDER BY name
            """
        )

        subcategories = database.fetch_all(
            """
            SELECT
                id,
                category_id,
                name
            FROM subcategories
            ORDER BY category_id, name
            """
        )

        locations = database.fetch_all(
            """
            SELECT
                id,
                building,
                floor,
                room,
                facility_type
            FROM locations
            ORDER BY building, floor, room
            """
        )

        return render_template(
            "report.html",
            categories=categories,
            subcategories=subcategories,
            locations=locations,
        )

    # ---------------------------------------------------------
    # REPORT ISSUE — SUBMIT
    # ---------------------------------------------------------

    @app.post("/report")
    @role_required("reporter")
    def create_issue():

        title = request.form.get(
            "title",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        category_id_raw = request.form.get(
            "category_id"
        )

        subcategory_id_raw = request.form.get(
            "subcategory_id"
        )

        location_id_raw = request.form.get(
            "location_id"
        )

        specific_area = request.form.get(
            "specific_area",
            "",
        ).strip()

        impact = request.form.get(
            "impact",
            "",
        ).upper()

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if not title:
            flash(
                "Please enter a short title.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        if len(title) > 120:
            flash(
                "The issue title must be 120 characters or less.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        if not description:
            flash(
                "Please describe the issue.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        if len(description) > 1000:
            flash(
                "The issue description must be 1000 characters or less.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        if len(specific_area) > 100:
            flash(
                "The specific area must be 100 characters or less.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        if not category_id_raw:
            flash(
                "Please select an issue category.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        if not location_id_raw:
            flash(
                "Please select a campus location.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        valid_impacts = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }

        if impact not in valid_impacts:
            flash(
                "Please select the issue impact.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        # -----------------------------------------------------
        # SAFE ID CONVERSION
        # -----------------------------------------------------

        try:
            category_id = int(category_id_raw)
            location_id = int(location_id_raw)

            subcategory_id = (
                int(subcategory_id_raw)
                if subcategory_id_raw
                else None
            )

        except (TypeError, ValueError):
            flash(
                "One or more selected values are invalid.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        # -----------------------------------------------------
        # TEMPORARY REPORTER
        # Authentication comes later.
        # -----------------------------------------------------

        reporter = database.fetch_one(
            """
            SELECT
                id,
                name,
                email
            FROM users
            WHERE id = ? AND role = 'reporter'
            """
            , (session["user_id"],)
        )

        if not reporter:
            flash(
                "No reporter account is configured.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        # -----------------------------------------------------
        # VALIDATE CATEGORY
        # -----------------------------------------------------

        category = database.fetch_one(
            """
            SELECT
                id,
                name
            FROM categories
            WHERE id = ?
            """,
            (category_id,),
        )

        if not category:
            flash(
                "The selected category does not exist.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        # -----------------------------------------------------
        # VALIDATE LOCATION
        # -----------------------------------------------------

        location = database.fetch_one(
            """
            SELECT
                id,
                building,
                floor,
                room
            FROM locations
            WHERE id = ?
            """,
            (location_id,),
        )

        if not location:
            flash(
                "The selected location does not exist.",
                "error",
            )
            return redirect(
                url_for("report_issue")
            )

        # -----------------------------------------------------
        # VALIDATE SUBCATEGORY
        # -----------------------------------------------------

        if subcategory_id is not None:

            subcategory = database.fetch_one(
                """
                SELECT
                    id,
                    category_id,
                    name
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
                flash(
                    "The selected subcategory is not valid "
                    "for that category.",
                    "error",
                )
                return redirect(
                    url_for("report_issue")
                )

        # -----------------------------------------------------
        # TRIAGE
        # -----------------------------------------------------

        try:

            triage_result = triage_engine.triage(
                category_id=category_id,
                subcategory_id=subcategory_id,
                location_id=location_id,
                impact=impact,
            )

            # -------------------------------------------------
            # CREATE ISSUE
            # -------------------------------------------------

            issue_id = database.execute_insert(
                """
                INSERT INTO issues (
                    title,
                    description,
                    category_id,
                    subcategory_id,
                    location_id,
                    specific_area,
                    priority,
                    status,
                    department_id,
                    reporter_id,
                    due_at
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    'TRIAGED',
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    title,
                    description,
                    category_id,
                    subcategory_id,
                    location_id,
                    specific_area or None,
                    triage_result.priority,
                    triage_result.department_id,
                    reporter["id"],
                    triage_result.due_at.isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            # -------------------------------------------------
            # HISTORY
            # -------------------------------------------------

            triage_note = (
                "Issue submitted through ResolveX. "
                f"Category: {category['name']}. "
                f"Impact: {impact}. "
                f"Priority: {triage_result.priority}. "
                f"Department: "
                f"{triage_result.department_name or 'Unassigned'}. "
                f"Related recent issues: "
                f"{triage_result.related_issue_count}. "
                f"Recurring flag: "
                f"{'Yes' if triage_result.recurring else 'No'}."
            )

            database.execute(
                """
                INSERT INTO issue_history (
                    issue_id,
                    user_id,
                    action,
                    note
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    issue_id,
                    reporter["id"],
                    "ISSUE_TRIAGED",
                    triage_note,
                ),
            )

            # -------------------------------------------------
            # RECURRING ISSUE EVENT
            # -------------------------------------------------

            if triage_result.recurring:

                recurring_note = (
                    "ResolveX detected a recurring issue pattern "
                    "at the selected location and category. "
                    f"{triage_result.related_issue_count} "
                    "related open/recent issues were found."
                )

                database.execute(
                    """
                    INSERT INTO issue_history (
                        issue_id,
                        user_id,
                        action,
                        note
                    )
                    VALUES (
                        ?,
                        ?,
                        ?,
                        ?
                    )
                    """,
                    (
                        issue_id,
                        reporter["id"],
                        "RECURRING_PATTERN_DETECTED",
                        recurring_note,
                    ),
                )

        except ValueError as exc:

            flash(
                str(exc),
                "error",
            )

            return redirect(
                url_for("report_issue")
            )

        except Exception:

            app.logger.exception(
                "Unexpected error while creating ResolveX issue."
            )

            flash(
                "We couldn't process your issue right now. "
                "Please try again.",
                "error",
            )

            return redirect(
                url_for("report_issue")
            )

        flash(
            f"Issue RX-{issue_id:04d} was successfully created.",
            "success",
        )

        return redirect(
            url_for(
                "issue_created",
                issue_id=issue_id,
            )
        )

    # ---------------------------------------------------------
    # MY ISSUES
    # ---------------------------------------------------------

    @app.get("/my-issues")
    @role_required("reporter")
    def my_issues():
        filter_name = request.args.get("filter", "all").lower()
        filter_statuses = {
            "all": None,
            "active": ("REPORTED", "TRIAGED", "ASSIGNED", "IN_PROGRESS", "REOPENED"),
            "resolved": ("RESOLVED", "VERIFIED"),
            "closed": ("CLOSED",),
        }
        if filter_name not in filter_statuses:
            filter_name = "all"

        statuses = filter_statuses[filter_name]
        status_clause = ""
        parameters = [session["user_id"]]
        if statuses:
            placeholders = ", ".join("?" for _ in statuses)
            status_clause = f"AND issues.status IN ({placeholders})"
            parameters.extend(statuses)

        issues = database.fetch_all(
            f"""
            SELECT issues.id, issues.title, issues.priority, issues.status,
                   issues.created_at, issues.updated_at, issues.specific_area,
                   categories.name AS category_name,
                   subcategories.name AS subcategory_name,
                   locations.building, locations.floor, locations.room
            FROM issues
            JOIN categories ON categories.id = issues.category_id
            LEFT JOIN subcategories ON subcategories.id = issues.subcategory_id
            JOIN locations ON locations.id = issues.location_id
            WHERE issues.reporter_id = ? {status_clause}
            ORDER BY datetime(issues.updated_at) DESC,
                     datetime(issues.created_at) DESC
            """,
            parameters,
        )

        return render_template(
            "my_issues.html",
            issues=issues,
            active_filter=filter_name,
        )

    # ---------------------------------------------------------
    # ISSUE CREATED / TRACKING
    # ---------------------------------------------------------

    @app.get("/issue-created/<int:issue_id>")
    @login_required
    def issue_created(issue_id: int):

        issue = database.fetch_one(
            """
            SELECT
                issues.id,
                issues.title,
                issues.description,
                issues.priority,
                issues.status,
                issues.reporter_id,
                issues.assigned_to,
                issues.department_id,
                issues.created_at,
                issues.due_at,
                issues.specific_area,

                categories.name
                    AS category_name,

                subcategories.name
                    AS subcategory_name,

                locations.building,
                locations.floor,
                locations.room,
                locations.facility_type,

                departments.name
                    AS department_name,

                users.name
                    AS assignee_name

            FROM issues

            JOIN categories
                ON categories.id = issues.category_id

            LEFT JOIN subcategories
                ON subcategories.id = issues.subcategory_id

            JOIN locations
                ON locations.id = issues.location_id

            LEFT JOIN departments
                ON departments.id = issues.department_id

            LEFT JOIN users
                ON users.id = issues.assigned_to

            WHERE issues.id = ?
            """,
            (issue_id,),
        )

        if not issue:
            return (
                render_template(
                    "error.html",
                    message="Issue not found.",
                ),
                404,
            )

        if (
            session.get("role") == "reporter"
            and issue["reporter_id"] != session["user_id"]
        ):
            return (
                render_template(
                    "error.html",
                    message="You can only view issues that you reported.",
                ),
                403,
            )

        if (
            session.get("role") == "technician"
            and issue["assigned_to"] != session["user_id"]
        ):
            return (
                render_template(
                    "error.html",
                    message="You can only view issues assigned to you.",
                ),
                403,
            )

        history = database.fetch_all(
            """
            SELECT
                issue_history.id,
                issue_history.action,
                issue_history.note,
                issue_history.timestamp,

                users.name
                    AS user_name

            FROM issue_history

            LEFT JOIN users
                ON users.id = issue_history.user_id

            WHERE issue_history.issue_id = ?

            ORDER BY
                issue_history.timestamp ASC,
                issue_history.id ASC
            """,
            (issue_id,),
        )

        return render_template(
            "issue_detail.html",
            issue=issue,
            history=history,
            departments=database.fetch_all(
                "SELECT id, name FROM departments ORDER BY name"
            ),
            technicians=database.fetch_all(
                "SELECT id, name FROM users WHERE role = 'technician' ORDER BY name"
            ),
        )

    @app.post("/issues/<int:issue_id>/verification")
    @role_required("reporter")
    def verify_issue(issue_id: int):
        action = request.form.get("action", "")
        issue = database.fetch_one(
            "SELECT id, status, reporter_id FROM issues WHERE id = ?",
            (issue_id,),
        )
        reporter = database.fetch_one(
            "SELECT id FROM users WHERE id = ? AND role = 'reporter'",
            (session["user_id"],),
        )

        transitions = {
            ("confirm", "RESOLVED"): ("VERIFIED", "RESOLUTION_VERIFIED"),
            ("close", "VERIFIED"): ("CLOSED", "ISSUE_CLOSED"),
            ("reopen", "RESOLVED"): ("REOPENED", "ISSUE_REOPENED"),
            ("reopen", "VERIFIED"): ("REOPENED", "ISSUE_REOPENED"),
        }
        transition = transitions.get((action, issue["status"])) if issue else None
        if not issue or not reporter or issue["reporter_id"] != reporter["id"] or not transition:
            flash("That verification action is not available for this issue.", "error")
            return redirect(url_for("issue_created", issue_id=issue_id))

        new_status, history_action = transition
        database.execute(
            """
            UPDATE issues
            SET status = ?, updated_at = CURRENT_TIMESTAMP,
                closed_at = CASE WHEN ? = 'CLOSED' THEN CURRENT_TIMESTAMP ELSE closed_at END
            WHERE id = ?
            """,
            (new_status, new_status, issue_id),
        )
        database.execute(
            """
            INSERT INTO issue_history (issue_id, user_id, action, note)
            VALUES (?, ?, ?, ?)
            """,
            (issue_id, reporter["id"], history_action, "Reporter confirmed the workflow action."),
        )
        flash(f"Issue RX-{issue_id:04d} is now {new_status.replace('_', ' ').lower()}.", "success")
        return redirect(url_for("issue_created", issue_id=issue_id))

    # ---------------------------------------------------------
    # ADMIN OPERATIONS CENTER
    # ---------------------------------------------------------

    @app.get("/dashboard")
    @role_required("admin")
    def dashboard():
        return render_template(
            "dashboard.html",
            metrics=analytics.summary(),
            resolution_metrics=analytics.resolution_metrics(),
            categories=analytics.category_breakdown(),
            buildings=analytics.building_breakdown(),
            trend=analytics.new_vs_resolved(),
            recurring=analytics.recurring_issues(),
            workloads=analytics.department_workload(),
            attention=analytics.attention_items(),
        )

    @app.get("/issues")
    @role_required("admin")
    def issues():
        filters = {
            "status": request.args.get("status", "").upper(),
            "priority": request.args.get("priority", "").upper(),
            "category_id": request.args.get("category_id", ""),
            "department_id": request.args.get("department_id", ""),
            "technician_id": request.args.get("technician_id", ""),
            "building": request.args.get("building", "").strip(),
            "from_date": request.args.get("from_date", ""),
            "to_date": request.args.get("to_date", ""),
            "overdue": request.args.get("overdue", "") == "1",
            "high_priority": request.args.get("high_priority", "") == "1",
            "search": request.args.get("search", "").strip(),
        }

        clauses = []
        parameters = []
        if filters["status"]:
            clauses.append("issues.status = ?")
            parameters.append(filters["status"])
        if filters["priority"]:
            clauses.append("issues.priority = ?")
            parameters.append(filters["priority"])
        if filters["category_id"].isdigit():
            clauses.append("issues.category_id = ?")
            parameters.append(int(filters["category_id"]))
        if filters["department_id"].isdigit():
            clauses.append("issues.department_id = ?")
            parameters.append(int(filters["department_id"]))
        if filters["technician_id"].isdigit():
            clauses.append("issues.assigned_to = ?")
            parameters.append(int(filters["technician_id"]))
        if filters["building"]:
            clauses.append("locations.building = ?")
            parameters.append(filters["building"])
        for key, operator in (("from_date", ">="), ("to_date", "<=")):
            if filters[key]:
                try:
                    datetime.strptime(filters[key], "%Y-%m-%d")
                except ValueError:
                    filters[key] = ""
                else:
                    boundary = f"{filters[key]} {'00:00:00' if key == 'from_date' else '23:59:59'}"
                    clauses.append(f"datetime(issues.created_at) {operator} ?")
                    parameters.append(boundary)
        if filters["overdue"]:
            clauses.append(
                "issues.due_at IS NOT NULL AND datetime(issues.due_at) < datetime('now') "
                "AND issues.status NOT IN ('RESOLVED', 'VERIFIED', 'CLOSED')"
            )
        if filters["high_priority"]:
            clauses.append("issues.priority IN ('HIGH', 'CRITICAL')")
        if filters["search"]:
            clauses.append(
                "(CAST(issues.id AS TEXT) LIKE ? OR issues.title LIKE ? "
                "OR issues.description LIKE ? OR locations.building LIKE ? "
                "OR issues.specific_area LIKE ?)"
            )
            search_term = f"%{filters['search']}%"
            parameters.extend([search_term] * 5)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        issue_rows = database.fetch_all(
            f"""
            SELECT issues.id, issues.title, issues.priority, issues.status,
                   issues.created_at, issues.due_at,
                   categories.name AS category_name,
                   locations.building, locations.floor, locations.room,
                   departments.name AS department_name,
                   users.name AS assignee_name
            FROM issues
            JOIN categories ON categories.id = issues.category_id
            JOIN locations ON locations.id = issues.location_id
            LEFT JOIN departments ON departments.id = issues.department_id
            LEFT JOIN users ON users.id = issues.assigned_to
            {where}
            ORDER BY CASE issues.priority
                WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                datetime(issues.created_at) DESC
            """,
            parameters,
        )
        categories = database.fetch_all(
            "SELECT id, name FROM categories ORDER BY name"
        )
        technicians = database.fetch_all(
            "SELECT id, name FROM users WHERE role = 'technician' ORDER BY name"
        )
        departments = database.fetch_all(
            "SELECT id, name FROM departments ORDER BY name"
        )
        buildings = database.fetch_all(
            "SELECT DISTINCT building FROM locations ORDER BY building"
        )
        return render_template(
            "issues.html",
            issues=issue_rows,
            categories=categories,
            technicians=technicians,
            departments=departments,
            buildings=buildings,
            filters=filters,
        )

    @app.post("/issues/<int:issue_id>/assign")
    @role_required("admin")
    def assign_issue(issue_id: int):
        technician_id_raw = request.form.get("technician_id", "")
        department_id_raw = request.form.get("department_id", "")
        try:
            technician_id = int(technician_id_raw)
            department_id = (
                int(department_id_raw)
                if department_id_raw
                else None
            )
            assignment_manager.assign(
                issue_id,
                technician_id,
                actor_id=session["user_id"],
                department_id=department_id,
            )
        except (TypeError, ValueError) as exc:
            flash(str(exc) or "Select a valid technician.", "error")
            return redirect(url_for("issues"))
        flash(f"Issue RX-{issue_id:04d} assigned successfully.", "success")
        return redirect(url_for("issues"))

    @app.post("/issues/<int:issue_id>/status")
    @role_required("technician")
    def update_issue_status(issue_id: int):
        requested_status = request.form.get("status", "").upper()
        note = request.form.get("note", "").strip()
        allowed_transitions = {
            "ASSIGNED": {"IN_PROGRESS"},
            "IN_PROGRESS": {"RESOLVED"},
            "REOPENED": {"IN_PROGRESS"},
        }

        technician = database.fetch_one(
                        """
                        SELECT id
                        FROM users
                        WHERE id = ?
                            AND role = 'technician'
                        """,
                        (session["user_id"],),
        )
        issue = database.fetch_one(
            "SELECT id, status, assigned_to FROM issues WHERE id = ?",
            (issue_id,),
        )

        if not issue or not technician:
            flash("That issue or technician account could not be found.", "error")
            return redirect(url_for("staff_queue"))
        if issue["assigned_to"] != technician["id"]:
            flash("Only the assigned technician can update this issue.", "error")
            return redirect(url_for("staff_queue"))
        if requested_status not in allowed_transitions.get(issue["status"], set()):
            flash("That status change is not allowed from the current state.", "error")
            return redirect(url_for("staff_queue"))
        if requested_status == "RESOLVED" and not note:
            flash("Add a work note before marking the issue resolved.", "error")
            return redirect(url_for("staff_queue"))
        if len(note) > 500:
            flash("The work note must be 500 characters or less.", "error")
            return redirect(url_for("staff_queue"))

        database.execute(
            """
            UPDATE issues
            SET status = ?, updated_at = CURRENT_TIMESTAMP,
                resolved_at = CASE WHEN ? = 'RESOLVED' THEN CURRENT_TIMESTAMP ELSE resolved_at END
            WHERE id = ?
            """,
            (requested_status, requested_status, issue_id),
        )
        database.execute(
            """
            INSERT INTO issue_history (issue_id, user_id, action, note)
            VALUES (?, ?, ?, ?)
            """,
            (issue_id, technician["id"], f"STATUS_{requested_status}", note or None),
        )
        flash(f"Issue RX-{issue_id:04d} updated.", "success")
        return redirect(url_for("staff_queue"))

    # ---------------------------------------------------------
    # STAFF WORK QUEUE
    # ---------------------------------------------------------

    @app.get("/staff")
    @role_required("technician")
    def staff_queue():

        technician = database.fetch_one(
            """
            SELECT
                id,
                name,
                email
            FROM users
            WHERE id = ?
              AND role = 'technician'
            """
            , (session["user_id"],)
        )

        if not technician:
            return (
                render_template(
                    "error.html",
                    message=(
                        "No technician account is configured."
                    ),
                ),
                500,
            )

        technician_id = technician["id"]

        # -----------------------------------------------------
        # ACTIVE ASSIGNED ISSUES
        # -----------------------------------------------------

        issues = database.fetch_all(
            """
            SELECT
                issues.id,
                issues.title,
                issues.priority,
                issues.status,
                issues.created_at,
                issues.due_at,

                categories.name
                    AS category_name,

                subcategories.name
                    AS subcategory_name,

                locations.building,
                locations.floor,
                locations.room,

                departments.name
                    AS department_name

            FROM issues

            JOIN categories
                ON categories.id = issues.category_id

            LEFT JOIN subcategories
                ON subcategories.id = issues.subcategory_id

            JOIN locations
                ON locations.id = issues.location_id

            LEFT JOIN departments
                ON departments.id = issues.department_id

            WHERE issues.assigned_to = ?

              AND issues.status NOT IN (
                  'RESOLVED',
                  'VERIFIED',
                  'CLOSED'
              )

            ORDER BY

                CASE issues.priority
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 4
                    ELSE 5
                END,

                CASE
                    WHEN issues.due_at IS NOT NULL
                     AND datetime(issues.due_at)
                         < datetime('now')
                    THEN 1
                    ELSE 2
                END,

                datetime(issues.created_at) ASC
            """,
            (technician_id,),
        )

        # -----------------------------------------------------
        # QUEUE METRICS
        # -----------------------------------------------------

        active_count = database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM issues
            WHERE assigned_to = ?
              AND status NOT IN (
                  'RESOLVED',
                  'VERIFIED',
                  'CLOSED'
              )
            """,
            (technician_id,),
        )

        high_priority_count = database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM issues
            WHERE assigned_to = ?
              AND priority IN (
                  'HIGH',
                  'CRITICAL'
              )
              AND status NOT IN (
                  'RESOLVED',
                  'VERIFIED',
                  'CLOSED'
              )
            """,
            (technician_id,),
        )

        overdue_count = database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM issues
            WHERE assigned_to = ?
              AND due_at IS NOT NULL
              AND datetime(due_at) < datetime('now')
              AND status NOT IN (
                  'RESOLVED',
                  'VERIFIED',
                  'CLOSED'
              )
            """,
            (technician_id,),
        )

        in_progress_count = database.fetch_one(
            """
            SELECT COUNT(*) AS count
            FROM issues
            WHERE assigned_to = ?
              AND status = 'IN_PROGRESS'
            """,
            (technician_id,),
        )

        return render_template(
            "staff_queue.html",
            technician=technician,
            issues=issues,
            metrics={
                "active": active_count["count"],
                "high_priority": high_priority_count["count"],
                "overdue": overdue_count["count"],
                "in_progress": in_progress_count["count"],
            },
        )

    # ---------------------------------------------------------
    # ERROR HANDLERS
    # ---------------------------------------------------------

    @app.errorhandler(404)
    def not_found(error):
        return (
            render_template(
                "error.html",
                message=(
                    "The page you're looking for "
                    "doesn't exist."
                ),
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):

        app.logger.exception(
            "Internal server error."
        )

        return (
            render_template(
                "error.html",
                message=(
                    "Something went wrong while processing "
                    "your request."
                ),
            ),
            500,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
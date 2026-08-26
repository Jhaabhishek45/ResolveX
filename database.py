import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable

from config import DATABASE_PATH


class DatabaseManager:
    """
    Centralized SQLite access layer for ResolveX.

    Responsibilities:
    - Create and initialize the database
    - Manage connections safely
    - Enforce foreign-key constraints
    - Execute parameterized queries
    """

    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = database_path
        self.initialize_database()

    @contextmanager
    def connection(self):
        """
        Provide a managed SQLite connection.

        Commits on success and rolls back on failure.
        """
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize_database(self):
        """Create all ResolveX tables and indexes."""

        with self.connection() as connection:
            cursor = connection.cursor()

            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL
                        CHECK (
                            role IN (
                                'reporter',
                                'technician',
                                'admin'
                            )
                        ),
                    created_at DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS subcategories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,

                    created_at DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (category_id)
                        REFERENCES categories(id)
                        ON DELETE CASCADE,

                    UNIQUE(category_id, name)
                );

                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    building TEXT NOT NULL,
                    floor TEXT,
                    room TEXT,
                    facility_type TEXT,

                    created_at DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(building, floor, room)
                );

                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    title TEXT NOT NULL,
                    description TEXT NOT NULL,

                    category_id INTEGER NOT NULL,
                    subcategory_id INTEGER,

                    location_id INTEGER NOT NULL,

                    specific_area TEXT,

                    priority TEXT NOT NULL
                        DEFAULT 'MEDIUM'
                        CHECK (
                            priority IN (
                                'LOW',
                                'MEDIUM',
                                'HIGH',
                                'CRITICAL'
                            )
                        ),

                    status TEXT NOT NULL
                        DEFAULT 'REPORTED'
                        CHECK (
                            status IN (
                                'REPORTED',
                                'TRIAGED',
                                'ASSIGNED',
                                'IN_PROGRESS',
                                'RESOLVED',
                                'VERIFIED',
                                'CLOSED',
                                'REOPENED'
                            )
                        ),

                    department_id INTEGER,
                    assigned_to INTEGER,
                    reporter_id INTEGER NOT NULL,

                    created_at DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    updated_at DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    due_at DATETIME,
                    resolved_at DATETIME,
                    closed_at DATETIME,

                    FOREIGN KEY (category_id)
                        REFERENCES categories(id),

                    FOREIGN KEY (subcategory_id)
                        REFERENCES subcategories(id),

                    FOREIGN KEY (location_id)
                        REFERENCES locations(id),

                    FOREIGN KEY (department_id)
                        REFERENCES departments(id),

                    FOREIGN KEY (assigned_to)
                        REFERENCES users(id),

                    FOREIGN KEY (reporter_id)
                        REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS issue_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    issue_id INTEGER NOT NULL,
                    user_id INTEGER,

                    action TEXT NOT NULL,
                    note TEXT,

                    timestamp DATETIME NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (issue_id)
                        REFERENCES issues(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (user_id)
                        REFERENCES users(id)
                );

                CREATE INDEX IF NOT EXISTS idx_issues_status
                    ON issues(status);

                CREATE INDEX IF NOT EXISTS idx_issues_priority
                    ON issues(priority);

                CREATE INDEX IF NOT EXISTS idx_issues_category
                    ON issues(category_id);

                CREATE INDEX IF NOT EXISTS idx_issues_location
                    ON issues(location_id);

                CREATE INDEX IF NOT EXISTS idx_issues_department
                    ON issues(department_id);

                CREATE INDEX IF NOT EXISTS idx_issues_reporter
                    ON issues(reporter_id);

                CREATE INDEX IF NOT EXISTS idx_issues_created_at
                    ON issues(created_at);

                CREATE INDEX IF NOT EXISTS idx_history_issue
                    ON issue_history(issue_id);

                CREATE INDEX IF NOT EXISTS idx_history_timestamp
                    ON issue_history(timestamp);
                """
            )

            issue_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(issues)"
                )
            }

            if "specific_area" not in issue_columns:
                connection.execute(
                    "ALTER TABLE issues ADD COLUMN specific_area TEXT"
                )

    def execute(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> int:
        """
        Execute INSERT/UPDATE/DELETE and return affected row count.
        """

        with self.connection() as connection:
            cursor = connection.execute(query, tuple(parameters))
            return cursor.rowcount

    def execute_insert(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ) -> int:
        """
        Execute INSERT and return the generated primary-key ID.
        """

        with self.connection() as connection:
            cursor = connection.execute(query, tuple(parameters))
            return int(cursor.lastrowid)

    def fetch_one(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ):
        """Return one row or None."""

        with self.connection() as connection:
            cursor = connection.execute(query, tuple(parameters))
            return cursor.fetchone()

    def fetch_all(
        self,
        query: str,
        parameters: Iterable[Any] = (),
    ):
        """Return all matching rows."""

        with self.connection() as connection:
            cursor = connection.execute(query, tuple(parameters))
            return cursor.fetchall()
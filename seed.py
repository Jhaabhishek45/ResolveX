from database import DatabaseManager


# DatabaseManager is created by the application and passed into seed().
# When seed.py is run directly, seed() creates its own database manager.
db = None


DEPARTMENTS = [
    ("IT Support", "Network, Wi-Fi, computers, printers and digital services."),
    ("AV & Technical Support", "Projectors, smart-class and presentation equipment."),
    ("Electrical Maintenance", "Power, lighting, sockets and electrical systems."),
    ("Facilities & Maintenance", "Building, furniture, AC and general maintenance."),
    ("Water & Sanitation", "Water supply, plumbing, washrooms and sanitation."),
    ("Campus Operations", "Common campus facilities and operational issues."),
    ("Library Support", "Library equipment, facilities and services."),
    ("Sports Facilities", "Sports infrastructure and equipment."),
    ("Safety & Security", "Campus safety and security-related facility issues."),
]


CATEGORIES = [
    (
        "Classroom & Academic",
        "Issues affecting classrooms, teaching equipment and academic spaces.",
    ),
    (
        "IT & Network",
        "Wi-Fi, internet, computers, printers and digital infrastructure.",
    ),
    (
        "Electrical & Power",
        "Power, lighting, switches, sockets and electrical problems.",
    ),
    (
        "Water & Sanitation",
        "Water supply, leakage, washrooms, drainage and cleanliness.",
    ),
    (
        "Facilities & Maintenance",
        "Building, furniture, AC and general maintenance.",
    ),
    (
        "Library",
        "Library facilities, equipment and study-space issues.",
    ),
    (
        "Sports & Recreation",
        "Sports facilities and recreational infrastructure.",
    ),
    (
        "Safety & Security",
        "Safety, access and security-related facility issues.",
    ),
]


SUBCATEGORIES = {
    "Classroom & Academic": [
        "Projector",
        "Smart Classroom Equipment",
        "Fan",
        "Air Conditioning",
        "Lighting",
        "Whiteboard",
        "Desk / Bench",
        "Chair",
        "Door / Lock",
        "Electrical Socket",
        "Classroom Cleanliness",
        "Other",
    ],
    "IT & Network": [
        "Wi-Fi",
        "Internet",
        "Computer / Desktop",
        "Printer",
        "Network Port",
        "Software",
        "Lab Equipment",
        "Other",
    ],
    "Electrical & Power": [
        "Power Failure",
        "Light",
        "Switch",
        "Electrical Socket",
        "Emergency Light",
        "Wiring / Electrical Safety",
        "Other",
    ],
    "Water & Sanitation": [
        "Drinking Water",
        "Water Leakage",
        "Washroom",
        "Wash Basin",
        "Drainage",
        "Cleaning",
        "Waste Disposal",
        "Other",
    ],
    "Facilities & Maintenance": [
        "Air Conditioning",
        "Furniture",
        "Lift / Elevator",
        "Door / Lock",
        "Window",
        "Building Damage",
        "Common Area",
        "Other",
    ],
    "Library": [
        "Computer",
        "Printer",
        "Lighting",
        "Air Conditioning",
        "Furniture",
        "Cleanliness",
        "Other",
    ],
    "Sports & Recreation": [
        "Sports Equipment",
        "Court / Playing Area",
        "Lighting",
        "Seating",
        "Cleanliness",
        "Other",
    ],
    "Safety & Security": [
        "Access / Lock",
        "Lighting",
        "Emergency Equipment",
        "Security Infrastructure",
        "Other",
    ],
}


# Verified SRM Ramapuram baseline locations.
# Exact floor/room data can be added later when verified.
LOCATIONS = [
    ("Main Block", None, None, "Academic"),
    ("Block III", None, None, "Academic"),
    ("Block 5", None, None, "Academic"),
    ("East Block", None, None, "Academic"),
    ("PG Block", None, None, "Academic"),
    ("BMS Block", None, None, "Academic"),
    ("Admin Block", None, None, "Administrative"),
    ("Sports Complex", None, None, "Sports"),
    ("Central Library", None, None, "Library"),
    ("MLCP / Fab Lab", None, None, "Specialized Facility"),
    ("Mechanical Workshop", None, None, "Workshop"),
    ("Dental Block", None, None, "Academic"),
    ("TRP / Hi-Tech Hall", None, None, "Event / Academic"),
    ("Hostel", None, None, "Residential"),
    ("Hospital", None, None, "Medical"),
    ("Canteen", None, None, "Food Facility"),
    ("Parking", None, None, "Transport"),
]


def seed_table(table, columns, rows):
    """Insert rows only when an equivalent record does not exist."""

    for row in rows:
        placeholders = ", ".join(["?"] * len(row))

        if table == "departments":
            existing = db.fetch_one(
                "SELECT id FROM departments WHERE name = ?",
                (row[0],),
            )

        elif table == "categories":
            existing = db.fetch_one(
                "SELECT id FROM categories WHERE name = ?",
                (row[0],),
            )

        elif table == "locations":
            existing = db.fetch_one(
                """
                SELECT id
                FROM locations
                WHERE building = ?
                  AND IFNULL(floor, '') = IFNULL(?, '')
                  AND IFNULL(room, '') = IFNULL(?, '')
                """,
                row[:3],
            )

        else:
            raise ValueError(f"Unsupported table: {table}")

        if existing:
            continue

        db.execute(
            f"""
            INSERT INTO {table} ({columns})
            VALUES ({placeholders})
            """,
            row,
        )


def seed_subcategories():
    for category_name, subcategories in SUBCATEGORIES.items():

        category = db.fetch_one(
            "SELECT id FROM categories WHERE name = ?",
            (category_name,),
        )

        if not category:
            continue

        category_id = category["id"]

        for name in subcategories:

            existing = db.fetch_one(
                """
                SELECT id
                FROM subcategories
                WHERE category_id = ?
                  AND name = ?
                """,
                (category_id, name),
            )

            if existing:
                continue

            db.execute(
                """
                INSERT INTO subcategories
                    (category_id, name)
                VALUES
                    (?, ?)
                """,
                (category_id, name),
            )


def seed_demo_users():
    users = [
        ("Abhishek Jha", "abhishek@resolvex.local", "reporter"),
        ("ResolveX Technician", "technician@resolvex.local", "technician"),
        ("ResolveX Admin", "admin@resolvex.local", "admin"),
    ]

    for name, email, role in users:
        existing = db.fetch_one(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        )

        if existing:
            continue

        db.execute(
            """
            INSERT INTO users (name, email, role)
            VALUES (?, ?, ?)
            """,
            (name, email, role),
        )


def seed_demo_issues():
    """Create repeatable, clearly labeled records for demonstrations."""

    reporter = db.fetch_one(
        "SELECT id FROM users WHERE email = ?",
        ("abhishek@resolvex.local",),
    )

    technician = db.fetch_one(
        "SELECT id FROM users WHERE email = ?",
        ("technician@resolvex.local",),
    )

    demo_issues = [
        {
            "title": "Projector has no display",
            "description": "The teaching projector is powered on but shows no display.",
            "category": "Classroom & Academic",
            "subcategory": "Projector",
            "building": "Block 5",
            "specific_area": "Teaching presentation area",
            "priority": "HIGH",
            "status": "TRIAGED",
            "offset": "-1 days",
            "due": "+36 hours",
        },
        {
            "title": "AC not cooling in classroom",
            "description": "The air-conditioning unit is running but the classroom remains warm.",
            "category": "Facilities & Maintenance",
            "subcategory": "Air Conditioning",
            "building": "Main Block",
            "specific_area": "Shared teaching space",
            "priority": "MEDIUM",
            "status": "ASSIGNED",
            "offset": "-2 days",
            "due": "+72 hours",
            "assigned": True,
        },
        {
            "title": "Power socket not functioning",
            "description": "The wall socket does not provide power for classroom equipment.",
            "category": "Electrical & Power",
            "subcategory": "Electrical Socket",
            "building": "East Block",
            "specific_area": "Equipment connection point",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "offset": "-3 days",
            "due": "+12 hours",
            "assigned": True,
        },
        {
            "title": "Printer unavailable",
            "description": "The shared printer is unavailable for library users.",
            "category": "Library",
            "subcategory": "Printer",
            "building": "Central Library",
            "specific_area": "Service desk",
            "priority": "LOW",
            "status": "CLOSED",
            "offset": "-4 days",
            "due": "-2 days",
            "resolved": True,
        },
        {
            "title": "Water leakage near Block III",
            "description": "Water is collecting near the shared water point and needs maintenance attention.",
            "category": "Water & Sanitation",
            "subcategory": "Water Leakage",
            "building": "Block III",
            "specific_area": "Ground-floor water point",
            "priority": "HIGH",
            "status": "REOPENED",
            "offset": "-5 days",
            "due": "+10 hours",
        },
        {
            "title": "Drinking water unavailable near Block III",
            "description": "The drinking water supply is unavailable near Block III.",
            "category": "Water & Sanitation",
            "subcategory": "Drinking Water",
            "building": "Block III",
            "specific_area": "Ground-floor water point",
            "priority": "HIGH",
            "status": "TRIAGED",
            "offset": "-6 days",
            "due": "+18 hours",
        },
    ]

    for item in demo_issues:

        if db.fetch_one(
            "SELECT id FROM issues WHERE title = ?",
            (item["title"],),
        ):
            continue

        category = db.fetch_one(
            "SELECT id FROM categories WHERE name = ?",
            (item["category"],),
        )

        subcategory = db.fetch_one(
            """
            SELECT id FROM subcategories
            WHERE category_id = ? AND name = ?
            """,
            (category["id"], item["subcategory"]),
        )

        location = db.fetch_one(
            "SELECT id FROM locations WHERE building = ?",
            (item["building"],),
        )

        department = db.fetch_one(
            "SELECT id FROM departments WHERE name = ?",
            (triage_department(item["subcategory"]),),
        )

        resolved_at = (
            "datetime('now', '-1 days')"
            if item.get("resolved")
            else "NULL"
        )

        closed_at = (
            "datetime('now', '-1 days')"
            if item.get("resolved")
            else "NULL"
        )

        assigned_to = (
            technician["id"]
            if item.get("assigned")
            else None
        )

        issue_id = db.execute_insert(
            f"""
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
                assigned_to,
                reporter_id,
                created_at,
                updated_at,
                due_at,
                resolved_at,
                closed_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                datetime('now', ?),
                datetime('now'),
                datetime('now', ?),
                {resolved_at},
                {closed_at}
            )
            """,
            (
                item["title"],
                item["description"],
                category["id"],
                subcategory["id"],
                location["id"],
                item["specific_area"],
                item["priority"],
                item["status"],
                department["id"],
                assigned_to,
                reporter["id"],
                item["offset"],
                item["due"],
            ),
        )

        db.execute(
            """
            INSERT INTO issue_history
                (issue_id, user_id, action, note)
            VALUES (?, ?, ?, ?)
            """,
            (
                issue_id,
                technician["id"] if assigned_to else reporter["id"],
                "DEMO_RECORD_SEEDED",
                "Clearly labeled ResolveX demonstration record.",
            ),
        )


def triage_department(subcategory):
    """Return the existing operational team for seeded demo data."""

    return {
        "Projector": "AV & Technical Support",
        "Air Conditioning": "Facilities & Maintenance",
        "Electrical Socket": "Electrical Maintenance",
        "Printer": "Library Support",
        "Water Leakage": "Water & Sanitation",
        "Drinking Water": "Water & Sanitation",
    }[subcategory]


def seed(database=None):
    """
    Seed ResolveX master data and demo records.

    When called from app.py, use the existing DatabaseManager.
    When run directly, create a new DatabaseManager.
    """
    global db

    db = database or DatabaseManager()

    seed_table(
        "departments",
        "name, description",
        DEPARTMENTS,
    )

    seed_table(
        "categories",
        "name, description",
        CATEGORIES,
    )

    seed_subcategories()

    seed_table(
        "locations",
        "building, floor, room, facility_type",
        LOCATIONS,
    )

    seed_demo_users()
    seed_demo_issues()

    print("ResolveX master data seeded successfully.")


if __name__ == "__main__":
    seed()
from database import DatabaseManager


db = DatabaseManager()


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
    ("Classroom & Academic", "Issues affecting classrooms, teaching equipment and academic spaces."),
    ("IT & Network", "Wi-Fi, internet, computers, printers and digital infrastructure."),
    ("Electrical & Power", "Power, lighting, switches, sockets and electrical problems."),
    ("Water & Sanitation", "Water supply, leakage, washrooms, drainage and cleanliness."),
    ("Facilities & Maintenance", "Building, furniture, AC and general maintenance."),
    ("Library", "Library facilities, equipment and study-space issues."),
    ("Sports & Recreation", "Sports facilities and recreational infrastructure."),
    ("Safety & Security", "Safety, access and security-related facility issues."),
]

SUBCATEGORIES = {
    "Classroom & Academic": ["Projector", "Smart Classroom Equipment", "Fan", "Air Conditioning", "Lighting", "Whiteboard", "Desk / Bench", "Chair", "Door / Lock", "Electrical Socket", "Classroom Cleanliness", "Other"],
    "IT & Network": ["Wi-Fi", "Internet", "Computer / Desktop", "Printer", "Network Port", "Software", "Lab Equipment", "Other"],
    "Electrical & Power": ["Power Failure", "Light", "Switch", "Electrical Socket", "Emergency Light", "Wiring / Electrical Safety", "Other"],
    "Water & Sanitation": ["Drinking Water", "Water Leakage", "Washroom", "Wash Basin", "Drainage", "Cleaning", "Waste Disposal", "Other"],
    "Facilities & Maintenance": ["Air Conditioning", "Furniture", "Lift / Elevator", "Door / Lock", "Window", "Building Damage", "Common Area", "Other"],
    "Library": ["Computer", "Printer", "Lighting", "Air Conditioning", "Furniture", "Cleanliness", "Other"],
    "Sports & Recreation": ["Sports Equipment", "Court / Playing Area", "Lighting", "Seating", "Cleanliness", "Other"],
    "Safety & Security": ["Access / Lock", "Lighting", "Emergency Equipment", "Security Infrastructure", "Other"],
}

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
    for row in rows:
        placeholders = ", ".join(["?"] * len(row))
        if table == "departments":
            existing = db.fetch_one("SELECT id FROM departments WHERE name = ?", (row[0],))
        elif table == "categories":
            existing = db.fetch_one("SELECT id FROM categories WHERE name = ?", (row[0],))
        elif table == "locations":
            existing = db.fetch_one(
                "SELECT id FROM locations WHERE building = ? AND IFNULL(floor, '') = IFNULL(?, '') AND IFNULL(room, '') = IFNULL(?, '')",
                row[:3],
            )
        else:
            raise ValueError(f"Unsupported table: {table}")
        if existing:
            continue
        db.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", row)


def seed_subcategories():
    for category_name, subcategories in SUBCATEGORIES.items():
        category = db.fetch_one("SELECT id FROM categories WHERE name = ?", (category_name,))
        if not category:
            continue
        for name in subcategories:
            existing = db.fetch_one(
                "SELECT id FROM subcategories WHERE category_id = ? AND name = ?",
                (category["id"], name),
            )
            if not existing:
                db.execute(
                    "INSERT INTO subcategories (category_id, name) VALUES (?, ?)",
                    (category["id"], name),
                )


def seed_demo_users():
    """Ensure the three demo accounts always have the correct roles."""
    users = [
        ("Abhishek Jha", "abhishek@resolvex.local", "reporter"),
        ("ResolveX Technician", "technician@resolvex.local", "technician"),
        ("ResolveX Admin", "admin@resolvex.local", "admin"),
    ]

    for name, email, role in users:
        existing = db.fetch_one("SELECT id FROM users WHERE email = ?", (email,))
        if existing:
            # Repair only the demo account's identity/role. Do not delete data.
            db.execute(
                "UPDATE users SET name = ?, role = ? WHERE id = ?",
                (name, role, existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
                (name, email, role),
            )


def seed_demo_issues():
    return


def seed():
    seed_table("departments", "name, description", DEPARTMENTS)
    seed_table("categories", "name, description", CATEGORIES)
    seed_subcategories()
    seed_table("locations", "building, floor, room, facility_type", LOCATIONS)
    seed_demo_users()
    seed_demo_issues()
    print("ResolveX master data seeded successfully.")


if __name__ == "__main__":
    seed()

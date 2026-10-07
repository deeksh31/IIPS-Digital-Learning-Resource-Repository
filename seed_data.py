import sqlite3
import os
from datetime import datetime

DB_NAME = "iips.db"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

resources = [
    {
        "title": "Python Programming Basics",
        "description": "Basic Python programming notes covering variables, data types, conditions, loops and functions.",
        "category": "Programming",
        "file": "python_programming_basics.txt"
    },
    {
        "title": "Data Structures and Algorithms",
        "description": "Study material covering arrays, lists, stacks, queues, searching and sorting.",
        "category": "Programming",
        "file": "data_structures_algorithms.txt"
    },
    {
        "title": "Database Management Systems",
        "description": "DBMS notes covering database concepts, SQL, normalization and transactions.",
        "category": "Database",
        "file": "dbms_notes.txt"
    },
    {
        "title": "Web Development Fundamentals",
        "description": "Introduction to HTML, CSS, JavaScript and basic web development concepts.",
        "category": "Web Development",
        "file": "web_development.txt"
    },
    {
        "title": "Machine Learning Introduction",
        "description": "Introduction to supervised learning, unsupervised learning, classification and regression.",
        "category": "Artificial Intelligence",
        "file": "machine_learning.txt"
    },
    {
        "title": "Software Engineering Notes",
        "description": "Software engineering fundamentals, SDLC models, requirements and software design.",
        "category": "Software Engineering",
        "file": "software_engineering.txt"
    },
    {
        "title": "Object Oriented Analysis and Design",
        "description": "OOAD study material covering objects, classes, use cases, UML and design concepts.",
        "category": "OOAD",
        "file": "ooad_notes.txt"
    },
    {
        "title": "Computer Networks Notes",
        "description": "Computer networking concepts including OSI model, TCP/IP, protocols and network security.",
        "category": "Networking",
        "file": "computer_networks.txt"
    },
    {
        "title": "Compiler Design Notes",
        "description": "Compiler design material covering lexical analysis, parsing, syntax analysis and code generation.",
        "category": "Computer Science",
        "file": "compiler_design.txt"
    },
    {
        "title": "Artificial Intelligence Fundamentals",
        "description": "Introduction to Artificial Intelligence, search techniques, knowledge representation and reasoning.",
        "category": "Artificial Intelligence",
        "file": "artificial_intelligence.txt"
    }
]


def create_demo_files():

    demo_content = {
        "python_programming_basics.txt":
            "IIPS Digital Learning Repository\n\nPython Programming Basics\n\n"
            "Topics:\n- Variables\n- Data Types\n- Conditions\n- Loops\n- Functions\n- Lists\n- Dictionaries\n",

        "data_structures_algorithms.txt":
            "IIPS Digital Learning Repository\n\nData Structures and Algorithms\n\n"
            "Topics:\n- Arrays\n- Lists\n- Stack\n- Queue\n- Searching\n- Sorting\n- Time Complexity\n",

        "dbms_notes.txt":
            "IIPS Digital Learning Repository\n\nDatabase Management Systems\n\n"
            "Topics:\n- Database Concepts\n- SQL\n- Keys\n- Normalization\n- Transactions\n",

        "web_development.txt":
            "IIPS Digital Learning Repository\n\nWeb Development Fundamentals\n\n"
            "Topics:\n- HTML\n- CSS\n- JavaScript\n- Responsive Design\n",

        "machine_learning.txt":
            "IIPS Digital Learning Repository\n\nMachine Learning Introduction\n\n"
            "Topics:\n- Supervised Learning\n- Unsupervised Learning\n- Classification\n- Regression\n",

        "software_engineering.txt":
            "IIPS Digital Learning Repository\n\nSoftware Engineering Notes\n\n"
            "Topics:\n- SDLC\n- Requirements\n- Design\n- Testing\n- Maintenance\n",

        "ooad_notes.txt":
            "IIPS Digital Learning Repository\n\nObject Oriented Analysis and Design\n\n"
            "Topics:\n- Objects\n- Classes\n- UML\n- Use Case Diagrams\n- Class Diagrams\n",

        "computer_networks.txt":
            "IIPS Digital Learning Repository\n\nComputer Networks Notes\n\n"
            "Topics:\n- OSI Model\n- TCP/IP\n- HTTP\n- DNS\n- Network Security\n",

        "compiler_design.txt":
            "IIPS Digital Learning Repository\n\nCompiler Design Notes\n\n"
            "Topics:\n- Lexical Analysis\n- Parsing\n- Syntax Analysis\n- Code Generation\n",

        "artificial_intelligence.txt":
            "IIPS Digital Learning Repository\n\nArtificial Intelligence Fundamentals\n\n"
            "Topics:\n- AI Agents\n- Search\n- Knowledge Representation\n- Reasoning\n"
    }

    for filename, content in demo_content.items():

        path = os.path.join(UPLOAD_FOLDER, filename)

        if not os.path.exists(path):

            with open(path, "w", encoding="utf-8") as file:
                file.write(content)


def seed():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get faculty user
    faculty = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        ("faculty@iips.com",)
    ).fetchone()

    if not faculty:
        print("Faculty account not found.")
        print("Run app.py once first so demo accounts are created.")
        conn.close()
        return

    faculty_id = faculty["id"]

    # Create categories if they don't exist
    category_ids = {}

    categories = [
        "Programming",
        "Database",
        "Web Development",
        "Artificial Intelligence",
        "Software Engineering",
        "OOAD",
        "Networking",
        "Computer Science"
    ]

    for category in categories:

        row = cursor.execute(
            "SELECT id FROM categories WHERE name = ?",
            (category,)
        ).fetchone()

        if row:
            category_ids[category] = row["id"]

        else:

            cursor.execute(
                "INSERT INTO categories (name) VALUES (?)",
                (category,)
            )

            category_ids[category] = cursor.lastrowid

    create_demo_files()

    # Check existing resources
    existing = cursor.execute(
        "SELECT title FROM resources"
    ).fetchall()

    existing_titles = {
        row["title"] for row in existing
    }

    added = 0

    for resource in resources:

        if resource["title"] in existing_titles:
            continue

        filename = resource["file"]

        cursor.execute(
            """
            INSERT INTO resources
            (
                title,
                description,
                filename,
                original_filename,
                file_type,
                uploader_id,
                category_id,
                status,
                upload_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resource["title"],
                resource["description"],
                filename,
                filename,
                "text/plain",
                faculty_id,
                category_ids[resource["category"]],
                "approved",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        added += 1

    conn.commit()
    conn.close()

    print()
    print("=" * 50)
    print("IIPS DEMO RESOURCES ADDED")
    print("=" * 50)
    print(f"Resources added: {added}")
   
if __name__ == "__main__":
    seed()
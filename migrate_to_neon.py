import os
import sqlite3
from datetime import datetime

from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURATION
# ============================================================

SQLITE_DATABASE = "database.db"

NEON_DATABASE_URL = os.environ.get("DATABASE_URL")

if not NEON_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Set your Neon PostgreSQL connection string first."
    )

# Support connection strings that start with postgres://
if NEON_DATABASE_URL.startswith("postgres://"):
    NEON_DATABASE_URL = NEON_DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


# ============================================================
# CONNECT TO DATABASES
# ============================================================

print("Connecting to local SQLite database...")

sqlite_conn = sqlite3.connect(SQLITE_DATABASE)
sqlite_conn.row_factory = sqlite3.Row

print("Connecting to Neon PostgreSQL...")

engine = create_engine(NEON_DATABASE_URL)


# ============================================================
# CREATE TABLES IN NEON
# ============================================================

with engine.begin() as conn:

    print("Creating tables in Neon...")

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            image VARCHAR(100),
            github VARCHAR(200),
            demo VARCHAR(200)
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS "user" (
            id INTEGER PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(200) NOT NULL
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS message (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """))


# ============================================================
# MIGRATE PROJECTS
# ============================================================

projects = sqlite_conn.execute(
    "SELECT * FROM project"
).fetchall()

print(f"Found {len(projects)} project(s).")

with engine.begin() as conn:

    for project in projects:

        exists = conn.execute(
            text("SELECT id FROM project WHERE id = :id"),
            {"id": project["id"]}
        ).fetchone()

        if exists:
            print(f"Project {project['id']} already exists. Skipping.")
            continue

        conn.execute(
            text("""
                INSERT INTO project
                (id, title, description, image, github, demo)
                VALUES
                (:id, :title, :description, :image, :github, :demo)
            """),
            {
                "id": project["id"],
                "title": project["title"],
                "description": project["description"],
                "image": project["image"],
                "github": project["github"],
                "demo": project["demo"],
            }
        )

        print(f"Migrated project: {project['title']}")


# ============================================================
# MIGRATE USERS
# ============================================================

users = sqlite_conn.execute(
    'SELECT * FROM user'
).fetchall()

print(f"Found {len(users)} user(s).")

with engine.begin() as conn:

    for user in users:

        exists = conn.execute(
            text('SELECT id FROM "user" WHERE id = :id'),
            {"id": user["id"]}
        ).fetchone()

        if exists:
            print(f"User {user['id']} already exists. Skipping.")
            continue

        conn.execute(
            text("""
                INSERT INTO "user"
                (id, username, password)
                VALUES
                (:id, :username, :password)
            """),
            {
                "id": user["id"],
                "username": user["username"],
                "password": user["password"],
            }
        )

        print(f"Migrated user: {user['username']}")


# ============================================================
# MIGRATE MESSAGES
# ============================================================

messages = sqlite_conn.execute(
    "SELECT * FROM message"
).fetchall()

print(f"Found {len(messages)} message(s).")

with engine.begin() as conn:

    for message in messages:

        exists = conn.execute(
            text("SELECT id FROM message WHERE id = :id"),
            {"id": message["id"]}
        ).fetchone()

        if exists:
            print(f"Message {message['id']} already exists. Skipping.")
            continue

        created_at = message["created_at"]

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        conn.execute(
            text("""
                INSERT INTO message
                (id, name, email, body, created_at)
                VALUES
                (:id, :name, :email, :body, :created_at)
            """),
            {
                "id": message["id"],
                "name": message["name"],
                "email": message["email"],
                "body": message["body"],
                "created_at": created_at,
            }
        )

        print(f"Migrated message {message['id']}")


# ============================================================
# CLOSE SQLITE
# ============================================================

sqlite_conn.close()

print()
print("======================================")
print("Migration completed successfully!")
print("======================================")
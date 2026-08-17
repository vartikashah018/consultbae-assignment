import sqlite3
from pathlib import Path

DATABASE_PATH = Path("consultbae.db")
SCHEMA_PATH = Path("database/schema.sql")


def create_database():
    connection = sqlite3.connect(DATABASE_PATH)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema = file.read()

    connection.executescript(schema)
    connection.commit()
    connection.close()

    print(f"Database created: {DATABASE_PATH}")


if __name__ == "__main__":
    create_database()
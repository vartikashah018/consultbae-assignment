import json
import sqlite3
from pathlib import Path

import pandas as pd

from normalize import (
    normalize_name,
    normalize_email,
    normalize_phone,
    normalize_city,
    normalize_status,
    normalize_verified,
)
from matching import find_person_match


DATABASE_PATH = Path("consultbae.db")


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def load_people(connection):
    """
    Load existing master people into Python dictionaries.
    """

    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, canonical_name, email, phone, city
        FROM people
    """)

    rows = cursor.fetchall()

    people = []

    for row in rows:
        people.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "city": row[4],
        })

    return people


def create_person(connection, record):
    """
    Create a new person in the master people table.
    """

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO people
        (canonical_name, email, phone, city)
        VALUES (?, ?, ?, ?)
    """, (
        record["name"],
        record["email"],
        record["phone"],
        record["city"],
    ))

    connection.commit()

    return cursor.lastrowid


def create_source_record(
    connection,
    person_id,
    source_name,
    source_record_id,
    original_name,
    original_email,
    original_phone,
    raw_data,
    match_method,
    match_score,
):
    """
    Store the original source record and how it was matched.
    """

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO source_records (
            person_id,
            source_name,
            source_record_id,
            original_name,
            original_email,
            original_phone,
            raw_data,
            match_method,
            match_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        person_id,
        source_name,
        str(source_record_id),
        original_name,
        original_email,
        original_phone,
        json.dumps(raw_data),
        match_method,
        match_score,
    ))

    connection.commit()


def create_quality_issue(
    connection,
    source_name,
    source_record_id,
    issue_type,
    severity,
    description,
    action_taken,
):
    """
    Store a data quality issue.
    """

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO data_quality_issues (
            source_name,
            source_record_id,
            issue_type,
            severity,
            description,
            action_taken
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        source_name,
        str(source_record_id),
        issue_type,
        severity,
        description,
        action_taken,
    ))

    connection.commit()


def process_record(
    connection,
    people,
    record,
    source_name,
    source_record_id,
    original_name,
    original_email,
    original_phone,
):
    """
    Match a record against existing people.

    If a match is found, attach the source record to that person.
    Otherwise create a new person.
    """

    match, score, method = find_person_match(
        record,
        people
    )

    if match:
        person_id = match["id"]

        print(
            f"MATCH: {original_name} -> "
            f"{match['name']} "
            f"({method}, {score:.1f})"
        )

    else:
        person_id = create_person(
            connection,
            record
        )

        new_person = {
            "id": person_id,
            "name": record["name"],
            "email": record["email"],
            "phone": record["phone"],
            "city": record["city"],
        }

        people.append(new_person)

        method = "new_person"
        score = 0

        print(
            f"NEW: {original_name} -> "
            f"person {person_id}"
        )

    create_source_record(
        connection=connection,
        person_id=person_id,
        source_name=source_name,
        source_record_id=source_record_id,
        original_name=original_name,
        original_email=original_email,
        original_phone=original_phone,
        raw_data=record,
        match_method=method,
        match_score=score,
    )


def process_naukri(connection, people):
    print("\n" + "=" * 70)
    print("PROCESSING NAUKRI")
    print("=" * 70)

    df = pd.read_csv(
        "data/source1_naukri_applicants.csv"
    )

    for index, row in df.iterrows():

        record = {
            "name": normalize_name(row["Full Name"]),
            "email": normalize_email(row["Email"]),
            "phone": normalize_phone(row["Phone"]),
            "city": normalize_city(row["City"]),
        }

        process_record(
            connection,
            people,
            record,
            "naukri",
            index,
            row["Full Name"],
            row["Email"],
            row["Phone"],
        )


def process_gig_workers(connection, people):
    print("\n" + "=" * 70)
    print("PROCESSING GIG WORKERS")
    print("=" * 70)

    df = pd.read_csv(
        "data/source2_gig_workers.csv"
    )

    for index, row in df.iterrows():

        # Ignore completely empty rows.
        if row.isna().all():
            create_quality_issue(
                connection,
                "gig_workers",
                index,
                "empty_row",
                "low",
                "Entire row is empty.",
                "Skipped during ingestion.",
            )

            continue

        # Detect malformed Isha row.
        if (
            isinstance(row["email_id"], str)
            and not row["email_id"].strip().lower().find("@") >= 0
        ):
            create_quality_issue(
                connection,
                "gig_workers",
                index,
                "malformed_row",
                "high",
                "Email column contains skill tags and remaining fields are shifted.",
                "Reconstructed fields based on the row structure.",
            )

            # Repair the known malformed structure.
            skill_tags = row["email_id"]
            email = row["worker_name"]
            worker_name = row["rate"]
            rate = row["location"]
            location = row["status"]
            status = row["skill_tags"]

        else:
            email = row["email_id"]
            worker_name = row["worker_name"]
            rate = row["rate"]
            location = row["location"]
            status = row["status"]
            skill_tags = row["skill_tags"]

        record = {
            "name": normalize_name(worker_name),
            "email": normalize_email(email),
            "phone": "",
            "city": normalize_city(location),
        }

        process_record(
            connection,
            people,
            record,
            "gig_workers",
            index,
            worker_name,
            email,
            "",
        )


def process_cbnexus(connection, people):
    print("\n" + "=" * 70)
    print("PROCESSING CBNEXUS")
    print("=" * 70)

    df = pd.read_csv(
        "data/source3_cbnexus_contacts.csv"
    )

    for index, row in df.iterrows():

        # Detect embedded header row.
        if str(row["Phone Number"]).strip().lower() == "phone number":

            create_quality_issue(
                connection,
                "cbnexus",
                index,
                "embedded_header",
                "medium",
                "A header row appears inside the data.",
                "Skipped during ingestion.",
            )

            continue

        record = {
            "name": normalize_name(row["Name"]),
            "email": "",
            "phone": normalize_phone(row["Phone Number"]),
            "city": normalize_city(row["City"]),
        }

        process_record(
            connection,
            people,
            record,
            "cbnexus",
            index,
            row["Name"],
            "",
            row["Phone Number"],
        )


def main():
    connection = get_connection()

    people = load_people(connection)

    process_naukri(connection, people)
    process_gig_workers(connection, people)
    process_cbnexus(connection, people)

    connection.close()

    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
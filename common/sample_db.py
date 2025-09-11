"""
Utility to create a small sample database in Firestore (preferably the Firestore Emulator).

This script seeds the following collections:
- main_fields/students: default main fields configuration
- students: a couple of student documents with precomputed search helpers
- users: example users allowed to access the bot
- fields: example field metadata

Usage:
  # Ensure Firestore Emulator is running on 127.0.0.1:8080
  # Optionally export FIRESTORE_EMULATOR_HOST if different
  python -m common.sample_db

Environment variables:
- FIRESTORE_EMULATOR_HOST (recommended for local runs)
- PROJECT_ID (optional; defaults to 'jbcubbot')
"""
from __future__ import annotations

import os
from typing import Optional, List, Dict, Any

from google.cloud import firestore
from common.models import Student, Course, FieldDesc

DEFAULT_PROJECT = os.getenv("PROJECT_ID", "jbcubbot")
DEFAULT_EMULATOR = os.getenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")

def _mk_client() -> firestore.Client:
    # noinspection PyTypeChecker
    return firestore.Client(project=DEFAULT_PROJECT)


def create_sample_db(db: firestore.Client) -> None:
    fields_ref = db.collection("fields")

    student_fields = {
        "first_name": FieldDesc(name="first_name", type="primary", description="First name").model_dump(),
        "last_name": FieldDesc(name="last_name", type="primary", description="Last name").model_dump(),
        "admission_year": FieldDesc(name="admission_year", type="primary", description="Admission year").model_dump(),
        "scholarship": FieldDesc(name="scholarship", type="primary", description="Scholarship").model_dump(),
        "cub_email": FieldDesc(name="cub_email", type="contacts", description="CUB Email").model_dump(),
        "personal_email": FieldDesc(name="personal_email", type="contacts", description="Personal Email").model_dump(),
        "telegram": FieldDesc(name="telegram", type="contacts", description="Telegram").model_dump(),
        "citizenship": FieldDesc(name="citizenship", type="primary", description="Citizenship").model_dump(),
        "matric_number": FieldDesc(name="matric_number", type="primary", description="Matriculation Num.").model_dump(),

    }

    db.collection('fields').document('students').set(student_fields)

    # 3) Students (use stable IDs so reruns are idempotent)
    john = Student(
        first_name="John",
        last_name="Doe",
        cub_email="john53452345@constructor.universiti",
        personal_email="john@example.com",
        telegram_name="@john",
        telegram_id=123419872,
        admission_year=2023,
        scholarship="none",
        citizenship="USA",
        public_comment="Student representative",
        secret_comment="Top of class",
        matric_number="12345"
    )
    jane = Student(
        first_name="Jane",
        last_name="Smith",
        cub_email="jane@gmail.coom",
        personal_email="jane1231342@constructor.universiti",
        telegram_name="",
        telegram_id=1231231,
        admission_year=2022,
        scholarship="full",
        citizenship="UK",
        public_comment="Exchange semester",
        secret_comment="",
    )

    # Derive IDs aligned with import logic used in tests: prefer Matriculation Num., else name::email
    def _student_id(doc) -> str:
        return doc.matric_number

    db.collection("students").add(john.model_dump())
    db.collection("students").add(jane.model_dump())

    users = [
        {"tg": "xoposhiy", "role": "admin"},
    ]
    for u in users:
        db.collection("users").document(u["tg"]).set(u)


def delete_collection(coll_ref, batch_size=50):
    while True:
        docs = list(coll_ref.limit(batch_size).stream())
        if not docs:
            break
        for doc in docs:
            doc.reference.delete()
        print(f"Deleted batch of {len(docs)} docs")


def drop_db_collections(db: firestore.Client):
    delete_collection(db.collection('fields'))
    delete_collection(db.collection('students'))
    delete_collection(db.collection('users'))


def main():
    os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
    client = _mk_client()
    drop_db_collections(client)
    create_sample_db(client)
    print("Sample Firestore database has been created.")


if __name__ == "__main__":
    main()

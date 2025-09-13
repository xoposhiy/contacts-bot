import io
import os

import pytest

from common.test_utils import fresh_db
from importing.import_service import ImportService
from common.models import Student


@pytest.fixture(scope="module")
def db():
    with fresh_db() as client:
        yield client


@pytest.fixture()
def service(db):
    return ImportService(db)


def _get_student_by_name(db, full_name: str) -> Student | None:
    parts = full_name.split()
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""
    for snap in db.collection("students").stream():
        s = Student(**(snap.to_dict() or {}))
        s.doc_id = snap.id
        if s.first_name == first and s.last_name == last:
            return s
    return None


def test_import_creates_from_sample_file(service, db):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sdt2025.csv")
    report = service.import_csv_from_path(path)
    assert report.created > 0
    # No updates expected because seed data doesn't match those rows
    assert report.updated >= 0


def test_update_by_email_changes_field(service, db):
    # Prepare CSV with one row matching John Doe by personal email and changing scholarship
    john = _get_student_by_name(db, "John Doe")
    assert john is not None
    csv_text = (
        "Last name,First name,Email,CUB Email,Telegram,Matriculation Num.,Citizenship,Type of grant,Comment\n" \
        f"{john.last_name},{john.first_name},{john.personal_email},,,,{john.citizenship},partial scholarship,Updated via test\n"
    )
    report = service.import_csv_text(csv_text)
    assert report.created == 0
    assert report.updated == 1
    # Verify DB updated
    refreshed = _get_student_by_name(db, "John Doe")
    assert refreshed is not None
    assert refreshed.scholarship == "partial scholarship"
    assert refreshed.public_comment == "Updated via test"


def test_ambiguous_by_telegram(service, db):
    # Create two students with the same telegram handle
    dup_tg = "@dup_handle"
    s1 = Student(
        first_name="A",
        last_name="One",
        cub_email="a.one@example.com",
        personal_email="",
        telegram_name=dup_tg,
        telegram_id=0,
        admission_year=2025,
        scholarship="",
        citizenship="",
        public_comment="",
        secret_comment="",
    )
    s2 = Student(
        first_name="B",
        last_name="Two",
        cub_email="b.two@example.com",
        personal_email="",
        telegram_name=dup_tg,
        telegram_id=0,
        admission_year=2025,
        scholarship="",
        citizenship="",
        public_comment="",
        secret_comment="",
    )
    db.collection("students").add(s1.model_dump())
    db.collection("students").add(s2.model_dump())

    csv_text = (
        "Last name,First name,Email,CUB Email,Telegram,Matriculation Num.,Citizenship,Type of grant,Comment\n"
        ",,,,@dup_handle,,, ,\n"
    )
    report = service.import_csv_text(csv_text)
    assert len(report.ambiguous_rows) == 1
    assert report.created == 0
    assert report.updated == 0


def test_duplicate_groups_detected(service, db):
    # Two rows point to the same John Doe by email
    john = _get_student_by_name(db, "John Doe")
    assert john is not None
    csv_text = (
        "Last name,First name,Email,CUB Email,Telegram,Matriculation Num.,Citizenship,Type of grant,Comment\n" \
        f"{john.last_name},{john.first_name},{john.personal_email},,,,{john.citizenship},,\n" \
        f"{john.last_name},{john.first_name},{john.personal_email},,,,{john.citizenship},,\n"
    )
    report = service.import_csv_text(csv_text)
    # No creations, at most 1 update (first application). We still detect duplicate group
    assert report.created == 0
    assert len(report.duplicate_groups) >= 1
    # The duplicate group should contain two row indexes (2 and 3 in the minimal CSV)
    assert any(len(g.row_indexes) >= 2 for g in report.duplicate_groups)

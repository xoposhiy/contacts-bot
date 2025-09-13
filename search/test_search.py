import pytest

from common.test_utils import fresh_db
from search.search_service import SearchService


@pytest.fixture(scope="module")
def db():
    """Provide a Firestore emulator client with a fresh seeded sample DB for this test module."""
    with fresh_db() as client:
        yield client


@pytest.fixture()
def service(db):
    return SearchService(db)


def test_search_by_full_name_returns_single(service):
    res = service.search_students("John Doe")
    assert len(res) == 1
    s = res[0]
    assert s.full_name == "John Doe"
    assert s.doc_id is not None
    assert s.cub_email


def test_search_by_first_name_single_token(service):
    res = service.search_students("john")
    assert any(s.full_name == "John Doe" for s in res)


def test_search_by_last_name_single_token(service):
    res = service.search_students("Doe")
    assert any(s.full_name == "John Doe" for s in res)


def test_search_no_results(service):
    res = service.search_students("Nonexistent Name")
    assert res == []


def test_search_by_full_name_jane(service):
    res = service.search_students("Jane Smith")
    assert len(res) == 1
    assert res[0].full_name == "Jane Smith"

def test_search_by_wrong_order(service):
    res = service.search_students("Smith  Jane")
    assert len(res) == 1
    assert res[0].full_name == "Jane Smith"

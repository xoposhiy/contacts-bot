from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import pytest
from google.cloud import firestore

from common.sample_db import drop_db_collections, create_sample_db

GCLOUD_PROJECT = "jbcubbot"
DEFAULT_EMULATOR = os.getenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")


def get_emulator_client_or_skip() -> firestore.Client:
    """Return a Firestore client connected to the emulator or skip tests if unavailable.

    Ensures required environment variables are set. Performs a lightweight call
    to verify the emulator is reachable. If not, the caller's test will be skipped.
    """
    # Ensure emulator env is in place for google-cloud-firestore SDK
    os.environ.setdefault("FIRESTORE_EMULATOR_HOST", DEFAULT_EMULATOR)
    os.environ.setdefault("PROJECT_ID", GCLOUD_PROJECT)

    try:
        # noinspection PyTypeChecker
        client = firestore.Client(project=GCLOUD_PROJECT)
        # Validate connectivity (will raise if not connected to emulator)
        _ = list(client.collections())
        return client
    except Exception as e:
        pytest.skip(f"Firestore emulator not available or unreachable: {e}")
        # For type checkers
        raise


@contextmanager
def fresh_db() -> Iterator[firestore.Client]:
    """Yield a Firestore client with a fresh seeded sample DB.

    Drops known collections, seeds sample data before yielding, and cleans up after.
    Skips tests if the emulator is not available.
    """
    client = get_emulator_client_or_skip()
    drop_db_collections(client)
    create_sample_db(client)
    yield client

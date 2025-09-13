from __future__ import annotations

import logging
from typing import List

from google.cloud import firestore

from common.models import Student, normalize, tokenize_names, generate_ordered_pairs

logger = logging.getLogger(__name__)


class SearchService:
    """
    Encapsulates all DB access and search logic for students.

    Always returns Student models (converted immediately after Firestore load).
    """

    def __init__(self, db: firestore.Client):
        self.db = db

    def _from_snapshot(self, snap: firestore.DocumentSnapshot) -> Student:
        data = snap.to_dict() or {}
        # noinspection PyArgumentList
        stu = Student(**data)
        stu.doc_id = snap.id
        return stu

    def fetch_by_pair(self, pair: str) -> List[Student]:
        out: List[Student] = []
        try:
            q = self.db.collection("students").where("name_pairs", "array_contains", pair)
            for snap in q.stream():
                out.append(self._from_snapshot(snap))
        except Exception as e:
            logger.exception("Error querying by pair '%s': %s", pair, e)
        return out

    def fetch_all(self) -> List[Student]:
        out: List[Student] = []
        for snap in self.db.collection("students").stream():
            out.append(self._from_snapshot(snap))
        return out

    def search_students(self, query: str) -> List[Student]:
        q = normalize(query)
        tokens = tokenize_names(q)
        if not tokens:
            return []

        found: dict[str, Student] = {}

        if len(tokens) >= 2:
            # Try ordered pairs first for precise match
            for pair in generate_ordered_pairs(tokens):
                for s in self.fetch_by_pair(pair):
                    if s.doc_id:
                        found[s.doc_id] = s
            if found:
                return list(found.values())
            # Fall back to single-token filtering below

        # Single token or broad fallback: fetch all and filter client-side
        all_students = self.fetch_all()
        tok = tokens[0]
        for s in all_students:
            fn = normalize(s.first_name or "")
            ln = normalize(s.last_name or "")
            # Token match on first or last name
            if tok in tokenize_names(fn) or tok in tokenize_names(ln):
                if s.doc_id:
                    found[s.doc_id] = s
        return list(found.values())

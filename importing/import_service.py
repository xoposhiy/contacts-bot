from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from google.cloud import firestore

from common.models import Student, tokenize_names

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    student_id: str
    row_indexes: List[int] = field(default_factory=list)


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    ambiguous_rows: List[Tuple[int, str]] = field(default_factory=list)  # (row_index, reason)
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)

    def summarize(self) -> str:
        lines = [
            f"Created: {self.created}",
            f"Updated: {self.updated}",
            f"Ambiguous/Skipped rows: {len(self.ambiguous_rows)}",
            f"Duplicate groups: {len(self.duplicate_groups)}",
        ]
        if self.ambiguous_rows:
            lines.append("\nAmbiguous rows:")
            for idx, reason in self.ambiguous_rows:
                lines.append(f" - row {idx}: {reason}")
        if self.duplicate_groups:
            lines.append("\nDuplicate groups (row indexes -> student_id):")
            for g in self.duplicate_groups:
                lines.append(f" - {g.row_indexes} -> {g.student_id}")
        return "\n".join(lines)


class ImportService:
    """
    CSV import service.

    Matching rules order:
      1) Any email (CUB or personal)
      2) Telegram handle (exact match, case-insensitive, with or without @)
      3) Names: all tokens from row's first+last exist in student's first+last tokens

    Updates only counted if any field value actually changes. Blank CSV values are ignored (not used to overwrite).
    """

    def __init__(self, db: firestore.Client, default_admission_year: int = 2025):
        self.db = db
        self.default_admission_year = default_admission_year

    # ---------- Public API ----------
    def import_csv_from_path(self, path: str) -> ImportReport:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return self.import_csv_file(f)

    def import_csv_bytes(self, content: bytes) -> ImportReport:
        text = content.decode("utf-8-sig", errors="replace")
        return self.import_csv_text(text)

    def import_csv_text(self, text: str) -> ImportReport:
        buf = io.StringIO(text)
        return self.import_csv_file(buf)

    # ---------- Internals ----------
    def import_csv_file(self, f) -> ImportReport:
        reader = csv.DictReader(f)
        rows = [self._normalize_row(r) for r in reader]

        # Load all students once and prepare indices
        students, by_email, by_tg = self._load_students_index()

        report = ImportReport()
        matched_row_groups: Dict[str, List[int]] = {}

        for idx, row in enumerate(rows, start=2):  # start=2 to account for header line
            if self._is_empty_row(row):
                continue
            matches = self._match_students(row, by_email, by_tg, students)
            if len(matches) == 0:
                # Create new
                self._create_student(row)
                report.created += 1
            elif len(matches) > 1:
                # Ambiguous: skip
                reason = f"multiple matches by keys: {[s.doc_id for s in matches if s.doc_id]}"
                report.ambiguous_rows.append((idx, reason))
            else:
                s = matches[0]
                if not s.doc_id:
                    # shouldn't happen, but guard
                    reason = "matched student without doc_id"
                    report.ambiguous_rows.append((idx, reason))
                    continue
                changed = self._update_student_if_changed(s, row)
                if changed:
                    report.updated += 1
                # Track duplicates per student
                matched_row_groups.setdefault(s.doc_id, []).append(idx)

        # Build duplicate groups where a single student matched multiple rows
        for doc_id, idxs in matched_row_groups.items():
            if len(idxs) > 1:
                report.duplicate_groups.append(DuplicateGroup(student_id=doc_id, row_indexes=idxs))
        return report

    # ---------- Helpers ----------
    @staticmethod
    def _norm(s: Optional[str]) -> str:
        return (s or "").strip()

    @staticmethod
    def _norm_email(s: Optional[str]) -> str:
        return (s or "").strip().lower()

    @staticmethod
    def _norm_tg(s: Optional[str]) -> str:
        s = (s or "").strip()
        if not s or s.lower() in {"-", "none", "n/a", "na"}:
            return ""
        if not s.startswith("@"):
            s = "@" + s
        return s

    def _normalize_row(self, row: Dict[str, str]) -> Dict[str, str]:
        # Map known headers from sample CSV to our model fields
        # Input headers example: "Last name", "First name", "Email", "CUB Email", "Telegram", "Matriculation Num.", "Citizenship", "Type of grant", "Comment"
        return {
            "first_name": self._norm(row.get("First name")),
            "last_name": self._norm(row.get("Last name")),
            "personal_email": self._norm_email(row.get("Email")),
            "cub_email": self._norm_email(row.get("CUB Email")),
            "telegram_name": self._norm_tg(row.get("Telegram")),
            "matric_number": self._norm(row.get("Matriculation Num.")),
            "citizenship": self._norm(row.get("Citizenship")),
            "scholarship": self._norm(row.get("Type of grant")),
            "public_comment": self._norm(row.get("Comment")),
        }

    @staticmethod
    def _is_empty_row(row: Dict[str, str]) -> bool:
        return not any(v for v in row.values())

    def _load_students_index(self):
        students: List[Student] = []
        by_email: Dict[str, List[Student]] = {}
        by_tg: Dict[str, List[Student]] = {}
        for snap in self.db.collection("students").stream():
            data = snap.to_dict() or {}
            stu = Student(**data)
            stu.doc_id = snap.id
            students.append(stu)
            emails = {self._norm_email(stu.cub_email), self._norm_email(stu.personal_email)}
            for em in emails:
                if em:
                    by_email.setdefault(em, []).append(stu)
            tg = self._norm_tg(stu.telegram_name)
            if tg:
                by_tg.setdefault(tg.lower(), []).append(stu)
        return students, by_email, by_tg

    def _match_students(self, row: Dict[str, str], by_email, by_tg, students: List[Student]) -> List[Student]:
        # 1) By any email
        matches: Dict[str, Student] = {}
        for em in [row.get("cub_email"), row.get("personal_email")]:
            emn = self._norm_email(em)
            if emn and emn in by_email:
                for s in by_email[emn]:
                    if s.doc_id:
                        matches[s.doc_id] = s
        if matches:
            return list(matches.values())
        # 2) By telegram handle
        tg = self._norm_tg(row.get("telegram_name"))
        if tg:
            lst = by_tg.get(tg.lower()) or []
            for s in lst:
                if s.doc_id:
                    matches[s.doc_id] = s
            if matches:
                return list(matches.values())
        # 3) By names tokens subset
        row_tokens = set(tokenize_names(row.get("first_name", ""), row.get("last_name", "")))
        if row_tokens:
            for s in students:
                toks = set(tokenize_names(s.first_name, s.last_name))
                if row_tokens.issubset(toks):
                    if s.doc_id:
                        matches[s.doc_id] = s
        return list(matches.values())

    def _create_student(self, row: Dict[str, str]) -> str:
        data = self._merge_into_student_dict({}, row, creating=True)
        stu = Student(**data)
        doc = self.db.collection("students").add(stu.model_dump())[1]
        return doc.id

    def _update_student_if_changed(self, s: Student, row: Dict[str, str]) -> bool:
        current = s.model_dump()
        new_data = self._merge_into_student_dict(current, row, creating=False)
        # Recompute derived fields (like name_pairs) via model validation
        tmp_model = Student(**{k: v for k, v in new_data.items() if k != "doc_id"})
        new_data = tmp_model.model_dump()
        # Remove computed fields and Firestore-only info
        new_data.pop("doc_id", None)
        # Compare meaningful fields
        changed = any(current.get(k) != new_data.get(k) for k in new_data.keys())
        if changed and s.doc_id:
            self.db.collection("students").document(s.doc_id).set(new_data, merge=False)
        return changed

    def _merge_into_student_dict(self, base: Dict[str, object], row: Dict[str, str], creating: bool) -> Dict[str, object]:
        def pick(field: str) -> Optional[str]:
            v = row.get(field)
            return v if v not in (None, "") else None

        # Start from existing data if updating
        out: Dict[str, object] = dict(base) if not creating else {}

        def set_if_present(key: str, value: Optional[object]):
            if value is not None:
                out[key] = value

        set_if_present("first_name", pick("first_name") or (creating and "") or out.get("first_name", ""))
        set_if_present("last_name", pick("last_name") or (creating and "") or out.get("last_name", ""))
        set_if_present("cub_email", pick("cub_email") or out.get("cub_email", ""))
        set_if_present("personal_email", pick("personal_email") or out.get("personal_email", ""))
        set_if_present("telegram_name", pick("telegram_name") or out.get("telegram_name", ""))
        set_if_present("matric_number", pick("matric_number") or out.get("matric_number"))
        set_if_present("citizenship", pick("citizenship") or out.get("citizenship", ""))
        set_if_present("scholarship", pick("scholarship") or out.get("scholarship", ""))
        set_if_present("public_comment", pick("public_comment") or out.get("public_comment", ""))

        # Required fields fallbacks
        set_if_present("telegram_id", out.get("telegram_id", 0) or 0)
        set_if_present("admission_year", out.get("admission_year", self.default_admission_year) or self.default_admission_year)
        set_if_present("secret_comment", out.get("secret_comment", ""))
        set_if_present("name_pairs", out.get("name_pairs", []))
        set_if_present("citizenship", out.get("citizenship", out.get("country", "")))
        # Ensure name_pairs will be consistent when saved: re-instantiate Student later
        return out

from __future__ import annotations

from typing import Optional

from google.cloud import firestore


class AccessService:
    """
    Access control service for bot users.

    Rules (users collection):
    - Allowed if there exists a document with ID equal to user's Telegram username.
    - OR allowed if any document has field 'telegram_id' equal to user's Telegram user_id.
    """

    def __init__(self, db: firestore.Client):
        self.db = db

    async def is_authorized_user(self, username: Optional[str], user_id: Optional[int]) -> bool:
        users_ref = self.db.collection("users")
        if username:
            snap = users_ref.document(username).get()
            if snap.exists:
                return True
        if user_id is not None:
            q = users_ref.where("telegram_id", "==", user_id).limit(1).stream()
            if any(True for _ in q):
                return True
        return False
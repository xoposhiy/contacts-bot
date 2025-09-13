from __future__ import annotations

import io
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from common.access_service import AccessService
from importing.import_service import ImportService

logger = logging.getLogger(__name__)

router = Router(name="importing")


@router.message(Command("import_csv"))
async def import_csv_command(message: Message):
    await message.answer("Please send a CSV file as a document to import.")


@router.message(F.document)
async def handle_csv_document(message: Message, access_service: AccessService, import_service: ImportService):
    # Access control
    username = message.from_user.username if message.from_user else None
    user_id = message.from_user.id if message.from_user else None
    if not await access_service.is_authorized_user(username, user_id):
        await message.answer("Access denied. Please contact the administrator to request access.")
        return

    document = message.document
    if not document:
        await message.answer("No document found in the message.")
        return
    name = (document.file_name or "").lower()
    mime = (document.mime_type or "").lower()
    if not (name.endswith(".csv") or mime == "text/csv"):
        await message.answer("Unsupported file type. Please send a .csv file.")
        return

    # Download file bytes
    try:
        buf = io.BytesIO()
        await message.bot.download(document, destination=buf)
        report = import_service.import_csv_bytes(buf.getvalue())
        await message.answer("Import finished\n" + report.summarize())
    except Exception as e:
        logger.exception("Failed to import CSV: %s", e)
        await message.answer(f"Failed to import CSV: {e}")

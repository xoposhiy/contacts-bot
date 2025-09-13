from __future__ import annotations

import logging
from typing import List

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from common.models import Student
from search.search_service import SearchService
from common.access_service import AccessService

logger = logging.getLogger(__name__)

router = Router(name="search")


def _format_student_card(s: Student) -> str:
    name = s.full_name

    cub_email = s.cub_email
    personal_email = s.personal_email
    tg = s.telegram_name
    admission = s.admission_year
    scholarship = s.scholarship

    lines = [f"<b>{name}</b>"]
    contacts: List[str] = []
    if cub_email:
        contacts.append(f"CUB: <code>{cub_email}</code>")
    if personal_email:
        contacts.append(f"Personal: <code>{personal_email}</code>")
    if tg:
        contacts.append(f"Telegram: {tg}")
    if contacts:
        lines.append("\n".join(contacts))
    if admission is not None:
        lines.append(f"Admission year: <b>{admission}</b>")
    if scholarship:
        lines.append(f"Scholarship: <b>{scholarship}</b>")
    return "\n".join(lines)




def _card_keyboard(student_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Courses", callback_data=f"courses:{student_id}"),
            InlineKeyboardButton(text="Others", callback_data=f"others:{student_id}"),
        ]
    ])


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_search(message: Message, access_service: AccessService, search_service: SearchService):
    username = message.from_user.username if message.from_user else None
    user_id = message.from_user.id if message.from_user else None

    query = message.text or ""
    logger.info("Text query from user_id=%s username=%s: %r", user_id, username, query)

    if not await access_service.is_authorized_user(username, user_id):
        await message.answer("Access denied. Please contact the administrator to request access.")
        return

    service = search_service
    results = service.search_students(query)

    if not results:
        await message.answer("No matches found. Try first name, last name, or both.")
        return

    if len(results) == 1:
        s = results[0]
        await message.answer(
            _format_student_card(s),
            reply_markup=_card_keyboard(s.doc_id))
        return

    # Multiple candidates: send plain text list with code-formatted names (for easy copy)
    lines = [f"Found {len(results)} students:"]
    for s in results:
        if s.full_name:
            lines.append(f"- <code>{s.full_name}</code>")
    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("courses:"))
async def on_courses(cb: CallbackQuery):
    # Placeholder until Courses feature is implemented
    await cb.answer()
    await cb.message.answer("Courses view is not implemented yet.")


@router.callback_query(F.data.startswith("others:"))
async def on_others(cb: CallbackQuery):
    # Placeholder until Others feature is implemented
    await cb.answer()
    await cb.message.answer("Other details view is not implemented yet.")

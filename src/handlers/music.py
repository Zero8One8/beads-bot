"""
Музыкальная библиотека - исцеляющие частоты, мантры, медитации.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.database.db import db
from src.database.models import MusicModel

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "music")
async def music_list(callback: CallbackQuery):
    """Список музыкальных треков."""
    await callback.answer()
    tracks = MusicModel.get_all()

    if not tracks:
        await callback.message.edit_text(
            "🎵 *МУЗЫКАЛЬНАЯ БИБЛИОТЕКА*\n\n"
            "Раздел находится в наполнении.\n\n"
            "Скоро здесь появятся:\n"
            "• Частоты 432 Гц и 528 Гц\n"
            "• Тибетские поющие чаши\n"
            "• Мантры и медитации\n\n"
            "_Мастер добавляет аудио в этот раздел через админку_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← НАЗАД", callback_data="menu")]
            ])
        )
        return

    text = "🎵 *МУЗЫКАЛЬНАЯ БИБЛИОТЕКА*\n\n"
    text += "Исцеляющие частоты, мантры, медитации:\n\n"

    for track in tracks:
        text += f"🎶 *{track['name']}*\n"
        text += f"_{track['description']}_\n\n"

    buttons = []
    for track in tracks:
        if track.get('audio_url'):
            buttons.append([InlineKeyboardButton(
                text=f"▶️ {track['name']}",
                callback_data=f"music_{track['id']}"
            )])

    buttons.append([InlineKeyboardButton(text="← НАЗАД", callback_data="menu")])

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("music_"))
async def music_play(callback: CallbackQuery):
    """Воспроизведение трека."""
    await callback.answer()
    track_id = int(callback.data.replace("music_", ""))

    with db.cursor() as c:
        c.execute("SELECT * FROM music WHERE id = ?", (track_id,))
        track = c.fetchone()

    if not track:
        await callback.answer("❌ Трек не найден", show_alert=True)
        return

    if track.get('audio_url'):
        await callback.message.answer_audio(
            audio=track['audio_url'],
            caption=f"*{track['name']}*\n\n{track['description']}",
            parse_mode="Markdown"
        )
    else:
        await callback.answer("Аудио файл пока не добавлен", show_alert=True)

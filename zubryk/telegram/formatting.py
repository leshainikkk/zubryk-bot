import logging

from telebot import apihelper, types

log = logging.getLogger("zubryk.formatting")
_rich_available = True
_UNEDITABLE = (
    "message can't be edited", "message to edit not found",
    "there is no text in the message to edit",
)


def send_html(bot, chat_id, html, keyboard=None, *, message=None):
    options = dict(
        parse_mode="HTML", reply_markup=keyboard,
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )
    if message is not None:
        try:
            return bot.edit_message_text(
                html, chat_id=chat_id, message_id=message.message_id, **options,
            )
        except apihelper.ApiTelegramException as exc:
            description = exc.description.lower()
            if exc.error_code == 400 and "message is not modified" in description:
                return message
            if exc.error_code != 400 or not any(reason in description for reason in _UNEDITABLE):
                raise
    return bot.send_message(chat_id, html, **options)


def send_rich(bot, chat_id, rich_html, fallback_html, keyboard=None, *, message=None):
    global _rich_available
    if _rich_available and hasattr(bot, "send_rich_message") and hasattr(types, "InputRichMessage"):
        rich_message = types.InputRichMessage(html=rich_html, skip_entity_detection=True)
        try:
            if message is not None:
                return bot.edit_message_text(
                    chat_id=chat_id, message_id=message.message_id,
                    rich_message=rich_message, reply_markup=keyboard,
                )
            return bot.send_rich_message(chat_id, rich_message, reply_markup=keyboard)
        except apihelper.ApiTelegramException as exc:
            if exc.error_code not in (400, 404):
                raise
            if exc.error_code == 400 and "message is not modified" in exc.description.lower():
                return message
            log.warning("Rich Message unavailable; using readable HTML (API status %s)", exc.error_code)
            if exc.error_code == 404:
                _rich_available = False
    return send_html(bot, chat_id, fallback_html, keyboard, message=message)

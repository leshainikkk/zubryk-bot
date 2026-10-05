import logging
import threading
import time

import schedule
import telebot
from telebot import types

from config import BOT_TOKEN, ADMIN_ID
from old import database as db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bel_bot")

bot = telebot.TeleBot(BOT_TOKEN)

db.setup_database()

try:
    BOT_USERNAME = bot.get_me().username
except Exception:
    log.exception("Could not fetch bot username on startup (will retry lazily when needed)")
    BOT_USERNAME = None


def get_bot_username():
    global BOT_USERNAME
    if not BOT_USERNAME:
        try:
            BOT_USERNAME = bot.get_me().username
        except Exception:
            log.exception("Could not fetch bot username")
    return BOT_USERNAME


HELP_TEXT = (
    "ℹ️ *Как всё устроено*\n\n"
    "📚 *Учить новые слова* — выбери тему, слова показываются по одному, "
    "кнопка «Дальше» открывает следующее.\n"
    "📝 *Тест* — бот спрашивает перевод слов, которые ты уже изучил(а). "
    "Пока не изучишь ни одного слова, тест недоступен.\n"
    "🥔 *Бульба* — внутренняя валюта. Начисляется за игру с друзьями "
    "и участвует в рейтинге.\n"
    "🔥 *Стрик* — число дней подряд с занятиями. Пропустишь день целиком — "
    "серия начнётся заново с 1.\n"
    "🎮 *Играть с друзьями* — выбери тему, отправь другу ссылку-приглашение. "
    "Как только он перейдёт по ней — начнётся игра 1 на 1: на каждый раунд "
    "4 варианта перевода, кто ошибся первым — проиграл, а победитель получает "
    "дополнительно +30🥔.\n"
    "⚙️ *Настройки* — время ежедневных слов, имя, поддержка, удаление профиля.\n"
    "🏆 *Рейтинг* — топ игроков за неделю и за всё время."
)


# ─────────────────────────────────────────────────────────────────────────
# Клавиатуры и общие helper'ы отображения
# ─────────────────────────────────────────────────────────────────────────

def home_only_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def main_menu_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📚 Учить новые слова", callback_data="study"))
    kb.add(types.InlineKeyboardButton("📝 Тест по изученным словам", callback_data="test"))
    kb.add(types.InlineKeyboardButton("🎮 Играть с друзьями", callback_data="play"))
    kb.row(
        types.InlineKeyboardButton("🏆 Рейтинг", callback_data="rating"),
        types.InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        types.InlineKeyboardButton("❓ Помощь", callback_data="help"),
    )
    return kb


def main_menu_text(uid):
    user = db.get_or_create_user(uid)
    name = user["name"] or "Друг"
    return f"{name}   {user['balance']}🥔  {user['streak']}🔥"


def show_main_menu(chat_id):
    """Главное меню всегда отправляется НОВЫМ сообщением внизу чата, а не
    заменяет собой старое — чтобы вся история (изученные слова, прошлые
    экраны) оставалась видна и никуда не пропадала."""
    bot.send_message(chat_id, main_menu_text(chat_id), reply_markup=main_menu_kb())


def send_screen(chat_id, text, kb, parse_mode=None):
    """Отправляет экран (меню/вопрос/сообщение) ВСЕГДА новым сообщением —
    старые сообщения в чате не редактируются и не исчезают."""
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode=parse_mode)


def groups_kb(prefix):
    kb = types.InlineKeyboardMarkup()
    for g in db.get_groups():
        kb.add(types.InlineKeyboardButton(g["name"], callback_data=f"{prefix}:{g['key']}"))
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def daily_time_kb(back_to_settings=False):
    kb = types.InlineKeyboardMarkup()
    row = []
    for code, label in db.DAILY_TIME_CHOICES:
        row.append(types.InlineKeyboardButton(label, callback_data=f"settime:{code}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    if back_to_settings:
        kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="settings"))
    return kb


def settings_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("⏰ Изменение времени", callback_data="settings:time"))
    kb.add(types.InlineKeyboardButton("✏️ Изменить имя", callback_data="settings:name"))
    kb.add(types.InlineKeyboardButton("🆘 Поддержка", callback_data="settings:support"))
    kb.add(types.InlineKeyboardButton("🗑 Удалить профиль", callback_data="settings:delete"))
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def show_settings_menu(chat_id):
    bot.send_message(chat_id, "⚙️ Настройки", reply_markup=settings_kb())


def rating_menu_kb():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🔥 За неделю", callback_data="rating:week"),
        types.InlineKeyboardButton("🥔 За всё время", callback_data="rating:all"),
    )
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def format_rating(top, me):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    if not top:
        lines = ["Пока в рейтинге никого нет."]
    else:
        lines = []
        for uid_, name, amount, rank in top:
            prefix = medals.get(rank, f"{rank}.")
            lines.append(f"{prefix} {name or 'Без имени'} — {amount}🥔")
    if me and (not top or me[3] > top[-1][3]):
        lines.append("")
        lines.append(f"Ты: {me[3]} место — {me[2]}🥔")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────
# Регистрация / профиль
# ─────────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message):
    try:
        uid = message.from_user.id
        parts = (message.text or "").split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""

        if payload.startswith("g_"):
            handle_game_deeplink(message, payload[2:])
            return

        user = db.get_or_create_user(uid, message.from_user.first_name or "")
        if user["registered"]:
            # На всякий случай гарантированно убираем старую кастомную
            # клавиатуру (например, "следующее" из прошлой версии бота) —
            # Telegram хранит такую клавиатуру у пользователя, пока ей явно
            # не пришлют ReplyKeyboardRemove().
            bot.send_message(message.chat.id, "👋", reply_markup=types.ReplyKeyboardRemove())
            show_main_menu(message.chat.id)
            return

        msg = bot.send_message(
            message.chat.id,
            "Здравствуйте! Как вас зовут?",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        bot.register_next_step_handler(msg, save_name)
    except Exception:
        log.exception("cmd_start failed")


def save_name(message):
    try:
        uid = message.from_user.id
        name = (message.text or "").strip()[:64] or "Без имени"
        db.get_or_create_user(uid)
        db.set_name(uid, name)
        bot.send_message(
            message.chat.id,
            f"Приятно познакомиться, {name}! Когда присылать тебе слово дня?",
            reply_markup=daily_time_kb(),
        )
    except Exception:
        log.exception("save_name failed")


def save_new_name(message):
    try:
        uid = message.from_user.id
        name = (message.text or "").strip()[:64] or "Без имени"
        db.set_name(uid, name)
        bot.send_message(message.chat.id, f"Имя изменено на {name}.")
        show_settings_menu(message.chat.id)
    except Exception:
        log.exception("save_new_name failed")


# ─────────────────────────────────────────────────────────────────────────
# Учить новые слова
# ─────────────────────────────────────────────────────────────────────────

def render_study_word(uid, group_key):
    group = db.get_group(group_key)
    word = db.get_next_new_word(uid, group_key)
    if not word:
        group_name = group["name"] if group else group_key
        text = (
            f"🎉 В теме «{group_name}» пока закончились новые слова!\n\n"
            f"Выбери другую тему или вернись на главную."
        )
        return text, groups_kb("sg")

    word_id, bel, ru = word
    db.mark_word_learned(uid, word_id)
    text = f"📚 Новое слово:\n\n🇧🇾 {bel}\n🇷🇺 {ru}"
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("➡️ Дальше", callback_data=f"sg:{group_key}"),
        types.InlineKeyboardButton("🏠 Главная", callback_data="menu"),
    )
    return text, kb


# ─────────────────────────────────────────────────────────────────────────
# Тест по изученным словам
# ─────────────────────────────────────────────────────────────────────────

def start_test_flow(chat_id, uid):
    count = db.start_test(uid)
    if count == 0:
        bot.send_message(
            chat_id,
            "Ты пока не изучил ни одного слова. Сначала изучи новые слова.",
            reply_markup=home_only_kb(),
        )
        return
    ask_next_test_word(chat_id, uid)


def ask_next_test_word(chat_id, uid):
    word = db.get_next_test_word(uid)
    if not word:
        bot.send_message(chat_id, "Тест завершён! Отличная работа 🔥", reply_markup=home_only_kb())
        return
    word_id, bel, ru = word
    # Кнопка "Главная" позволяет выйти из теста в любой момент, не отвечая на
    # вопрос. Если её нажать, _safe_clear_step() отменит ожидание текстового
    # ответа для этого вопроса, чтобы следующее сообщение пользователя не
    # было случайно принято за ответ теста.
    msg = bot.send_message(chat_id, f"Как будет по-белорусски:\n🇷🇺 {ru}", reply_markup=home_only_kb())
    bot.register_next_step_handler(msg, check_test_answer, word_id, bel)


def check_test_answer(message, word_id, correct_bel):
    try:
        uid = message.from_user.id
        answer = (message.text or "").strip().lower()
        correct = answer == correct_bel.strip().lower()
        db.record_test_answer(uid, word_id, correct)
        if correct:
            bot.send_message(message.chat.id, f"✅ Правильно!\n{correct_bel}")
        else:
            bot.send_message(message.chat.id, f"❌ Неправильно.\nПравильный ответ: {correct_bel}")
        db.pop_test_word(uid)
        ask_next_test_word(message.chat.id, uid)
    except Exception:
        log.exception("check_test_answer failed")


@bot.message_handler(commands=["test"])
def cmd_test(message):
    try:
        uid = message.from_user.id
        db.get_or_create_user(uid, message.from_user.first_name or "")
        start_test_flow(message.chat.id, uid)
    except Exception:
        log.exception("cmd_test failed")


# ─────────────────────────────────────────────────────────────────────────
# Поддержка (/support, сохранено для совместимости)
# ─────────────────────────────────────────────────────────────────────────

def support_start(chat_id):
    msg = bot.send_message(chat_id, "Опишите вашу проблему. Я передам её разработчику.")
    bot.register_next_step_handler(msg, support_collect)


def support_collect(message):
    try:
        uid = message.from_user.id
        db.get_or_create_user(uid, message.from_user.first_name or "")
        text = message.text
        bot.send_message(
            ADMIN_ID,
            f"🆘 Новое сообщение в поддержку:\nОт пользователя: {uid}\nТекст:\n{text}",
        )
        bot.send_message(
            message.chat.id,
            "Ваше обращение отправлено. Спасибо! Я скоро посмотрю.",
            reply_markup=home_only_kb(),
        )
    except Exception:
        log.exception("support_collect failed")


@bot.message_handler(commands=["support"])
def cmd_support(message):
    try:
        support_start(message.chat.id)
    except Exception:
        log.exception("cmd_support failed")


# ─────────────────────────────────────────────────────────────────────────
# Игра 1×1 с друзьями
# ─────────────────────────────────────────────────────────────────────────

def game_groups_kb():
    kb = types.InlineKeyboardMarkup()
    for g in db.get_groups():
        kb.add(types.InlineKeyboardButton(g["name"], callback_data=f"pg:{g['key']}"))
    kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
    return kb


def send_round_to_player(target_uid, game_id, round_info):
    kb = types.InlineKeyboardMarkup()
    for opt_id, ru in round_info["options"]:
        kb.add(types.InlineKeyboardButton(ru, callback_data=f"ga:{game_id}:{round_info['round']}:{opt_id}"))
    text = f"Как переводится слово:\n«{round_info['word_bel']}»"
    try:
        bot.send_message(target_uid, text, reply_markup=kb)
    except Exception:
        log.exception("Failed to send round to player %s", target_uid)


def handle_game_deeplink(message, token):
    uid = message.from_user.id
    chat_id = message.chat.id
    db.get_or_create_user(uid, message.from_user.first_name or "Игрок")
    result = db.try_join_game(token, uid)
    res = result["result"]

    if res == "not_found":
        bot.send_message(chat_id, "Ссылка недействительна или игра уже закрыта.", reply_markup=home_only_kb())
        return
    if res == "not_waiting":
        bot.send_message(chat_id, "Эта игра уже идёт или завершена другими игроками.", reply_markup=home_only_kb())
        return
    if res == "full":
        bot.send_message(chat_id, "В этой игре уже два игрока.", reply_markup=home_only_kb())
        return
    if res == "already_in":
        game_id = result["game_id"]
        if result["status"] == "active":
            view = db.get_current_round_view(game_id)
            if view:
                bot.send_message(chat_id, "Ты уже в этой игре, вот текущий раунд:")
                send_round_to_player(uid, game_id, view)
                return
        bot.send_message(chat_id, "Ты уже в этой игре.", reply_markup=home_only_kb())
        return

    # res == "joined"
    game_id = result["game_id"]
    player1_id = result["player1_id"]
    bot.send_message(player1_id, "🎮 Игра началась! Второй игрок подключился.")
    bot.send_message(chat_id, "🎮 Игра началась!")

    round_info = db.start_round(game_id)
    if not round_info:
        fail_text = "Не удалось начать игру: в этой теме не нашлось слов."
        bot.send_message(player1_id, fail_text, reply_markup=home_only_kb())
        bot.send_message(chat_id, fail_text, reply_markup=home_only_kb())
        return

    send_round_to_player(player1_id, game_id, round_info)
    send_round_to_player(uid, game_id, round_info)


def handle_game_answer(call, uid, chat_id, data):
    _, gid_s, round_s, wordid_s = data.split(":")
    game_id, round_number, chosen_word_id = int(gid_s), int(round_s), int(wordid_s)
    result = db.submit_answer(game_id, uid, round_number, chosen_word_id)
    res = result["result"]

    if res in ("not_found", "not_player"):
        bot.answer_callback_query(call.id, "Эта игра тебе недоступна.", show_alert=True)
        return

    if res == "stale":
        bot.answer_callback_query(call.id, "Этот раунд уже неактуален.", show_alert=True)
        return

    if res == "duplicate":
        bot.answer_callback_query(call.id, "Ты уже отвечал(а) в этом раунде.", show_alert=True)
        return

    # любой другой исход — снимаем клавиатуру с этого сообщения, чтобы
    # нельзя было нажать дважды
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    if res == "wrong":
        bot.answer_callback_query(call.id, "❌ Неправильно! Игра окончена.")
        loser_id = result["loser_id"]
        winner_id = result.get("winner_id")
        bot.send_message(loser_id, "❌ Неправильный ответ. Ты проиграл(а) эту игру.", reply_markup=home_only_kb())
        if winner_id:
            bot.send_message(
                winner_id,
                "🏆 Соперник ошибся! Ты победил(а) в игре и получаешь дополнительно +30🥔!",
                reply_markup=home_only_kb(),
            )
        return

    if res == "correct_wait":
        bot.answer_callback_query(call.id, "✅ Правильно! +1🥔. Ждём ответа соперника…")
        return

    if res == "advance":
        bot.answer_callback_query(call.id, "✅ Правильно! +1🥔")
        next_round = result.get("next_round")
        if next_round:
            game = db.get_game(game_id)
            if game and game["player1_id"] and game["player2_id"]:
                send_round_to_player(game["player1_id"], game_id, next_round)
                send_round_to_player(game["player2_id"], game_id, next_round)
        return


# ─────────────────────────────────────────────────────────────────────────
# Единый обработчик inline-кнопок
# ─────────────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    uid = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data or ""

    try:
        _dispatch_callback(call, uid, chat_id, data)
    except Exception:
        log.exception("Callback dispatch failed for data=%s", data)
        try:
            bot.answer_callback_query(call.id, "Произошла ошибка, попробуй ещё раз.", show_alert=True)
        except Exception:
            pass


def _safe_clear_step(chat_id):
    """Отменяет ранее зарегистрированный register_next_step_handler для этого
    чата (например, бот ждал ответ теста или новое имя текстом). Вызывается
    при любом нажатии inline-кнопки, чтобы пользователь мог в любой момент
    уйти в другое меню, а следующее обычное сообщение не было по ошибке
    воспринято как "ответ" на давно неактуальный вопрос."""
    try:
        bot.clear_step_handler_by_chat_id(chat_id)
    except Exception:
        pass


def _dispatch_callback(call, uid, chat_id, data):
    db.get_or_create_user(uid)
    _safe_clear_step(chat_id)

    if data == "menu":
        bot.answer_callback_query(call.id)
        show_main_menu(chat_id)
        return

    if data == "study":
        bot.answer_callback_query(call.id)
        groups = db.get_groups()
        if not groups:
            send_screen(chat_id, "Пока нет доступных тем для изучения.", home_only_kb())
        else:
            send_screen(chat_id, "Выбери тему для изучения:", groups_kb("sg"))
        return

    if data.startswith("sg:"):
        bot.answer_callback_query(call.id)
        group_key = data.split(":", 1)[1]
        text, kb = render_study_word(uid, group_key)
        send_screen(chat_id, text, kb)
        return

    if data == "test":
        bot.answer_callback_query(call.id)
        start_test_flow(chat_id, uid)
        return

    if data == "play":
        bot.answer_callback_query(call.id)
        groups = db.get_groups()
        if not groups:
            send_screen(chat_id, "Пока нет доступных тем для игры.", home_only_kb())
        else:
            send_screen(chat_id, "Выбери тему для игры с другом:", game_groups_kb())
        return

    if data.startswith("pg:"):
        group_key = data.split(":", 1)[1]
        if db.get_group_word_count(group_key) < 4:
            bot.answer_callback_query(call.id, "В этой теме пока маловато слов для игры 🙁", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        game_id, token = db.create_game(uid, group_key)
        username = get_bot_username()
        if username:
            link = f"https://t.me/{username}?start=g_{token}"
            text = (
                "Комната создана! Отправь эту ссылку другу:\n"
                f"{link}\n\n"
                "Как только он перейдёт по ней — игра начнётся."
            )
        else:
            text = (
                "Комната создана, но не удалось получить имя бота для ссылки. "
                "Попробуй ещё раз чуть позже."
            )
        send_screen(chat_id, text, home_only_kb())
        return

    if data.startswith("ga:"):
        handle_game_answer(call, uid, chat_id, data)
        return

    if data == "rating":
        bot.answer_callback_query(call.id)
        send_screen(chat_id, "🏆 Рейтинг", rating_menu_kb())
        return

    if data == "rating:week":
        bot.answer_callback_query(call.id)
        top, me = db.get_rating_weekly(uid)
        text = "🔥 Рейтинг за неделю:\n\n" + format_rating(top, me)
        send_screen(chat_id, text, rating_menu_kb())
        return

    if data == "rating:all":
        bot.answer_callback_query(call.id)
        top, me = db.get_rating_alltime(uid)
        text = "🥔 Рейтинг за всё время:\n\n" + format_rating(top, me)
        send_screen(chat_id, text, rating_menu_kb())
        return

    if data == "settings":
        bot.answer_callback_query(call.id)
        send_screen(chat_id, "⚙️ Настройки", settings_kb())
        return

    if data == "settings:time":
        bot.answer_callback_query(call.id)
        send_screen(chat_id, "Выбери время ежедневных слов:", daily_time_kb(back_to_settings=True))
        return

    if data == "settings:name":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "Введи новое имя:")
        bot.register_next_step_handler(msg, save_new_name)
        return

    if data == "settings:support":
        bot.answer_callback_query(call.id)
        support_start(chat_id)
        return

    if data == "settings:delete":
        bot.answer_callback_query(call.id)
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("Да, удалить", callback_data="delete:yes"),
            types.InlineKeyboardButton("Отмена", callback_data="delete:no"),
        )
        send_screen(
            chat_id,
            "⚠️ Вы действительно хотите удалить профиль?\n"
            "Прогресс, баланс Бульбы и streak будут удалены безвозвратно.",
            kb,
        )
        return

    if data == "delete:yes":
        db.delete_user(uid)
        bot.answer_callback_query(call.id, "Профиль удалён.")
        bot.send_message(chat_id, "Профиль удалён. Напиши /start, чтобы начать заново.")
        return

    if data == "delete:no":
        bot.answer_callback_query(call.id)
        send_screen(chat_id, "⚙️ Настройки", settings_kb())
        return

    if data.startswith("settime:"):
        code = data.split(":", 1)[1]
        db.set_daily_time(uid, code)
        label = db.daily_time_label(None if code == "off" else code)
        bot.answer_callback_query(call.id, f"Сохранено: {label}")
        # reply_markup=ReplyKeyboardRemove() отправляется гарантированно (не
        # внутри except), чтобы окончательно убрать старую кастомную
        # клавиатуру прошлой версии бота ("следующее" и т.п.), если она у
        # пользователя ещё осталась.
        bot.send_message(
            chat_id,
            f"Готово! Ежедневные слова: {label}.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        show_main_menu(chat_id)
        return

    if data == "help":
        bot.answer_callback_query(call.id)
        send_screen(chat_id, HELP_TEXT, home_only_kb(), parse_mode="Markdown")
        return

    # неизвестный callback — просто закрываем "часики", ничего не меняем
    bot.answer_callback_query(call.id)


# ─────────────────────────────────────────────────────────────────────────
# Ежедневная рассылка (у каждого пользователя своё время)
# ─────────────────────────────────────────────────────────────────────────

def send_daily_words_for_time(code):
    for uid in db.get_users_due_for_daily(code):
        try:
            words = db.get_next_new_words_multi(uid, limit=5)
            if not words:
                bot.send_message(
                    uid,
                    "🏁 Ты уже изучил(а) все слова во всех темах! Загляни в «Играть с друзьями» 🎮",
                )
                db.mark_daily_sent(uid)
                continue

            lines = []
            for word_id, bel, ru in words:
                db.mark_word_learned(uid, word_id)
                lines.append(f"🇧🇾 {bel}\n🇷🇺 {ru}")

            bot.send_message(uid, "📚 Твои сегодняшние слова:\n\n" + "\n\n".join(lines))
            db.mark_daily_sent(uid)
        except Exception:
            log.exception("Failed to send daily words to user %s", uid)


def loop():
    for code, _label in db.DAILY_TIME_CHOICES:
        if code == "off":
            continue
        hhmm = f"{code[:2]}:{code[2:]}"
        schedule.every().day.at(hhmm).do(send_daily_words_for_time, code)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    bot.polling(none_stop=True, timeout=60)

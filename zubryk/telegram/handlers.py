from html import escape
from . import cards
from .logging import setup_logging
from .answers import normalize_answer
import logging
import threading
from telebot import types
from zubryk import storage as db
from zubryk.config import ADMIN_ID
from .client import bot
from .keyboards import *
from .presentation import *
from .scheduler import loop

log = logging.getLogger("zubryk.bot")
BOT_USERNAME = None

def get_bot_username():
    global BOT_USERNAME
    if not BOT_USERNAME:
        try:
            BOT_USERNAME = bot.get_me().username
        except Exception:
            log.exception("Could not fetch bot username")
    return BOT_USERNAME


@bot.message_handler(commands=["start"], chat_types=["private"])
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
            if payload.startswith("study_"):
                key=payload[6:]
                if db.get_group(key):
                    show_study_word(message.chat.id, uid, key)
                    return
            if payload=="support":
                support_start(message.chat.id)
                return
            if payload=="settings":
                show_settings_menu(message.chat.id)
                return
            if payload=="play":
                send_screen(message.chat.id, cards.topics_text(for_game=True), game_groups_kb())
                return
            show_main_menu(message.chat.id)
            return

        msg = send_screen(
            message.chat.id,
            "🌿 <b>Прывітанне! Я Зубрык.</b>\n\n"
            "Помогу учить беларускую по несколько слов в день. "
            "Здесь можно повторять слова и играть с друзьями.\n\n"
            "<b>Как тебя зовут?</b> Напиши своё имя.",
            types.ReplyKeyboardRemove(),
        )
        bot.register_next_step_handler(msg, save_name)
    except Exception:
        log.exception("cmd_start failed")


def save_name(message):
    try:
        if _route_pending_command(message):
            return
        uid = message.from_user.id
        name = (message.text or "").strip()[:64] or "Без имени"
        db.get_or_create_user(uid)
        db.set_name(uid, name)
        send_screen(
            message.chat.id,
            f"Прыемна пазнаёміцца, <b>{escape(name)}</b>!\n\n" + cards.time_text(onboarding=True),
            daily_time_kb(),
        )
    except Exception:
        log.exception("save_name failed")


def save_new_name(message):
    try:
        if _route_pending_command(message):
            return
        uid = message.from_user.id
        name = (message.text or "").strip()[:64] or "Без имени"
        db.set_name(uid, name)
        show_settings_menu(message.chat.id, notice=f"Имя сохранено: {name}")
    except Exception:
        log.exception("save_new_name failed")


def render_study_word(uid, group_key):
    group = db.get_group(group_key)
    if not group:
        return "📚 <b>Тема недоступна</b>\n\nВыбери другую тему для изучения.", groups_kb("sg"), None
    word = db.get_next_new_word(uid, group_key)
    if not word:
        group_name = escape(group["name"])
        text = (
            f"🎉 <b>Тема пройдена!</b>\n<i>{group_name}</i>\n\n"
            "Все её слова уже знакомы. Выбери новую тему или проверь себя в тесте."
        )
        return text, groups_kb("sg"), None

    word_id, bel, ru = word
    return cards.study_word_text(bel, ru, group["name"]), study_word_kb(group_key), word_id


def show_study_word(chat_id, uid, group_key):
    text, kb, word_id = render_study_word(uid, group_key)
    msg = send_screen(chat_id, text, kb)
    if word_id is not None:
        db.mark_word_learned(uid, word_id)
    return msg


def start_test_flow(chat_id, uid, *, message=None):
    _safe_clear_step(chat_id)
    count = db.start_test(uid)
    if count == 0:
        send_screen(
            chat_id,
            "📝 <b>Начнём с новых слов</b>\n\n"
            "Тест проверяет то, что ты уже изучил. "
            "Открой несколько слов — и возвращайся сюда.",
            test_result_kb(), message=message,
        )
        return
    ask_next_test_word(chat_id, uid, total=count, message=message)


def ask_next_test_word(chat_id, uid, *, total=0, completed=0, correct_count=0, feedback=None, message=None):
    word = db.get_next_test_word(uid)
    if not word:
        send_screen(chat_id, cards.test_result_text(correct_count, completed, feedback), test_result_kb(), message=message)
        return
    word_id, bel, ru = word
    msg = send_screen(chat_id, cards.test_question_text(ru, completed + 1, total, feedback), home_only_kb(), message=message)
    bot.register_next_step_handler(msg, check_test_answer, word_id, bel, total, completed, correct_count)


def check_test_answer(message, word_id, correct_bel, total=0, completed=0, correct_count=0):
    try:
        if _route_pending_command(message):
            return
        uid = message.from_user.id
        if not message.text:
            msg = send_screen(message.chat.id, "✍️ Напиши перевод <b>текстовым сообщением</b>.", home_only_kb())
            bot.register_next_step_handler(msg, check_test_answer, word_id, correct_bel, total, completed, correct_count)
            return
        answer = normalize_answer(message.text or "")
        correct = answer == normalize_answer(correct_bel)
        db.record_test_answer(uid, word_id, correct)
        db.pop_test_word(uid)
        ask_next_test_word(
            message.chat.id, uid, total=total, completed=completed + 1,
            correct_count=correct_count + int(correct),
            feedback=cards.test_feedback_text(correct, correct_bel),
        )
    except Exception:
        log.exception("check_test_answer failed")


@bot.message_handler(commands=["test"], chat_types=["private"])
def cmd_test(message):
    try:
        uid = message.from_user.id
        db.get_or_create_user(uid, message.from_user.first_name or "")
        start_test_flow(message.chat.id, uid)
    except Exception:
        log.exception("cmd_test failed")


def support_start(chat_id):
    if not ADMIN_ID:
        send_screen(chat_id, "💬 <b>Поддержка</b>\n\nПоддержка пока не подключена. Продолжить обучение можно через главное меню.", home_only_kb())
        return
    msg = send_screen(chat_id, "💬 <b>Напиши разработчику</b>\n\nОпиши проблему одним сообщением. Я передам твоё обращение.", home_only_kb())
    bot.register_next_step_handler(msg, support_collect)


def support_collect(message):
    try:
        if _route_pending_command(message):
            return
        uid = message.from_user.id
        db.get_or_create_user(uid, message.from_user.first_name or "")
        text = message.text
        bot.send_message(
            ADMIN_ID,
            f"🆘 Новое сообщение в поддержку:\nОт пользователя: {uid}\nТекст:\n{text}",
        )
        send_screen(
            message.chat.id,
            "✅ <b>Обращение отправлено</b>\n\nСпасибо! Разработчик получит твоё сообщение.",
            home_only_kb(),
        )
    except Exception:
        log.exception("support_collect failed")


@bot.message_handler(commands=["support"], chat_types=["private"])
def cmd_support(message):
    try:
        support_start(message.chat.id)
    except Exception:
        log.exception("cmd_support failed")


def send_round_to_player(target_uid, game_id, round_info):
    kb = types.InlineKeyboardMarkup()
    for opt_id, ru in round_info["options"]:
        kb.add(types.InlineKeyboardButton(ru, callback_data=f"ga:{game_id}:{round_info['round']}:{opt_id}"))
    text = cards.game_round_text(round_info['word_bel'], round_info['round'])
    try:
        send_screen(target_uid, text, kb)
    except Exception:
        log.exception("Failed to send round to player %s", target_uid)


def handle_game_deeplink(message, token):
    uid = message.from_user.id
    chat_id = message.chat.id
    db.get_or_create_user(uid, message.from_user.first_name or "Игрок")
    result = db.try_join_game(token, uid)
    res = result["result"]

    if res == "not_found":
        send_screen(chat_id, "🎮 <b>Приглашение устарело</b>\n\nЭта игра уже закрыта или ссылка недействительна. Создай новую дуэль.", home_only_kb())
        return
    if res == "not_waiting":
        send_screen(chat_id, "🎮 <b>Дуэль уже началась</b>\n\nЭта игра идёт или уже завершена. Можно создать новую.", home_only_kb())
        return
    if res == "full":
        send_screen(chat_id, "🎮 <b>Комната заполнена</b>\n\nВ этой игре уже два игрока. Создай свою дуэль.", home_only_kb())
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

    game_id = result["game_id"]
    player1_id = result["player1_id"]
    send_screen(player1_id, "🎮 <b>Соперник подключился!</b>\n\nДуэль начинается. Удачи обоим!")
    send_screen(chat_id, "🎮 <b>Ты в игре!</b>\n\nДуэль начинается. Удачи обоим!")

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

    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    if res == "wrong":
        bot.answer_callback_query(call.id, "❌ Неправильно! Игра окончена.")
        loser_id = result["loser_id"]
        winner_id = result.get("winner_id")
        send_screen(loser_id, "🏁 <b>Дуэль завершена</b>\n\nВ этот раз победил соперник. Ещё одна игра — ещё одна возможность потренироваться.", home_only_kb())
        if winner_id:
            send_screen(
                winner_id,
                "🏆 <b>Перамога!</b>\n\nСоперник ошибся — эта дуэль твоя.\n\n"
                "<blockquote>Бонус за победу: <b>+30 🥔</b></blockquote>",
                home_only_kb(),
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


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if not call.message or call.message.chat.type != "private":
        bot.answer_callback_query(call.id,"Откройте бота в личном чате")
        return
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
    try:
        bot.clear_step_handler_by_chat_id(chat_id)
    except Exception:
        pass


def _retire_keyboard(message):
    try:
        bot.edit_message_reply_markup(message.chat.id, message.message_id, reply_markup=None)
    except Exception:
        log.debug("Could not remove keyboard from a previous card", exc_info=True)


def _route_pending_command(message):
    text = (message.text or "").strip()
    if not text.startswith("/"):
        return False
    command = text.split()[0].split("@", 1)[0]
    handler = {"/start": cmd_start, "/test": cmd_test, "/help": cmd_help, "/app": cmd_app, "/support": cmd_support}.get(command)
    if handler:
        _safe_clear_step(message.chat.id)
        handler(message)
    else:
        show_main_menu(message.chat.id)
    return True


def _dispatch_callback(call, uid, chat_id, data):
    if data == "noop":
        bot.answer_callback_query(call.id)
        return

    if data.startswith("groups:"):
        _,prefix,page=data.split(":")
        if prefix not in ("sg","pg"):
            bot.answer_callback_query(call.id)
            return
        bot.answer_callback_query(call.id)
        send_screen(chat_id, cards.topics_text(for_game=prefix == "pg"), groups_kb(prefix, int(page)), message=call.message)
        return

    user = db.get_or_create_user(uid)
    _safe_clear_step(chat_id)

    if data == "menu":
        bot.answer_callback_query(call.id)
        show_main_menu(chat_id, message=call.message)
        return

    if data == "study":
        bot.answer_callback_query(call.id)
        groups = db.get_groups()
        if not groups:
            send_screen(chat_id, "📚 <b>Темы скоро появятся</b>\n\nПока нет доступных тем для изучения.", home_only_kb(), message=call.message)
        else:
            send_screen(chat_id, cards.topics_text(), groups_kb("sg"), message=call.message)
        return

    if data.startswith("sg:"):
        bot.answer_callback_query(call.id)
        group_key = data.split(":", 1)[1]
        show_study_word(chat_id, uid, group_key)
        _retire_keyboard(call.message)
        return

    if data == "test":
        bot.answer_callback_query(call.id)
        start_test_flow(chat_id, uid, message=call.message)
        return

    if data == "play":
        bot.answer_callback_query(call.id)
        groups = db.get_groups()
        if not groups:
            send_screen(chat_id, "🎮 <b>Темы скоро появятся</b>\n\nПока нет доступных тем для игры.", home_only_kb(), message=call.message)
        else:
            send_screen(chat_id, cards.topics_text(for_game=True), game_groups_kb(), message=call.message)
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
            group = db.get_group(group_key)
            text = cards.invitation_text(group["name"] if group else group_key, link)
            kb = invitation_kb(link)
        else:
            text = (
                "🎮 <b>Не удалось подготовить приглашение</b>\n\n"
                "Попробуй ещё раз чуть позже."
            )
            kb = home_only_kb()
        send_screen(chat_id, text, kb, message=call.message)
        return

    if data.startswith("ga:"):
        handle_game_answer(call, uid, chat_id, data)
        return

    if data in ("rating", "rating:week", "rating:all"):
        bot.answer_callback_query(call.id)
        weekly = data != "rating:all"
        top, me = db.get_rating_weekly(uid) if weekly else db.get_rating_alltime(uid)
        title = "За неделю" if weekly else "За всё время"
        text = f"🏆 <b>Рейтинг</b>\n<i>{title}</i>\n\n" + format_rating(top, me)
        send_screen(chat_id, text, rating_menu_kb("week" if weekly else "all"), message=call.message)
        return

    if data == "settings":
        bot.answer_callback_query(call.id)
        show_settings_menu(chat_id, message=call.message)
        return

    if data == "settings:time":
        bot.answer_callback_query(call.id)
        send_screen(chat_id, cards.time_text(), daily_time_kb(back_to_settings=True, selected=user["daily_time"]), message=call.message)
        return

    if data == "settings:name":
        bot.answer_callback_query(call.id)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("‹ Настройки", callback_data="settings"))
        msg = send_screen(chat_id, "✏️ <b>Как тебя называть?</b>\n\nНапиши новое имя одним сообщением.", kb, message=call.message)
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
            types.InlineKeyboardButton("Да, удалить", callback_data="delete:yes", style="danger"),
            types.InlineKeyboardButton("Отмена", callback_data="delete:no"),
        )
        send_screen(
            chat_id,
            "🗑 <b>Удалить профиль?</b>\n\n"
            "Прогресс, баланс бульбы и серия дней будут удалены. Восстановить их не получится.",
            kb, message=call.message,
        )
        return

    if data == "delete:yes":
        db.delete_user(uid)
        bot.answer_callback_query(call.id, "Профиль удалён.")
        send_screen(chat_id, "🗑 <b>Профиль удалён</b>\n\nНапиши /start, чтобы начать заново.", message=call.message)
        return

    if data == "delete:no":
        bot.answer_callback_query(call.id)
        show_settings_menu(chat_id, message=call.message)
        return

    if data.startswith("settime:"):
        code = data.split(":", 1)[1]
        db.set_daily_time(uid, code)
        label = db.daily_time_label(None if code == "off" else code)
        bot.answer_callback_query(call.id, f"Сохранено: {label}")

        if user["registered"]:
            show_settings_menu(chat_id, message=call.message, notice="Рассылка отключена" if code == "off" else f"Слова дня: {label}")
        else:
            show_main_menu(chat_id, message=call.message)
        return

    if data == "help":
        bot.answer_callback_query(call.id)
        show_help(chat_id, message=call.message)
        return

    bot.answer_callback_query(call.id)

@bot.message_handler(commands=["app"],chat_types=["private"])
def cmd_app(message):
    from zubryk.config import get_mini_app_url
    url=get_mini_app_url()
    kb=types.InlineKeyboardMarkup()
    if url:
        kb.add(types.InlineKeyboardButton("🌿 Открыть приложение",web_app=types.WebAppInfo(url),style="primary"))
        kb.add(types.InlineKeyboardButton("🏠 Главная", callback_data="menu"))
        send_screen(message.chat.id, "🌿 <b>Зубрык всегда под рукой</b>\n\nТвой прогресс, грамматика и подготовка к ЦТ / ЦЭ — в приложении.", kb)
    else:
        show_main_menu(message.chat.id)


@bot.message_handler(commands=["help"],chat_types=["private"])
def cmd_help(message):
    show_help(message.chat.id)


def run():
    setup_logging()
    from .runtime import acquire_polling_lock
    polling_lock=acquire_polling_lock()
    db.setup_database()
    threading.Thread(target=loop, daemon=True).start()
    import importlib.metadata
    log.info("Bot polling started (pyTelegramBotAPI %s)",importlib.metadata.version("pyTelegramBotAPI"))
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=False)
    finally:
        polling_lock.close()

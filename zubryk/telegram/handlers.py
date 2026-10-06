from html import escape
from .formatting import send_rich
from .logging import setup_logging
from .answers import normalize_answer
from zubryk.sources import word_source
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
                    text,kb=render_study_word(uid,key)
                    send_screen(message.chat.id,text,kb,parse_mode="HTML")
                    return
            if payload=="support":
                support_start(message.chat.id)
                return
            if payload=="settings":
                show_settings_menu(message.chat.id)
                return
            if payload=="play":
                send_screen(message.chat.id,"Выберите тему игры:",game_groups_kb())
                return
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
    text = f"<b>{escape(bel)}</b>\n{escape(ru)}\n\n<i>{escape(group['name']) if group else 'Новое слово'}</i>"
    source=word_source(bel)
    if source:
        text += f'\n\n<a href="{escape(source["url"],quote=True)}">Викисловарь</a> · <a href="{source["licenseUrl"]}">CC BY-SA 4.0</a>'
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("➡️ Дальше", callback_data=f"sg:{group_key}"),
        types.InlineKeyboardButton("🏠 Главная", callback_data="menu"),
    )
    return text, kb


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
    msg = bot.send_message(chat_id, f"<b>Как будет по-белорусски?</b>\n\n{escape(ru)}", parse_mode="HTML", reply_markup=home_only_kb())
    bot.register_next_step_handler(msg, check_test_answer, word_id, bel)


def check_test_answer(message, word_id, correct_bel):
    try:
        uid = message.from_user.id
        answer = normalize_answer(message.text or "")
        correct = answer == normalize_answer(correct_bel)
        db.record_test_answer(uid, word_id, correct)
        if correct:
            bot.send_message(message.chat.id, f"<b>Правильно!</b>\n{escape(correct_bel)}", parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, f"<b>Есть ошибка.</b>\nПравильный ответ: {escape(correct_bel)}", parse_mode="HTML")
        db.pop_test_word(uid)
        ask_next_test_word(message.chat.id, uid)
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
        bot.send_message(chat_id,"Поддержка пока не подключена. Продолжить обучение можно через главное меню.",reply_markup=home_only_kb())
        return
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


def _dispatch_callback(call, uid, chat_id, data):
    db.get_or_create_user(uid)
    _safe_clear_step(chat_id)

    if data.startswith("groups:"):
        _,prefix,page=data.split(":")
        if prefix not in ("sg","pg"):
            bot.answer_callback_query(call.id)
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_reply_markup(chat_id,call.message.message_id,reply_markup=groups_kb(prefix,int(page)))
        return

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
        send_screen(chat_id, text, kb, parse_mode="HTML")
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
        send_screen(chat_id, text, rating_menu_kb(), parse_mode="HTML")
        return

    if data == "rating:all":
        bot.answer_callback_query(call.id)
        top, me = db.get_rating_alltime(uid)
        text = "🥔 Рейтинг за всё время:\n\n" + format_rating(top, me)
        send_screen(chat_id, text, rating_menu_kb(), parse_mode="HTML")
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
            types.InlineKeyboardButton("Да, удалить", callback_data="delete:yes", style="danger"),
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

        bot.send_message(
            chat_id,
            f"Готово! Ежедневные слова: {label}.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        show_main_menu(chat_id)
        return

    if data == "help":
        bot.answer_callback_query(call.id)
        send_rich(bot,chat_id,
            "<h2>Как устроен Зубрик</h2><p>Небольшие занятия помогают сделать беларускую частью дня.</p>"
            "<h3>Слова и повторение</h3><p>Выберите тему и открывайте новые слова. Тест в чате проверяет уже изученное.</p>"
            "<h3>Ваше приложение</h3><p>Прогресс, грамматика, учебные задания для подготовки к ЦТ / ЦЭ и общие настройки.</p>"
            "<details><summary>Игры, награды и серия дней</summary><p>Отправьте другу приглашение. Правильный ответ даёт 1 бульбен, победа — ещё 30. Новое изученное слово поддерживает серию дней.</p></details>",
            "<b>Как устроен Зубрик</b>\n\nУчите слова и повторяйте их в чате. В Mini App — ваш прогресс, грамматика и учебные задания.\n\nИгры с друзьями приносят бульбены. Новое слово поддерживает серию дней.",home_only_kb())
        return

    bot.answer_callback_query(call.id)

@bot.message_handler(commands=["app"],chat_types=["private"])
def cmd_app(message):
    from zubryk.config import get_mini_app_url
    url=get_mini_app_url()
    kb=types.InlineKeyboardMarkup()
    if url:
        kb.add(types.InlineKeyboardButton("Открыть Зубрик",web_app=types.WebAppInfo(url),style="primary"))
        bot.send_message(message.chat.id,"<b>Зубрик</b>\n\nВаш прогресс, грамматика и подготовка к ЦТ / ЦЭ.",parse_mode="HTML",reply_markup=kb)
    else:
        show_main_menu(message.chat.id)


@bot.message_handler(commands=["help"],chat_types=["private"])
def cmd_help(message):
    bot.send_message(message.chat.id,"<b>Как устроен Зубрик</b>\n\nУчите слова и повторяйте их в чате. Приложение открывается кнопкой «Зубрик» в меню: там грамматика, упражнения и ваш прогресс.\n\nИгры с друзьями приносят бульбены. Новое слово поддерживает серию дней.",parse_mode="HTML",reply_markup=main_menu_kb())


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

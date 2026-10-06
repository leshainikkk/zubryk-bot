import telebot
from zubryk.config import BOT_TOKEN

if not BOT_TOKEN:
    raise RuntimeError("Укажите BOT_TOKEN в .env")
bot = telebot.TeleBot(BOT_TOKEN)

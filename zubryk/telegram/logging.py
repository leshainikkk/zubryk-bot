import logging

from zubryk.config import BOT_TOKEN


class SecretSafeFormatter(logging.Formatter):
    def format(self, record):
        value=super().format(record)
        return value.replace(BOT_TOKEN,"[redacted]") if BOT_TOKEN else value


def setup_logging():
    handler=logging.StreamHandler()
    handler.setFormatter(SecretSafeFormatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.INFO,handlers=[handler],force=True)
    for name in ("TeleBot", "telebot", "urllib3"):
        logger=logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate=True

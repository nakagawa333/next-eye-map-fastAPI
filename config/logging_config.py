from logging import FileHandler, Formatter, StreamHandler, basicConfig, getLogger, DEBUG
from logging.handlers import RotatingFileHandler
import os

#ログの設定
FORMATTER = '%(asctime)s - (%(filename)s) - [%(levelname)s] - %(message)s'
LOG_FILE = os.path.join("logs", "app.log")

def setup_logger():
    logger = getLogger("app")
    logger.setLevel(DEBUG)
    handler = StreamHandler()
    frmt = Formatter(FORMATTER)
    handler.setFormatter(frmt)
    logger.addHandler(handler)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(frmt)

    logger.addHandler(file_handler)
    return logger
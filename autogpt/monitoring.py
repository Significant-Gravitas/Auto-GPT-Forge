import json
import logging
import logging.config
import queue

"""
Module used to describe all of the different data types
"""

import logging
import logging.handlers

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"
UNDERLINE_SEQ = "\033[04m"

ORANGE = "\033[33m"
YELLOW = "\033[93m"
WHITE = "\33[37m"
BLUE = "\033[34m"
LIGHT_BLUE = "\033[94m"
RED = "\033[91m"
GREY = "\33[90m"
GREEN = "\033[92m"

EMOJIS = {
    "DEBUG": "🐛",
    "INFO": "📝",
    "CHAT": "💬",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "💥",
}

KEYWORD_COLORS = {
    "DEBUG": WHITE,
    "INFO": LIGHT_BLUE,
    "CHAT": GREEN,
    "WARNING": YELLOW,
    "ERROR": ORANGE,
    "CRITICAL": RED,
}


def formatter_message(message, use_color=True):
    """
    Syntax highlight certain keywords
    """
    if use_color:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


def format_word(message, word, color_seq, bold=False, underline=False):
    """
    Surround the fiven word with a sequence
    """
    replacer = color_seq + word + RESET_SEQ
    if underline:
        replacer = UNDERLINE_SEQ + replacer
    if bold:
        replacer = BOLD_SEQ + replacer
    return message.replace(word, replacer)


class ConsoleFormatter(logging.Formatter):
    """
    This Formatted simply colors in the levelname i.e 'INFO', 'DEBUG'
    """

    def __init__(self, fmt, datefmt=None, style="%", use_color=True):
        super().__init__(fmt, datefmt, style)
        self.use_color = use_color

    def format(self, record):
        """
        Format and highlight certain keywords
        """
        rec = record
        levelname = rec.levelname
        if self.use_color and levelname in KEYWORD_COLORS:
            levelname_color = KEYWORD_COLORS[levelname] + levelname + RESET_SEQ
            rec.levelname = levelname_color
        rec.name = GREY + f"{rec.name:<15}" + RESET_SEQ
        rec.msg = (
            KEYWORD_COLORS[levelname] + EMOJIS[levelname] + "  " + rec.msg + RESET_SEQ
        )
        return logging.Formatter.format(self, rec)


class CustomLogger(logging.Logger):
    """
    This adds extra logging functions such as logger.trade and also
    sets the logger to use the custom formatter
    """

    CONSOLE_FORMAT = (
        "[%(asctime)s] [$BOLD%(name)-15s$RESET] [%(levelname)-8s]\t%(message)s"
    )
    FORMAT = "%(asctime)s %(name)-15s %(levelname)-8s %(message)s"
    COLOR_FORMAT = formatter_message(CONSOLE_FORMAT, True)
    JSON_FORMAT = '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'

    def __init__(self, name, logLevel="DEBUG"):
        logging.Logger.__init__(self, name, logLevel)

        # Queue Handler
        queue_handler = logging.handlers.QueueHandler(queue.Queue(-1))
        json_formatter = logging.Formatter(self.JSON_FORMAT)
        queue_handler.setFormatter(json_formatter)
        self.addHandler(queue_handler)

        console_formatter = ConsoleFormatter(self.COLOR_FORMAT)
        console = logging.StreamHandler()
        console.setFormatter(console_formatter)
        self.addHandler(console)

    def chat(self, message):
        """
        Log a chat message
        """
        response = json.loads(message)
        self.info(f"Chat: {response['message']}")


class QueueLogger(logging.Logger):
    """
    Custom logger class with queue
    """

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        queue_handler = logging.handlers.QueueHandler(queue.Queue(-1))
        self.addHandler(queue_handler)


logging_config = dict(
    version=1,
    formatters={
        "console": {
            "()": ConsoleFormatter,
            "format": CustomLogger.COLOR_FORMAT,
        },
    },
    handlers={
        "h": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "level": logging.DEBUG,
        },
    },
    root={
        "handlers": ["h"],
        "level": logging.DEBUG,
    },
)


def setup_logger(json_format=False):
    """
    Setup the logger with the specified format
    """
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger("AutoGPT")
    logger.propagate = True

import logging
import datetime
import aiofiles
import asyncio


def debug():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename=f'Logs/{datetime.date.today()}-debug.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)


def info():
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename=f'Logs/{datetime.date.today()}-info.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)


async def write_to_file(location, body_msg):
    """Write a line to a file.

    :param location: (str) File Location
    :param body_msg: (str) Line that should be appended to the file.
    """
    async with aiofiles.open(location, "a+", encoding='utf-8') as file:
        await file.write(body_msg)


def manage_log(body_msg, log_type, method=None):
    """Process the type of logging it is and writes to file.

    :param body_msg: (str) Line that should be appended to the file.
    :param log_type: (str) The end of the file name that differentiates the type of logging it is.
    :param method: The function/method that called this function.
    """
    msg = f"{datetime.datetime.now()} -- {body_msg} --> {method.__name__ if method else ''}\n"
    coroutine = write_to_file(f"Logs/{datetime.date.today()}-{log_type}.log",  msg)

    asyncio.run_coroutine_threadsafe(coroutine, asyncio.get_event_loop())


def console(message, method=None):
    """Prints message to console and adds to logging.

    :param message: The message that will be printed out and logged.
    :param method: The function/method that called this function.
    """
    message = f"{message}".replace("**", "")  # getting rid of bold in markdown
    print(message)
    manage_log(message, "console", method=method)


def logfile(message):
    """Logs a message to the info file.

    :param message: The message that will be logged.
    """
    manage_log(message, "info")


def useless(message, method=None):
    """Logs Try-Except-Passes. This will put the exceptions into a log file specifically for cases with no exception
    needed.

    :param message: The message that will be logged.
    :param method: The function/method that called this function.
    """
    manage_log(message, "useless", method=method)

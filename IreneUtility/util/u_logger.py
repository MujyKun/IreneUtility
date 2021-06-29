import logging
import datetime
import aiofiles
import asyncio
import functools
import inspect


def get_class(method):
    """
    Returns the class that belongs to the method.
    :param method: The method that needs to be checked.

    REF -> https://stackoverflow.com/a/25959545/13159093
    """
    if isinstance(method, functools.partial):
        return get_class(method.func)
    if inspect.ismethod(method) or (inspect.isbuiltin(method) and getattr(method, '__self__', None) is not None and getattr(method.__self__, '__class__', None)):
        for cls in inspect.getmro(method.__self__.__class__):
            if method.__name__ in cls.__dict__:
                return cls
        method = getattr(method, '__func__', method)  # fallback to __qualname__ parsing
    if inspect.isfunction(method):
        cls = getattr(inspect.getmodule(method),
                      method.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls

    this_class = getattr(method, '__objclass__', None)  # handle special descriptor objects
    return this_class.__name__ if this_class else "Unknown_Class"


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


def manage_log(body_msg, log_type, method=None, event_loop=None):
    """Process the type of logging it is and writes to file.

    :param body_msg: (str) Line that should be appended to the file.
    :param log_type: (str) The end of the file name that differentiates the type of logging it is.
    :param method: The function/method that called this function.
    :param event_loop: An existing event loop.
    """
    try:
        class_name = ""
        func_name = ""
        if method:
            class_name = f"{get_class(method)}"
            try:
                func_name = f"{method.__name__}"
            except AttributeError:
                func_name = f"{method}"
        msg = f"{datetime.datetime.now()} -- {body_msg} " \
              f"{f'--> {class_name}.{func_name}' if method else ''}\n"
        coroutine = write_to_file(f"Logs/{datetime.date.today()}-{log_type}.log",  msg)

        asyncio.run_coroutine_threadsafe(coroutine, event_loop or asyncio.get_event_loop())
    except Exception as e:
        print(f"{e} (Exception) - Failed to log. - {body_msg} - u_logger.manage_log")


def console(message, method=None, event_loop=None):
    """Prints message to console and adds to logging.

    :param message: The message that will be printed out and logged.
    :param method: The function/method that called this function.
    :param event_loop: An existing event loop.
    """
    message = f"{message}".replace("**", "")  # getting rid of bold in markdown
    print(message)
    manage_log(message, "console", method=method, event_loop=event_loop)


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

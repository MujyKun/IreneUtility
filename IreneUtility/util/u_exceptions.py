from . import u_logger as log


class TooLarge(Exception):
    """The input was too long."""
    def __init__(self):
        super(TooLarge, self).__init__("That number was too large.")


class Limit(Exception):
    """A limit was reached."""
    def __init__(self, msg="A Limit was reached for something."):
        super(Limit, self).__init__(msg)


class ImproperFormat(Exception):
    """Invalid Format was given."""
    def __init__(self):
        super(ImproperFormat, self).__init__("An Invalid Format was given.")


class NoTimeZone(Exception):
    """No Timezone was found."""
    def __init__(self):
        super(NoTimeZone, self).__init__("The user did not have a timezone.")


class MaxAttempts(Exception):
    """Essentially StopIteration, but created for logging to file & console upon raising error."""
    def __init__(self, msg):
        super(MaxAttempts, self).__init__(f"Max Attempts reached. - {msg}")
        log.console(msg)


class ShouldNotBeHere(Exception):
    """Raised when safe-guarded code is created. If this exception is raised, the code reached a point it should not
    have"""
    def __init__(self, msg):
        super(ShouldNotBeHere, self).__init__(f"Code was reached when it shouldn't have been - {msg}")
        log.console(msg)


class InvalidParamsPassed(Exception):
    """
    Raised when IDs are invalid for an add/remove/set method.
    """
    def __init__(self, msg):
        super(InvalidParamsPassed, self).__init__(f" -> {msg}")
        log.console(msg)


class NoKeyFound(Exception):
    """
    Raised when no keys were found.
    """
    def __init__(self, msg):
        super(NoKeyFound, self).__init__(f" -> {msg}")
        log.console(msg)


class Pass(Exception):
    """
    A hack exception. This exception was meant to occur in order to jump to a part in code.
    Indicates something went right instead of wrong.
    """
    def __init__(self):
        pass


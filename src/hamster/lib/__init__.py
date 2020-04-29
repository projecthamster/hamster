import logging

logger = logging.getLogger(__name__)  # noqa: E402


from hamster.lib.fact import Fact  # for backward compatibility with v2


def default_logger(name):
    """Return a toplevel logger.

    This should be used only in the toplevel file.
    Files deeper in the hierarchy should use
    ``logger = logging.getLogger(__name__)``,
    in order to considered as children of the toplevel logger.

    Beware that without a setLevel() somewhere,
    the default value (warning) will be used, so no debug message will be shown.

    Args:
        name (str): usually `__name__` in the package toplevel __init__.py, or
                    `__file__` in a script file
                    (because __name__ would be "__main__" in this case).
    """

    # https://docs.python.org/3/howto/logging.html#logging-advanced-tutorial
    logger = logging.getLogger(name)

    # this is a basic handler, with output to stderr
    logger_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    logger_handler.setFormatter(formatter)
    logger.addHandler(logger_handler)

    return logger

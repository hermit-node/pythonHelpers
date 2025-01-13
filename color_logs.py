import logging

# ANSI color codes
RESET = "\033[0m"
COLORS = {
    "DATE": "\033[38;5;229m",  # Pastel Yellow
    "NAME": "\033[38;5;215m",  # Pastel Orange
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[1;41m",  # Red Background
    "EXTRA": "\033[36m",  # Cyan for extra variables
}


class HighlightedFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)

    def format(self, record):
        # Apply colors to specific components
        level_color = COLORS["NAME"]
        name_color = COLORS["NAME"]
        message_color = COLORS.get(record.levelname, RESET)
        extra_color = COLORS["EXTRA"]

        # Format standard fields
        record.levelname = f"{level_color}{record.levelname}{RESET}"
        record.name = f"{name_color}{record.name}{RESET}"

        # Format dynamic extra fields
        extra_fields = []
        for key, value in record.__dict__.items():
            if (
                    key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "msg", "name", "pathname", "process", "processName", "relativeCreated",
                "stack_info", "taskName", "thread", "threadName"
            } and value is not None and value != []
            ):
                extra_fields.append(f"{extra_color}{key}={value}{RESET}")

        # Format dynamic message placeholders
        if record.args and isinstance(record.args, dict):
            for key, value in record.args.items():
                colored_value = f"{extra_color}{value}{message_color}"
                record.msg = record.msg.replace(f"{{{key}}}", colored_value)

        # Combine message and extra fields
        extra_text = " | ".join(extra_fields)
        record.msg = f"{message_color}{record.msg}{RESET}"
        if extra_text:
            record.msg = f"{record.msg} ({extra_text})"

        # Format time, level, name, and message
        formatted_time = f"{COLORS['DATE']}{self.formatTime(record)}{RESET}"
        formatted_message = record.msg

        # Combine components into the desired format
        return f"{formatted_time}: {record.levelname}.{record.name} -- {formatted_message}"



class ColorfulFormatter(logging.Formatter):
    def format(self, record):
        log_color = COLORS.get(record.levelname, RESET)
        message = super().format(record)
        return f"{log_color}{message}{RESET}"


def color_logs(name="example_logger", extra_colors=None, clear_bully=False):
    logger = logging.getLogger(name)

    # Prevent duplicates and root propagation
    if logger.hasHandlers() and clear_bully:
        logger.handlers.clear()
        logger.propagate = False

    # Set up handler with HighlightedFormatter
    handler = logging.StreamHandler()
    formatter = HighlightedFormatter("%(asctime)s - %(levelname)s - %(name)s -- %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    return logger

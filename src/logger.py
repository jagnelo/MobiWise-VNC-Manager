import os
import sys
from datetime import datetime
import threading

from globals import Globals


class Logger:
    class Log:
        def __init__(self, timestamp, level, thread, source, message):
            self.timestamp = timestamp
            self.level = level
            self.thread = thread
            self.source = source
            self.message = message

    def __init__(self):
        self.logs = []
        self.logs_rlock = threading.RLock()

    def log(self, level, source, message, direct_write=False):
        log = Logger.Log(datetime.now(), level, threading.current_thread().name, source, message)
        with self.logs_rlock:
            if direct_write:
                Logger.write(log)
            else:
                self.logs.append(log)

    def info(self, source, message):
        self.log(Globals.LOGS_LEVEL_INFO, source, message)

    def debug(self, source, message):
        self.log(Globals.LOGS_LEVEL_DEBUG, source, message)

    def warn(self, source, message):
        self.log(Globals.LOGS_LEVEL_WARN, source, message)

    def error(self, source, message):
        self.log(Globals.LOGS_LEVEL_ERROR, source, message)

    def flush(self):
        with self.logs_rlock:
            for log in self.logs:
                Logger.write(log)
            self.logs.clear()

    @staticmethod
    def write(log: Log):
        if not os.path.exists(Globals.LOGS_DIR):
            os.makedirs(Globals.LOGS_DIR)
        file_name = os.path.join(Globals.LOGS_DIR, "%s.%s" % (log.thread, Globals.LOGS_FILE_TYPE))
        timestamp = str(log.timestamp)
        sep = "  "
        spaces = (" " * len(timestamp)) + sep
        message = log.message.replace("\n", "\n" + spaces).rstrip()
        with open(file_name, "a") as file:
            file.write("%s%s[%s][%s] %s\n" % (timestamp, sep, log.level, log.source, message))


logger = Logger()


class StreamRedirect(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    Source: https://stackoverflow.com/questions/19425736/how-to-redirect-stdout-and-stderr-to-logger-in-python
    """

    def __init__(self, source, level):
        self.source = source
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        logger.log(self.level, self.source, buf, direct_write=True)

    def flush(self):
        pass


sys.stdout = StreamRedirect("STDOUT", Globals.LOGS_LEVEL_INFO)
sys.stderr = StreamRedirect("STDERR", Globals.LOGS_LEVEL_ERROR)

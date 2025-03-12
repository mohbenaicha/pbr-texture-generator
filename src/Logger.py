import logging
from logging.handlers import RotatingFileHandler
import threading

class LoggerSingleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LoggerSingleton, cls).__new__(cls, *args, **kwargs)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.logger = logging.getLogger("LoggerSingleton")
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler("app.log", maxBytes=1000000, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, level, message):
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "critical":
            self.logger.critical(message)
        else:
            self.logger.info(message)

# Usage example:
log_to_file = LoggerSingleton()



# server logging
logging.basicConfig(level=logging.DEBUG)
server_logger = logging.getLogger("uvicorn")
server_logger.setLevel(logging.DEBUG)
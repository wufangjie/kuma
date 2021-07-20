

# init basic logger here
import logging
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = 'debug.log'

_initialized = False

def init_log():
    global _initialized
    if not _initialized:
        _initialized = True
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
            handlers=[
                #logging.FileHandler("{0}/{1}.log".format(logPath, fileName)),
                #logging.StreamHandler(sys.stdout)
            ])

                
        logging_file_path = os.path.join(BASE_DIR, LOG_FILE)
        log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

        #file_handler = RotatingFileHandler(logging_file_path, mode='a', maxBytes=150*1024*1024, backupCount=2, encoding='utf-8')
        file_handler = logging.FileHandler(logging_file_path, mode='a', encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(file_handler)

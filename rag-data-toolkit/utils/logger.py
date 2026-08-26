import logging
from pathlib import Path


def setup_logger(log_path: str = 'logs/app.log') -> logging.Logger:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('rag_data_toolkit')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

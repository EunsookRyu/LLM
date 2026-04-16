# logger.py
import logging
import sys


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    애플리케이션 로거를 설정하고 반환한다.
    """
    logger = logging.getLogger("chatbot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    # 콘솔 핸들러 (Docker 로그로 수집됨)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # 로그 형식: 시간 | 레벨 | 모듈 | 메시지
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 모듈 수준 로거
logger = setup_logging()

# backend/app/core/logging_config.py

import logging
import sys
import json
import os
from datetime import datetime
import traceback # 예외 정보 캡처용

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for logging."""
    def format(self, record):
        # Base record fields
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).astimezone().isoformat(), # ISO 8601 형식 타임스탬프
            "level": record.levelname,
            "message": record.getMessage(),
            # 소스 코드 위치 정보
            "module": record.name,
            "funcName": record.funcName,
            "lineno": record.lineno,
            # 프로세스/스레드 정보
            "process": record.process,
            "thread": record.thread,
            "threadName": record.threadName,
        }

        # Add service name based on module path heuristic (can be improved)
        if 'backend/app/main.py' in record.pathname:
            log_record['service'] = 'backend-api'
        elif 'backend/app/worker.py' in record.pathname:
            log_record['service'] = 'worker'
        elif 'backend/app/services' in record.pathname:
             log_record['service'] = 'backend-service' # 또는 해당 서비스 파일명으로 구분
        else:
            log_record['service'] = 'unknown' # 또는 'app'

        # Add extra context passed with the log record
        # logger.info("message", extra={'extra_context': {'key1': 'value1', 'key2': 'value2'}})
        if hasattr(record, 'extra_context') and isinstance(record.extra_context, dict):
            log_record.update(record.extra_context)

        # Add exception info if present
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
            # 또는 traceback 모듈 사용
            # exc_type, exc_value, exc_traceback = record.exc_info
            # log_record['exc_type'] = exc_type.__name__
            # log_record['exc_value'] = str(exc_value)
            # log_record['exc_traceback'] = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))


        # Add stack info if present
        if record.stack_info:
            log_record['stack_info'] = self.formatStack(record.stack_info)

        return json.dumps(log_record)

def setup_logging():
    """Configures the root logger with a JSON formatter."""
    # Get the root logger
    root_logger = logging.getLogger()

    # Configure logging level (from environment variable, default INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create a console handler to output logs to standard output
    # In containerized environments, logs to stdout/stderr are collected by default
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level) # Handler level should be <= logger level

    # Set the custom JSON formatter
    formatter = JsonFormatter()
    console_handler.setFormatter(formatter)

    # Add the handler to the root logger
    root_logger.addHandler(console_handler)

    # Optional: Configure specific loggers (e.g., library loggers) if needed
    # logging.getLogger('boto3').setLevel(logging.WARNING) # Suppress verbose boto3 logs

    logger.info("Logging configured with JSON format.")


# --- Usage in application code (backend/app/main.py, backend/app/worker.py, etc.) ---

# 1. 파일 상단에 로깅 설정 함수 임포트 및 호출
# import logging_config
# logging_config.setup_logging()
# logger = logging.getLogger(__name__) # 해당 모듈의 로거 인스턴스 가져오기

# 2. 로깅 사용
# logger.info("애플리케이션 시작", extra={'extra_context': {'version': '1.0'}})
# logger.warning("주의 메시지 발생")
# logger.error("오류 발생", extra={'extra_context': {'user_id': 123}}, exc_info=True) # exc_info=True로 예외 정보 포함
# logger.debug("디버그 정보")

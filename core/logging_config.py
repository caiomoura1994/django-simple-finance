import inspect
import logging
import os
import sys
from loguru import logger

# Interceptar logs do Django padrão e redirecionar para loguru
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """Configura o loguru para desenvolvimento ou produção"""
    DEBUG = os.getenv('DEBUG', '1') == '1'

    # Remover handler padrão do loguru
    logger.remove()

    if DEBUG:
        # Desenvolvimento local - console colorido
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True,
        )
    else:
        # Produção - Google Cloud Logging
        from google.cloud import logging as cloud_logging
        from google.cloud.logging.handlers import CloudLoggingHandler

        GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT', '')
        client = cloud_logging.Client(project=GOOGLE_CLOUD_PROJECT)
        cloud_handler = CloudLoggingHandler(client)

        # Criar sink para loguru usando o handler do Google Cloud
        def cloud_logging_sink(message):
            record = message.record

            # Converter nível do loguru para nível do logging padrão
            level_map = {
                'TRACE': logging.DEBUG,
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'SUCCESS': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
                'CRITICAL': logging.CRITICAL,
            }
            log_level = level_map.get(record['level'].name, logging.INFO)

            # Criar LogRecord compatível
            log_record = logging.LogRecord(
                name=record['name'],
                level=log_level,
                pathname=record['file'].path,
                lineno=record['line'],
                msg=record['message'],
                args=(),
                exc_info=record['exception'],
            )
            cloud_handler.emit(log_record)

        logger.add(cloud_logging_sink, level="DEBUG", serialize=False)

    # Configurar interceptação de logs do Django
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

"""
Test settings for the project.
These settings override the base settings when running tests.
"""
from .settings import *  # noqa
import tempfile
import os

# Media files
TEST_MEDIA_ROOT = os.path.join(tempfile.gettempdir(), 'django_test_media')
MEDIA_ROOT = TEST_MEDIA_ROOT
MEDIA_URL = '/media/'

# Celery
CELERY_TASK_ALWAYS_EAGER = True  # Executa tasks de forma síncrona
CELERY_TASK_EAGER_PROPAGATES = True  # Propaga exceções normalmente

# Database (opcional, mas recomendado para testes mais rápidos)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Usa SQLite em memória para testes mais rápidos
    }
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# File Upload Settings
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.MemoryFileUploadHandler',
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
FILE_UPLOAD_TEMP_DIR = os.path.join(TEST_MEDIA_ROOT, 'tmp')
FILE_UPLOAD_PERMISSIONS = 0o644

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
} 
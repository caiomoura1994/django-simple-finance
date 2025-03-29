import os
import django
from django.conf import settings

# Configure Django settings before importing Celery app
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.test_settings')
django.setup()

# Import Celery app after Django is configured
from core.celery import app as celery_app

# Configure Celery for testing
celery_app.conf.update(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
) 
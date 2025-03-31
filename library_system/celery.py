import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')

app = Celery('library_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-overdue-loand-daily': {
        'task': 'library_system.tasks.check_overdue_loans',
        'schedule': 86400.0,
    },
}
app.conf.timezone = 'UTC'
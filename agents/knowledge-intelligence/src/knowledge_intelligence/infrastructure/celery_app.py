from celery import Celery
from knowledge_intelligence.settings import get_settings

settings = get_settings()
app = Celery(
    "knowledge_intelligence", broker=settings.redis_url, backend=settings.redis_url
)
app.conf.task_default_queue = "knowledge"
app.conf.imports = ("knowledge_intelligence.infrastructure.tasks",)

from celery import Celery
from kombu import Exchange, Queue
from app import models
from app.core.settings import settings

# Define nossas filas explicitamente
default_exchange = Exchange('default', type='direct')
task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('dead_letter', default_exchange, routing_key='dead_letter'),
)

# Define as rotas. Qualquer tarefa não especificada vai para a fila 'default'.
task_routes = {
    'app.contests.tasks.process_edict_task': {
        'queue': 'default',
        'routing_key': 'default',
    },
}

celery_app = Celery("tasks")

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    include=["app.contests.tasks"],
    
    # Vincula as filas e rotas que definimos
    task_queues=task_queues,
    task_routes=task_routes,
    task_default_queue='default',

    # --- CONFIGURAÇÃO DA DEAD LETTER QUEUE ---
    # Se uma tarefa falhar, ela será reenviada para a exchange 'default'
    # com a routing_key 'dead_letter', caindo na nossa fila 'dead_letter'.
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
from celery import shared_task

from apps.orders.daily_sales_whatsapp import run_daily_sales_whatsapp_job
from apps.orders.walk_in_whatsapp import send_walk_in_whatsapp


@shared_task(name='apps.orders.tasks.send_walk_in_whatsapp_task')
def send_walk_in_whatsapp_task(order_id: int, event: str):
    send_walk_in_whatsapp(order_id, event)


@shared_task(name='apps.orders.tasks.send_daily_sales_whatsapp_task')
def send_daily_sales_whatsapp_task():
    return run_daily_sales_whatsapp_job()

import logging

from celery import shared_task

from .services import process_admin_message

logger = logging.getLogger(__name__)


@shared_task(name='apps.messaging.tasks.process_admin_message_task')
def process_admin_message_task(message_id):
  """Background task to deliver an admin outbound message."""
  try:
    return process_admin_message(message_id)
  except Exception as exc:
    logger.exception('Error processing admin message %s: %s', message_id, exc)
    return False

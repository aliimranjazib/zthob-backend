from celery import shared_task

from apps.invoicing.services.walk_in_invoice import issue_walk_in_tax_invoice


@shared_task(name='apps.invoicing.tasks.issue_walk_in_tax_invoice_task')
def issue_walk_in_tax_invoice_task(order_id: int):
    issue_walk_in_tax_invoice(order_id)

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.invoicing.models import TaxInvoice
from apps.invoicing.serializers import TaxInvoiceSummarySerializer
from apps.invoicing.services.walk_in_invoice import schedule_walk_in_tax_invoice
from apps.orders.models import Order
from apps.tailors.permissions import IsShopStaff
from apps.tailors.shop_access import user_can_manage_shop_order
from apps.tailors.views.base import BaseTailorAPIView
from zthob.utils import api_response


class TailorOrderTaxInvoiceView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    @extend_schema(
        summary='Get walk-in tax invoice status',
        responses={200: TaxInvoiceSummarySerializer},
        tags=['Tailor Orders'],
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.select_related('tax_invoice'), pk=order_id)
        if not user_can_manage_shop_order(request.user, order, employee_permission='can_manage_orders'):
            if not user_can_manage_shop_order(request.user, order, employee_permission='can_manage_pos'):
                return api_response(
                    success=False,
                    message="You don't have access to this order",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        tax_invoice = getattr(order, 'tax_invoice', None)
        if not tax_invoice:
            return api_response(
                success=True,
                message='No tax invoice for this order yet',
                data=None,
                status_code=status.HTTP_200_OK,
            )
        serializer = TaxInvoiceSummarySerializer(tax_invoice, context={'request': request})
        return api_response(success=True, message='Tax invoice retrieved', data=serializer.data)


class TailorOrderTaxInvoiceDownloadView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.select_related('tax_invoice'), pk=order_id)
        if not user_can_manage_shop_order(request.user, order, employee_permission='can_manage_orders'):
            if not user_can_manage_shop_order(request.user, order, employee_permission='can_manage_pos'):
                return api_response(
                    success=False,
                    message="You don't have access to this order",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        tax_invoice = getattr(order, 'tax_invoice', None)
        if not tax_invoice or not tax_invoice.pdf_file:
            raise Http404('Tax invoice PDF not available')
        return FileResponse(
            tax_invoice.pdf_file.open('rb'),
            as_attachment=True,
            filename=f'tax_invoice_{order.order_number}.pdf',
            content_type='application/pdf',
        )


class TailorOrderTaxInvoiceRetryView(BaseTailorAPIView):
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        if not user_can_manage_shop_order(request.user, order, employee_permission='can_manage_orders'):
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        tax_invoice = getattr(order, 'tax_invoice', None)
        if tax_invoice and tax_invoice.is_success:
            serializer = TaxInvoiceSummarySerializer(tax_invoice, context={'request': request})
            return api_response(success=True, message='Tax invoice already issued', data=serializer.data)
        schedule_walk_in_tax_invoice(order.id)
        return api_response(
            success=True,
            message='Tax invoice submission queued',
            data={'order_id': order.id},
            status_code=status.HTTP_202_ACCEPTED,
        )

# apps/tailors/views/order_download.py
"""
View that allows authenticated tailors to download a PDF of a specific order.

Endpoint:
    GET /api/tailors/orders/<order_id>/download-pdf/

Returns:
    - 200 application/pdf  with Content-Disposition: attachment; filename="order_<number>.pdf"
    - 403 if the user is not a TAILOR or does not own the order
    - 404 if the order does not exist
"""
import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.orders.models import Order
from apps.tailors.permissions import IsShopStaff
from apps.tailors.services.order_pdf import generate_order_pdf
from zthob.utils import api_response
from .base import BaseTailorAPIView

logger = logging.getLogger(__name__)


class TailorOrderDownloadPDFView(BaseTailorAPIView):
    """
    Download a full PDF receipt for a specific order.

    Only the tailor who owns the order can download it.
    The PDF includes order details, customer info, items, measurements,
    pricing summary and status history.
    """
    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    @extend_schema(
        summary="Download order PDF",
        description=(
            "Download a comprehensive PDF receipt for the specified order. "
            "PDF includes order details, customer info, all items with measurements "
            "and custom styles, pricing breakdown and status history. "
            "Returns a binary PDF file."
        ),
        responses={
            200: bytes,   # raw PDF
            403: dict,
            404: dict,
        },
        tags=["Tailor Orders"],
        parameters=[
            {
                'name': 'order_id',
                'in': 'path',
                'required': True,
                'description': 'ID of the order to download',
                'schema': {'type': 'integer'},
            }
        ],
    )
    def get(self, request, order_id):
        profile = self.get_tailor_profile(request.user)
        if not profile:
            return api_response(
                success=False,
                message="Tailor profile not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Fetch order with related data in a single query burst
        order = get_object_or_404(
            Order.objects.select_related(
                'customer',
                'tailor',
                'tailor__tailor_profile',
                'rider',
                'assigned_rider',
                'family_member',
                'delivery_address',
            ).prefetch_related(
                'order_items__fabric',
                'order_items__family_member',
                'payments__collected_by',
                'status_history__changed_by',
            ),
            id=order_id,
        )

        if order.tailor_id != profile.user_id:
            return api_response(
                success=False,
                message="You don't have access to this order",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Detect language from Accept-Language header (e.g. "ar", "ar-SA", "ar;q=0.9")
        accept_lang = request.headers.get('Accept-Language', 'en')
        lang = 'ar' if accept_lang.strip().lower().startswith('ar') else 'en'

        # Generate PDF
        try:
            pdf_bytes = generate_order_pdf(order, lang=lang)
        except Exception as exc:
            logger.exception("PDF generation failed for order %s: %s", order_id, exc)
            return api_response(
                success=False,
                message="Failed to generate PDF. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = f"order_{order.order_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(pdf_bytes)
        return response

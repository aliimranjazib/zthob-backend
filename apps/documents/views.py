from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated

from apps.documents.service import generate_order_html
from apps.orders.models import Order
from apps.tailors.permissions import IsShopStaff
from apps.tailors.views.base import BaseTailorAPIView
from zthob.translations import get_language_from_request
from zthob.utils import api_response


class OrderDocumentPreviewView(BaseTailorAPIView):
    """HTML preview of the complete order document (same layout as the PDF)."""

    permission_classes = [IsAuthenticated, IsShopStaff]
    required_employee_permission = 'can_manage_orders'

    @extend_schema(exclude=True)
    def get(self, request, order_id):
        profile = self.get_tailor_profile(request.user)
        if not profile:
            return api_response(success=False, message='Tailor profile not found', status_code=404)

        try:
            order = Order.objects.select_related(
                'customer',
                'tailor',
                'tailor__tailor_profile',
                'measurement_rider__rider_profile',
                'delivery_rider__rider_profile',
                'delivery_address',
            ).prefetch_related(
                'order_items__fabric',
                'order_items__family_member',
                'order_items__customer_fabric_images',
                'status_history__changed_by',
            ).get(id=order_id)
        except Order.DoesNotExist:
            return api_response(success=False, message='Order not found', status_code=404)

        if order.tailor_id != profile.user_id:
            return api_response(success=False, message="You don't have access to this order", status_code=403)

        lang = request.GET.get('lang') or get_language_from_request(request) or 'en'
        if lang not in ('en', 'ar', 'ur'):
            lang = 'en'
        html, _context, _layout = generate_order_html(order, lang=lang)
        return HttpResponse(html, content_type='text/html; charset=utf-8')

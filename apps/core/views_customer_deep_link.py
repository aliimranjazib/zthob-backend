"""Public HTTP endpoints for customer order deep links and app link verification."""

from __future__ import annotations

import json

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from apps.core.customer_deep_link import (
    build_android_assetlinks_payload,
    build_apple_app_site_association_payload,
    custom_scheme_order_url,
    customer_app_android_package,
    parse_order_id_from_path,
)
from apps.orders.models import Order


def _absolute_order_url(request, order_id: int) -> str:
    return request.build_absolute_uri(f'/order/{order_id}')


def _store_context() -> dict:
    return {
        'play_store_url': (getattr(settings, 'CUSTOMER_APP_PLAY_STORE_URL', '') or '').strip(),
        'app_store_url': (getattr(settings, 'CUSTOMER_APP_APP_STORE_URL', '') or '').strip(),
        'android_package': customer_app_android_package(),
    }


@require_GET
@cache_control(public=True, max_age=300)
def customer_order_deep_link_view(request, order_id: str):
    parsed = parse_order_id_from_path(order_id)
    if parsed is None:
        raise Http404('Invalid order link')

    order_https_url = _absolute_order_url(request, parsed)
    order_exists = Order.objects.filter(pk=parsed).exists()
    context = {
        **_store_context(),
        'order_id': parsed,
        'order_exists': order_exists,
        'order_url': order_https_url,
        'order_https_url': order_https_url,
        'custom_scheme_url': custom_scheme_order_url(parsed),
        'page_title': 'Mgask — Order',
        'auto_redirect_app_store': getattr(settings, 'CUSTOMER_DEEPLINK_AUTO_REDIRECT', True),
    }
    return TemplateResponse(request, 'customer_order_deep_link.html', context)


@require_GET
@cache_control(public=True, max_age=3600)
def android_assetlinks_view(request):
    payload = build_android_assetlinks_payload()
    return JsonResponse(payload, safe=False)


@require_GET
@csrf_exempt
@cache_control(public=True, max_age=3600)
def apple_app_site_association_view(request):
    payload = build_apple_app_site_association_payload()
    return HttpResponse(
        json.dumps(payload, separators=(',', ':')),
        content_type='application/json',
    )


@require_GET
@cache_control(public=True, max_age=3600)
def apple_app_site_association_legacy_view(request):
    """Some crawlers request the file at the site root."""
    return apple_app_site_association_view(request)

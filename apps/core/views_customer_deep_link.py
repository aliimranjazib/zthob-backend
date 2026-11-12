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
    customer_app_android_package,
    customer_app_android_sha256_list,
    customer_app_apple_app_id,
    customer_order_link_paths,
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

    order_exists = Order.objects.filter(pk=parsed).exists()
    context = {
        **_store_context(),
        'order_id': parsed,
        'order_exists': order_exists,
        'order_url': _absolute_order_url(request, parsed),
        'page_title': 'Mgask — Order',
    }
    return TemplateResponse(request, 'customer_order_deep_link.html', context)


@require_GET
@cache_control(public=True, max_age=3600)
def android_assetlinks_view(request):
    fingerprints = customer_app_android_sha256_list()
    package = customer_app_android_package()
    if not package or not fingerprints:
        return JsonResponse([], safe=False)

    payload = [
        {
            'relation': ['delegate_permission/common.handle_all_urls'],
            'target': {
                'namespace': 'android_app',
                'package_name': package,
                'sha256_cert_fingerprints': fingerprints,
            },
        }
    ]
    return JsonResponse(payload, safe=False)


def _apple_app_site_association_payload() -> dict:
    app_id = customer_app_apple_app_id()
    if not app_id:
        return {'applinks': {'apps': [], 'details': []}}

    return {
        'applinks': {
            'apps': [],
            'details': [
                {
                    'appID': app_id,
                    'paths': customer_order_link_paths(),
                }
            ],
        }
    }


@require_GET
@csrf_exempt
@cache_control(public=True, max_age=3600)
def apple_app_site_association_view(request):
    payload = _apple_app_site_association_payload()
    return HttpResponse(
        json.dumps(payload, separators=(',', ':')),
        content_type='application/json',
    )


@require_GET
@cache_control(public=True, max_age=3600)
def apple_app_site_association_legacy_view(request):
    """Some crawlers request the file at the site root."""
    return apple_app_site_association_view(request)

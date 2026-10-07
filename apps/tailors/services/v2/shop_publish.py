"""Owner v2 shop publish readiness and submit-for-review."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.tailors.models import ServiceArea, ShopStaffAssignment, TailorProfile, TailorProfileReview

MANAGER_ROLE = 'manager'

PUBLISHABLE_STATUSES = frozenset({'draft', 'rejected'})
BLOCKED_ALREADY_SUBMITTED = frozenset({'pending'})
BLOCKED_ALREADY_LIVE = frozenset({'approved'})


class PublishStateError(Exception):
    """Review status does not allow publish."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class PublishBlockedError(Exception):
    """Profile/staff checks failed."""

    def __init__(self, payload: dict):
        super().__init__('Publish blocked')
        self.payload = payload


def _review_for_shop(shop: TailorProfile) -> TailorProfileReview:
    review = getattr(shop, 'review', None)
    if review is not None:
        return review
    review, _created = TailorProfileReview.objects.get_or_create(
        profile=shop,
        defaults={'review_status': 'draft'},
    )
    return review


def _shop_has_operational_staff(shop: TailorProfile) -> bool:
    assignments = (
        ShopStaffAssignment.objects.filter(
            shop_id=shop.id,
            is_active=True,
            staff_member__is_active=True,
            staff_member__user__is_active=True,
        )
        .exclude(staff_member__user__phone__isnull=True)
        .exclude(staff_member__user__phone='')
        .select_related('staff_member')
    )
    for assignment in assignments:
        roles = assignment.roles or []
        if MANAGER_ROLE in roles or assignment.can_manage_orders:
            return True
    return False


def _service_area_ok(review: TailorProfileReview) -> bool:
    if not review.service_areas:
        return False
    area_id = review.service_areas[0]
    return ServiceArea.objects.filter(id=area_id, is_active=True).exists()


def evaluate_publish_readiness(shop: TailorProfile) -> dict:
    review = _review_for_shop(shop)
    items = []

    shop_name_ok = bool((shop.shop_name or '').strip())
    items.append({
        'key': 'shop_name',
        'ok': shop_name_ok,
        'message': 'Shop name is set.' if shop_name_ok else 'Shop name is required.',
    })

    address_ok = bool((shop.address or '').strip())
    items.append({
        'key': 'address',
        'ok': address_ok,
        'message': 'Address is set.' if address_ok else 'Address is required.',
    })

    service_area_ok = _service_area_ok(review)
    items.append({
        'key': 'service_area',
        'ok': service_area_ok,
        'message': (
            'Service area is set.'
            if service_area_ok
            else 'Service area is required.'
        ),
    })

    shop_image_ok = bool(shop.shop_image)
    items.append({
        'key': 'shop_image',
        'ok': shop_image_ok,
        'message': 'Shop image is set.' if shop_image_ok else 'Shop image is required.',
    })

    staff_ok = _shop_has_operational_staff(shop)
    items.append({
        'key': 'operational_staff',
        'ok': staff_ok,
        'message': (
            'A manager or order manager is assigned to this shop.'
            if staff_ok
            else 'Assign an active manager or staff who can manage orders for this shop.'
        ),
    })

    blocking_issues = [item['message'] for item in items if not item['ok']]
    ready = not blocking_issues

    return {
        'ready': ready,
        'review_status': review.review_status,
        'items': items,
        'blocking_issues': blocking_issues,
    }


def publish_shop(shop: TailorProfile) -> TailorProfileReview:
    with transaction.atomic():
        review = _review_for_shop(shop)
        status = review.review_status

        if status in BLOCKED_ALREADY_SUBMITTED:
            raise PublishStateError(
                'Shop is already submitted for review.',
                code='already_pending',
            )
        if status in BLOCKED_ALREADY_LIVE:
            raise PublishStateError(
                'Shop is already approved and live.',
                code='already_approved',
            )
        if status not in PUBLISHABLE_STATUSES:
            raise PublishStateError(
                f'Cannot publish from review status "{status}".',
                code='invalid_status',
            )

        checklist = evaluate_publish_readiness(shop)
        if not checklist['ready']:
            raise PublishBlockedError(checklist)

        review.review_status = 'pending'
        review.submitted_at = timezone.now()
        review.rejection_reason = None
        review.save(
            update_fields=[
                'review_status',
                'submitted_at',
                'rejection_reason',
                'updated_at',
            ],
        )
        return review

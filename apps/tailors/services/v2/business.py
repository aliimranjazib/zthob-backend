"""V2 business domain services."""

from apps.core.services import PhoneVerificationService
from apps.tailors.models import Business, TailorProfile


def get_owner_business(user) -> Business | None:
    return Business.objects.filter(owner_id=user.id, is_active=True).first()


def create_business(*, owner, validated_data) -> Business:
    phone = validated_data.get('contact_phone') or owner.phone or ''
    if phone:
        phone = PhoneVerificationService.normalize_phone_to_local(phone)

    business = Business.objects.create(
        owner=owner,
        name=validated_data.get('name', '').strip(),
        contact_phone=phone,
        contact_email=validated_data.get('contact_email'),
        city=validated_data.get('city', '').strip(),
        default_language=validated_data.get('default_language', 'ar'),
        timezone=validated_data.get('timezone', 'Asia/Riyadh'),
        currency=validated_data.get('currency', 'SAR'),
        status=Business.STATUS_ACTIVE,
        setup_step=Business.SETUP_BUSINESS_CREATED,
    )
    if validated_data.get('logo'):
        business.logo = validated_data['logo']
        business.save(update_fields=['logo', 'updated_at'])
    return business


def update_business(*, business: Business, validated_data) -> Business:
    for field, value in validated_data.items():
        setattr(business, field, value)
    business.save()
    return business


def ensure_business_for_shop_create(*, owner, shop_name: str) -> Business:
    business = get_owner_business(owner)
    if business is not None:
        return business

    phone = PhoneVerificationService.normalize_phone_to_local(owner.phone or '')
    return Business.objects.create(
        owner=owner,
        name=(shop_name or '').strip() or owner.get_full_name() or '',
        contact_phone=phone,
        status=Business.STATUS_ACTIVE,
        setup_step=Business.SETUP_BUSINESS_CREATED,
    )


def mark_business_shop_progress(business: Business) -> None:
    shop_count = (
        TailorProfile.objects.filter(business_id=business.id)
        .exclude(shop_name__isnull=True)
        .exclude(shop_name='')
        .count()
    )
    if shop_count <= 0:
        business.setup_step = Business.SETUP_BUSINESS_CREATED
    elif shop_count == 1:
        business.setup_step = Business.SETUP_FIRST_SHOP_CREATED
    else:
        business.setup_step = Business.SETUP_COMPLETED
    business.status = Business.STATUS_ACTIVE
    business.save(update_fields=['setup_step', 'status', 'updated_at'])

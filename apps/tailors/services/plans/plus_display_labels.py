"""Localized product names and settings-tile copy for Plus plans."""


def build_tailor_plus_display_fields(*, language: str, translate) -> dict:
    plan_name = translate('Tailor Plus', language)
    return {
        'display_name': plan_name,
        'upgrade_label': translate('Upgrade to {plan}', language, plan=plan_name),
    }


def build_owner_plus_display_fields(*, language: str, translate) -> dict:
    plan_name = translate('Owner Plus', language)
    return {
        'display_name': plan_name,
        'upgrade_label': translate('Upgrade to {plan}', language, plan=plan_name),
    }

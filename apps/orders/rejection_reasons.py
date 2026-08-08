"""Predefined tailor order rejection reasons for COD reject flow."""

ORDER_REJECTION_REASONS = (
    ('out_of_capacity', 'Shop is at full capacity'),
    ('cannot_meet_deadline', 'Cannot meet the requested delivery date'),
    ('fabric_unavailable', 'Required fabric is not available'),
    ('service_not_available', 'Service is not available at the moment'),
    ('customer_request_unfeasible', 'Customer request cannot be fulfilled'),
    ('other', 'Other reason'),
)

ORDER_REJECTION_REASON_KEYS = {key for key, _ in ORDER_REJECTION_REASONS}


def get_rejection_reason_label(reason_code, language='en'):
    from zthob.translations import translate_message

    for key, label in ORDER_REJECTION_REASONS:
        if key == reason_code:
            return translate_message(label, language)
    return None


def build_rejection_reasons_config(language='en'):
    from zthob.translations import translate_message

    return [
        {
            'key': key,
            'label': translate_message(label, language),
        }
        for key, label in ORDER_REJECTION_REASONS
    ]


def resolve_rejection_reason(data, *, language='en'):
    """
    Resolve the final rejection reason from optional predefined code and/or free text.

    Rules:
    - At least one of rejection_reason_code or rejection_reason must be provided.
    - rejection_reason_code must match a configured key when provided.
    - For code "other", rejection_reason text is required (min 10 chars).
    - For any other code, the predefined translated label is used.
    - Free-text-only rejections require at least 10 characters.
    """
    reason_code = (data.get('rejection_reason_code') or '').strip()
    reason_text = (data.get('rejection_reason') or '').strip()

    if reason_code and reason_code not in ORDER_REJECTION_REASON_KEYS:
        raise ValueError('Invalid rejection reason code.')

    if not reason_code and not reason_text:
        raise ValueError('A rejection reason is required.')

    if reason_code == 'other':
        if len(reason_text) < 10:
            raise ValueError('Please provide details for the rejection reason (min 10 characters).')
        return reason_code, reason_text

    if reason_code:
        label = get_rejection_reason_label(reason_code, language)
        if not label:
            raise ValueError('Invalid rejection reason code.')
        if reason_text:
            return reason_code, f'{label} - {reason_text}'
        return reason_code, label

    if len(reason_text) < 10:
        raise ValueError('Rejection reason is required (min 10 characters).')

    return '', reason_text

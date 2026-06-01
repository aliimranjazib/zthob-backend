from decimal import Decimal, ROUND_HALF_UP


PAYMENT_OPTION_KEYS = ('full', 'advance_50', 'advance_30', 'pay_later')


def money(value):
    return Decimal(value or '0.00').quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def build_payment_options(total_amount):
    """Return backend-controlled payment choices for a checkout total."""
    total = money(total_amount)
    options = [
        {
            'key': 'full',
            'label': 'Pay Full Amount',
            'payment_plan': 'full',
            'pay_now_amount': str(total),
            'pay_later_amount': '0.00',
            'payment_status_after_order': 'paid',
        }
    ]

    if total >= Decimal('100.00'):
        pay_now = money(total * Decimal('0.50'))
        options.append({
            'key': 'advance_50',
            'label': 'Pay 50% Advance',
            'payment_plan': 'partial',
            'pay_now_amount': str(pay_now),
            'pay_later_amount': str(money(total - pay_now)),
            'payment_status_after_order': 'partially_paid',
        })

    if total >= Decimal('500.00'):
        pay_now = money(total * Decimal('0.30'))
        options.append({
            'key': 'advance_30',
            'label': 'Pay 30% Advance',
            'payment_plan': 'partial',
            'pay_now_amount': str(pay_now),
            'pay_later_amount': str(money(total - pay_now)),
            'payment_status_after_order': 'partially_paid',
        })

    options.append({
        'key': 'pay_later',
        'label': 'Cash / Pay Later',
        'payment_plan': 'pay_later',
        'pay_now_amount': '0.00',
        'pay_later_amount': str(total),
        'payment_status_after_order': 'pending',
    })
    return options


def get_payment_option(total_amount, key):
    for option in build_payment_options(total_amount):
        if option['key'] == key:
            return option
    return None

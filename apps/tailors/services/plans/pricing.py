"""Shared Tailor Plus / Owner Plus price copy from mgask.sa/plans.html."""

from __future__ import annotations

PLUS_PRICE_AMOUNT = 3200
PLUS_PRICE_CURRENCY = 'SAR'
PLUS_BILLING_PERIOD = 'year'
PLUS_MONTHLY_EQUIVALENT = 267

PLUS_PRICE_LABEL = '3,200 SAR / year'
PLUS_VAT_NOTE = 'excl. VAT – about SAR 267 a month'
PLUS_PRICE_FOOTNOTE = (
    'The subscription is annual and renews after we notify you, '
    'and you are entitled to a full refund within 7 days of activation.'
)
PLUS_PRICE_TAGLINE = 'Run your shop with us'
FREE_PRICE_LABEL = 'Free'


def build_plus_price(*, language: str, translate) -> dict:
    return {
        'amount': PLUS_PRICE_AMOUNT,
        'currency': PLUS_PRICE_CURRENCY,
        'billing_period': PLUS_BILLING_PERIOD,
        'monthly_equivalent': PLUS_MONTHLY_EQUIVALENT,
        'label': translate(PLUS_PRICE_LABEL, language),
        'vat_note': translate(PLUS_VAT_NOTE, language),
        'tagline': translate(PLUS_PRICE_TAGLINE, language),
        'footnote': translate(PLUS_PRICE_FOOTNOTE, language),
    }


def build_free_price(*, language: str, translate) -> dict:
    return {
        'amount': 0,
        'currency': PLUS_PRICE_CURRENCY,
        'billing_period': PLUS_BILLING_PERIOD,
        'monthly_equivalent': None,
        'label': translate(FREE_PRICE_LABEL, language),
        'vat_note': None,
        'tagline': None,
        'footnote': None,
    }

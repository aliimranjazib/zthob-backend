from django.template.response import TemplateResponse

from apps.tailors.content.tailor_faq import (
    DEFAULT_FAQ_LANGUAGE,
    SUPPORTED_FAQ_LANGUAGES,
    get_tailor_faq_content,
    resolve_faq_language,
)


def tailor_help_view(request):
    """Public tailor FAQ page for web / in-app WebView."""
    lang = resolve_faq_language(request.GET.get('lang'))
    content = get_tailor_faq_content(lang)

    return TemplateResponse(
        request,
        'tailors/tailor_help.html',
        {
            'lang': lang,
            'content': content,
            'is_rtl': lang in ('ar', 'ur'),
            'supported_languages': SUPPORTED_FAQ_LANGUAGES,
            'default_language': DEFAULT_FAQ_LANGUAGE,
        },
    )

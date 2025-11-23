# API Translation System Guide

## Overview

The API translation system automatically translates all API responses to Arabic based on the `Accept-Language` header sent by the client. This is a **fast, in-memory translation system** with O(1) lookup performance - no external API calls or database queries.

## How It Works

1. **Client sends request** with `Accept-Language: ar` header
2. **Middleware detects** the language preference
3. **api_response() function** automatically translates messages and errors
4. **Response returned** in Arabic (or English if header not set)

## Usage

### For Clients (Frontend/Mobile Apps)

Simply include the `Accept-Language` header in your API requests:

```bash
# English (default)
curl -X GET "http://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept-Language: en"

# Arabic
curl -X GET "http://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept-Language: ar"
```

### For Developers (Backend)

**No code changes needed!** The translation happens automatically. Your existing code:

```python
return api_response(
    success=True,
    message="Order created successfully",
    data=serializer.data
)
```

Will automatically return Arabic if the client sends `Accept-Language: ar`:

```json
{
    "success": true,
    "message": "تم إنشاء الطلب بنجاح",
    "data": {...}
}
```

### Adding New Translations

To add translations for new messages, edit `zthob/translations.py`:

```python
TRANSLATIONS = {
    # Add your new translation here
    "Your new message": "رسالتك الجديدة بالعربية",
    
    # With placeholders
    "Order {order_id} created": "تم إنشاء الطلب {order_id}",
}
```

## Performance

- **Lookup Speed**: O(1) - instant dictionary lookup
- **Memory**: All translations loaded in memory (very fast)
- **No External Calls**: No API costs or network latency
- **No Database Queries**: Pure Python dictionary operations

## Language Detection

The system detects language from:
1. `Accept-Language` HTTP header (primary method)
2. Falls back to English if header not present

### Accept-Language Header Format

The system supports standard HTTP Accept-Language headers:
- `Accept-Language: ar` → Arabic
- `Accept-Language: ar-SA,ar;q=0.9` → Arabic (preferred)
- `Accept-Language: en` → English
- No header → English (default)

## Translation Coverage

### Currently Translated

✅ Success messages  
✅ Error messages  
✅ Validation errors  
✅ Authentication errors  
✅ Permission errors  
✅ Not found errors  
✅ Common field validation errors  

### Adding More Translations

To add translations for messages not yet covered:

1. **Find the English message** in your code
2. **Add to `zthob/translations.py`**:
   ```python
   TRANSLATIONS = {
       "Your message": "رسالتك",
   }
   ```
3. **Restart Django** (translations are loaded at startup)

## Examples

### Example 1: Success Response

**Request (English)**:
```bash
curl -H "Accept-Language: en" /api/orders/123/
```

**Response**:
```json
{
    "success": true,
    "message": "Order retrieved successfully",
    "data": {...}
}
```

**Request (Arabic)**:
```bash
curl -H "Accept-Language: ar" /api/orders/123/
```

**Response**:
```json
{
    "success": true,
    "message": "تم استرجاع الطلب بنجاح",
    "data": {...}
}
```

### Example 2: Error Response

**Request (English)**:
```bash
curl -H "Accept-Language: en" /api/orders/999/
```

**Response**:
```json
{
    "success": false,
    "message": "The requested resource was not found.",
    "errors": "Not found"
}
```

**Request (Arabic)**:
```bash
curl -H "Accept-Language: ar" /api/orders/999/
```

**Response**:
```json
{
    "success": false,
    "message": "الموارد المطلوبة غير موجودة.",
    "errors": "غير موجود"
}
```

### Example 3: Validation Errors

**Request (English)**:
```bash
curl -H "Accept-Language: en" -X POST /api/orders/ \
  -d '{"invalid": "data"}'
```

**Response**:
```json
{
    "success": false,
    "message": "Validation failed",
    "errors": {
        "field_name": ["This field is required."]
    }
}
```

**Request (Arabic)**:
```bash
curl -H "Accept-Language: ar" -X POST /api/orders/ \
  -d '{"invalid": "data"}'
```

**Response**:
```json
{
    "success": false,
    "message": "فشل التحقق",
    "errors": {
        "field_name": ["هذا الحقل مطلوب."]
    }
}
```

## Technical Details

### Files Modified

1. **`zthob/translations.py`** - Translation dictionary and utilities
2. **`zthob/utils.py`** - Updated `api_response()` function
3. **`zthob/middleware.py`** - Request context middleware
4. **`zthob/settings.py`** - Added middleware to MIDDLEWARE list

### Architecture

```
Request → Middleware (stores request) → View → api_response() 
    → Translation System → Translated Response
```

### Backward Compatibility

✅ **Fully backward compatible** - existing code works without changes  
✅ **Optional request parameter** - can still pass request explicitly  
✅ **Defaults to English** - if no language header, returns English  

## Testing

### Test with cURL

```bash
# Test English
curl -H "Accept-Language: en" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     http://mgask.net/api/tailors/analytics/

# Test Arabic
curl -H "Accept-Language: ar" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     http://mgask.net/api/tailors/analytics/
```

### Test in Python

```python
from django.test import RequestFactory
from zthob.utils import api_response

factory = RequestFactory()
request = factory.get('/api/test/')
request.META['HTTP_ACCEPT_LANGUAGE'] = 'ar'

response = api_response(
    success=True,
    message="Order created successfully",
    request=request
)
# Response will be in Arabic
```

## Troubleshooting

### Translations Not Working?

1. **Check middleware is enabled** in `settings.py`:
   ```python
   MIDDLEWARE = [
       ...
       "zthob.middleware.TranslationMiddleware",
   ]
   ```

2. **Check Accept-Language header** is being sent:
   ```bash
   curl -v -H "Accept-Language: ar" ...
   ```

3. **Check translation exists** in `zthob/translations.py`

4. **Restart Django** after adding new translations

### Message Not Translated?

If a message appears in English:
1. Check if it exists in `TRANSLATIONS` dictionary
2. Add it if missing
3. Restart Django

### Performance Issues?

The translation system is extremely fast (O(1) lookups). If you experience slowness:
- Check middleware order in settings
- Ensure no blocking operations in translation functions
- Monitor Django logs for errors

## Future Enhancements

Potential improvements:
- [ ] User language preference stored in database
- [ ] Admin panel for managing translations
- [ ] Support for more languages (French, Urdu, etc.)
- [ ] Translation caching for frequently used messages
- [ ] Dynamic translation loading (hot-reload)

## Support

For questions or issues:
1. Check this guide
2. Review `zthob/translations.py` for available translations
3. Check Django logs for errors
4. Contact development team


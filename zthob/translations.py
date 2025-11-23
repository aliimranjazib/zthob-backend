"""
Fast in-memory translation system for API responses.
Uses dictionary lookups for O(1) performance - no external calls or DB queries.
"""

# Translation dictionary: English -> Arabic
TRANSLATIONS = {
    # Success messages
    "OTP sent to {phone_number}": "تم إرسال رمز التحقق إلى {phone_number}",
    "Invalid phone number": "رقم الهاتف غير صحيح",
    "Invalid OTP format": "تنسيق رمز التحقق غير صحيح",
    "System settings retrieved successfully": "تم استرجاع إعدادات النظام بنجاح",
    "System settings updated successfully": "تم تحديث إعدادات النظام بنجاح",
    "Sliders retrieved successfully": "تم استرجاع الشرائح بنجاح",
    "Order retrieved successfully": "تم استرجاع الطلب بنجاح",
    "Order created successfully": "تم إنشاء الطلب بنجاح",
    "Order updated successfully": "تم تحديث الطلب بنجاح",
    "Order deleted successfully": "تم حذف الطلب بنجاح",
    "Tailor profile fetched": "تم جلب ملف الخياط",
    "Tailor profile updated successfully": "تم تحديث ملف الخياط بنجاح",
    "Fabric created successfully": "تم إنشاء القماش بنجاح",
    "Fabric updated successfully": "تم تحديث القماش بنجاح",
    "Fabric deleted successfully": "تم حذف القماش بنجاح",
    "Analytics data retrieved successfully": "تم استرجاع بيانات التحليلات بنجاح",
    "User registered successfully": "تم تسجيل المستخدم بنجاح",
    "Login successful": "تم تسجيل الدخول بنجاح",
    "User profile retrieved successfully": "تم استرجاع ملف المستخدم بنجاح",
    "Password changed successfully": "تم تغيير كلمة المرور بنجاح",
    "Operation completed successfully": "تمت العملية بنجاح",
    
    # Error messages
    "Authentication failed. Please provide a valid token.": "فشل المصادقة. يرجى تقديم رمز صحيح.",
    "Invalid or expired token": "رمز غير صحيح أو منتهي الصلاحية",
    "You do not have permission to perform this action.": "ليس لديك صلاحية لتنفيذ هذا الإجراء.",
    "The requested resource was not found.": "الموارد المطلوبة غير موجودة.",
    "Not found": "غير موجود",
    "An error occurred": "حدث خطأ",
    "Validation failed": "فشل التحقق",
    "The requested resource with ID {id} does not exist.": "الموارد المطلوبة بالمعرف {id} غير موجودة.",
    "Tailor with ID {id} does not exist. Please select a valid tailor.": "الخياط بالمعرف {id} غير موجود. يرجى اختيار خياط صحيح.",
    "Delivery address with ID {id} does not exist. Please select a valid address.": "عنوان التسليم بالمعرف {id} غير موجود. يرجى اختيار عنوان صحيح.",
    "Family member with ID {id} does not exist. Please select a valid family member.": "عضو العائلة بالمعرف {id} غير موجود. يرجى اختيار عضو عائلة صحيح.",
    "Fabric with ID {id} does not exist. Please select a valid fabric.": "القماش بالمعرف {id} غير موجود. يرجى اختيار قماش صحيح.",
    "Customer with ID {id} does not exist.": "العميل بالمعرف {id} غير موجود.",
    "Invalid credentials": "بيانات الاعتماد غير صحيحة",
    "User not found": "المستخدم غير موجود",
    "Phone number already verified": "تم التحقق من رقم الهاتف بالفعل",
    "Invalid OTP code": "رمز التحقق غير صحيح",
    "OTP expired": "انتهت صلاحية رمز التحقق",
    "OTP verification successful": "تم التحقق من رمز التحقق بنجاح",
    "You can only view your own orders": "يمكنك فقط عرض طلباتك الخاصة",
    "You can only view order that is assigned to you": "يمكنك فقط عرض الطلبات المخصصة لك",
    
    # Common field errors
    "This field is required.": "هذا الحقل مطلوب.",
    "This field may not be blank.": "لا يمكن أن يكون هذا الحقل فارغًا.",
    "Enter a valid email address.": "أدخل عنوان بريد إلكتروني صحيح.",
    "Enter a valid phone number.": "أدخل رقم هاتف صحيح.",
    "Ensure this value is less than or equal to {max_value}.": "تأكد من أن هذه القيمة أقل من أو تساوي {max_value}.",
    "Ensure this value is greater than or equal to {min_value}.": "تأكد من أن هذه القيمة أكبر من أو تساوي {min_value}.",
    "Invalid pk \"{pk}\" - object does not exist.": "معرف غير صحيح \"{pk}\" - الكائن غير موجود.",
    
    # Rider messages
    "Rider profile created successfully": "تم إنشاء ملف السائق بنجاح",
    "Rider profile updated successfully": "تم تحديث ملف السائق بنجاح",
    "Rider profile retrieved successfully": "تم استرجاع ملف السائق بنجاح",
    "Order accepted successfully": "تم قبول الطلب بنجاح",
    "Order rejected successfully": "تم رفض الطلب بنجاح",
    "Order completed successfully": "تم إكمال الطلب بنجاح",
    
    # Notification messages
    "Notification sent successfully": "تم إرسال الإشعار بنجاح",
    "Notifications retrieved successfully": "تم استرجاع الإشعارات بنجاح",
    
    # Generic fallbacks
    "Success": "نجاح",
    "Error": "خطأ",
    "Failed": "فشل",
}


def get_language_from_request(request):
    """
    Detect language from request headers.
    Checks Accept-Language header or falls back to 'en'.
    
    Args:
        request: Django/DRF request object
        
    Returns:
        str: Language code ('ar' for Arabic, 'en' for English)
    """
    if not request:
        return 'en'
    
    # Check Accept-Language header
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    
    # Parse Accept-Language header (e.g., "ar,en;q=0.9" or "ar-SA,ar;q=0.9")
    if accept_language:
        # Extract primary language (first 2 chars before comma or semicolon)
        primary_lang = accept_language.split(',')[0].split(';')[0].strip()[:2].lower()
        if primary_lang == 'ar':
            return 'ar'
    
    # Check if user has language preference (if you add this to user model later)
    # if hasattr(request, 'user') and request.user.is_authenticated:
    #     if hasattr(request.user, 'language_preference'):
    #         return request.user.language_preference
    
    return 'en'  # Default to English


def translate_message(message, language='en', **kwargs):
    """
    Translate a message to the specified language.
    Supports string formatting with kwargs.
    
    Args:
        message: English message string
        language: Target language code ('ar' or 'en')
        **kwargs: Formatting arguments for the message
        
    Returns:
        str: Translated message (or original if translation not found)
    """
    if not message or language == 'en':
        # Return original message if English or empty
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError):
                return message
        return message
    
    # Look up translation
    translated = TRANSLATIONS.get(message, None)
    
    if translated:
        # Apply formatting if kwargs provided
        if kwargs:
            try:
                return translated.format(**kwargs)
            except (KeyError, ValueError):
                # If formatting fails, return translated without formatting
                return translated
        return translated
    
    # If translation not found, try to format original message
    if kwargs:
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    # Return original message if no translation found
    return message


def translate_errors(errors, language='en'):
    """
    Translate error messages (supports dict, list, or string).
    
    Args:
        errors: Error object (dict, list, or string)
        language: Target language code ('ar' or 'en')
        
    Returns:
        Translated error object (same structure as input)
    """
    if not errors or language == 'en':
        return errors
    
    if isinstance(errors, str):
        return translate_message(errors, language)
    
    elif isinstance(errors, dict):
        translated_dict = {}
        for key, value in errors.items():
            if isinstance(value, list):
                # Translate each error in the list
                translated_dict[key] = [
                    translate_message(str(err), language) if isinstance(err, str) else err
                    for err in value
                ]
            elif isinstance(value, str):
                translated_dict[key] = translate_message(value, language)
            elif isinstance(value, dict):
                # Recursively translate nested dicts
                translated_dict[key] = translate_errors(value, language)
            else:
                translated_dict[key] = value
        return translated_dict
    
    elif isinstance(errors, list):
        return [
            translate_message(str(err), language) if isinstance(err, str) else err
            for err in errors
        ]
    
    return errors


def add_translation(message_key, arabic_translation):
    """
    Dynamically add a new translation at runtime.
    Useful for adding translations without code changes.
    
    Args:
        message_key: English message string
        arabic_translation: Arabic translation
    """
    TRANSLATIONS[message_key] = arabic_translation


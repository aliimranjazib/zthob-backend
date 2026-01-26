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
    
    # Order Status Actions - Labels
    "Accept Order": "قبول الطلب",
    "Mark In Progress": "تعيين قيد التنفيذ",
    "Mark Ready for Delivery": "تعيين جاهز للتسليم",
    "Mark Delivered": "تعيين تم التسليم",
    "Cancel Order": "إلغاء الطلب",
    "Start Pickup": "بدء الاستلام",
    "Mark Picked Up": "تعيين تم الاستلام",
    "Start Delivery": "بدء التسليم",
    "Start Measurement": "بدء القياس",
    "Complete Measurement": "إكمال القياس",
    "Start Stitching": "بدء الخياطة",
    "Finish Stitching": "إنهاء الخياطة",
    "Mark Collected": "تعيين تم الاستلام",
    "Mark Ready for Pickup": "تعيين جاهز للاستلام",
    "Taking Measurements": "أخذ القياسات",
    
    # Order Status Actions - Descriptions
    "Accept this order": "قبول هذا الطلب",
    "Start processing this order": "بدء معالجة هذا الطلب",
    "Order is ready for pickup/delivery": "الطلب جاهز للاستلام/التسليم",
    "Mark order as delivered": "تعيين الطلب كتم التسليم",
    "Mark order as collected": "تعيين الطلب كتم الاستلام",
    "Order is ready for customer pickup": "الطلب جاهز لاستلام العميل",
    "Cancel this order": "إلغاء هذا الطلب",
    "Accept this order for delivery": "قبول هذا الطلب للتسليم",
    "On way to pickup order from tailor": "في الطريق لاستلام الطلب من الخياط",
    "Order picked up from tailor": "تم استلام الطلب من الخياط",
    "On way to deliver order to customer": "في الطريق لتسليم الطلب للعميل",
    "On way to take customer measurements": "في الطريق لأخذ قياسات العميل",
    "Currently taking customer measurements": "أخذ قياسات العميل حالياً",
    "Measurements taken successfully": "تم أخذ القياسات بنجاح",
    "Order delivered to customer": "تم تسليم الطلب للعميل",
    "Mark order as in progress": "تعيين الطلب كقيد التنفيذ",
    "Start stitching the garment": "بدء خياطة الثوب",
    "Stitching completed": "اكتملت الخياطة",
    
    # Order Status Actions - Confirmation Messages
    "Are you sure you want to accept order?": "هل أنت متأكد أنك تريد قبول الطلب؟",
    "Are you sure you want to accept this order?": "هل أنت متأكد أنك تريد قبول هذا الطلب؟",
    "Are you sure you want to mark delivered?": "هل أنت متأكد أنك تريد تعيين تم التسليم؟",
    "Are you sure you want to cancel order?": "هل أنت متأكد أنك تريد إلغاء الطلب؟",
    
    # Cancel Reason Messages
    "Orders can only be cancelled when status is pending": "يمكن إلغاء الطلبات فقط عندما تكون الحالة معلقة",
    "Order is {status} and cannot be cancelled": "الطلب {status} ولا يمكن إلغاؤه",
    
    # Shop Status Messages
    "Shop is now ON": "المتجر الآن مفتوح",
    "Shop is now OFF": "المتجر الآن مغلق",
    "shop_status field is required": "حقل حالة المتجر مطلوب",
    "shop_status must be true or false": "يجب أن تكون حالة المتجر true أو false",
    "Profile not found": "الملف الشخصي غير موجود",
    
    # Generic fallbacks
    "Success": "نجاح",
    "Error": "خطأ",
    "Failed": "فشل",
    
    # Custom Style Categories
    "Collar Styles": "أنماط الياقة",
    "Cuff Styles": "أنماط الأكمام",
    "Placket Styles": "أنماط الفتحة",
    "Front Single Pocket": "جيب أمامي واحد",
    "Front Double Pocket": "جيب أمامي مزدوج",
    "Side Pocket": "جيب جانبي",
    "Button Colors": "ألوان الأزرار",
    "Yoke Styles": "أنماط النير",
    
    # Collar Styles
    "Standard": "عادي",
    "Mandarin": "ماندارين",
    "Square": "مربع",
    "Curved": "منحني",
    "Band": "شريط",
    "Club": "نادي",
    "Businessround": "دائري رسمي",
    "Cutaway": "مقصوص",
    "Modernbusiness": "رسمي حديث",
    "Business": "رسمي",
    "Bottomdown": "زر سفلي",
    "Longpoint": "طويل مدبب",
    "Narrowspread": "ضيق منتشر",
    "Simple": "بسيط",
    "Polo": "بولو",
    "Hoodie": "هودي",
    
    # Cuff Styles
    "Singlebutton": "زر واحد",
    "Simplekuwaiti": "كويتي بسيط",
    "Modern": "حديث",
    "Anglefrench": "فرنسي زاوية",
    "Link": "رابط",
    "Napolean": "نابليون",
    "Snap": "كبس",
    "Strap": "حزام",
    "Zip": "سحاب",
    "Urban": "حضري",
    "Triplebuttons": "ثلاثة أزرار",
    
    # Placket Styles
    "Standardhidden": "عادي مخفي",
    "Narrow": "ضيق",
    "Narrowhidden": "ضيق مخفي",
    "Reversehidden": "عكسي مخفي",
    "Hiddenzipsoft": "سحاب مخفي ناعم",
    "Hiddenbuttons": "أزرار مخفية",
    "Doublehole": "ثقب مزدوج",
    
    # Pocket Styles
    "1 Point": "مدبب",
    "2 Square": "مربع",
    "3 Round": "دائري",
    "4 Angle": "زاوية",
    "5 Inclined": "مائل",
    "6 Wallet": "محفظة",
    "7 Threelines": "ثلاثة خطوط",
    "8 Threelinesdiagonal": "ثلاثة خطوط قطرية",
    "Double 3Lines": "ثلاثة خطوط مزدوج",
    "Double 3Linesdiagonal": "ثلاثة خطوط قطرية مزدوج",
    "Double Angle": "زاوية مزدوج",
    "Double Inclined": "مائل مزدوج",
    "Double Point": "مدبب مزدوج",
    "Double Round": "دائري مزدوج",
    "Double Square": "مربع مزدوج",
    "Double Wallet": "محفظة مزدوج",
    "Leftside": "جانب أيسر",
    "Rightside": "جانب أيمن",
    "Doubleside": "جانب مزدوج",
    
    # Button Colors
    "Red": "أحمر",
    "Gray": "رمادي",
    "Grayish Brown": "بني رمادي",
    "Maroon": "عنابي",
    "Antiquegold": "ذهبي عتيق",
    "Deepgreen": "أخضر داكن",
    "White": "أبيض",
    "Black": "أسود",
    "Lavender": "لافندر",
    "Pink": "وردي",
    "Mint": "نعناع",
    "Rustybrown": "بني صدئ",
    "Orange": "برتقالي",
    "Skyblue": "أزرق سماوي",
    "Evergreen": "أخضر دائم",
    "Plumurple": "بنفسجي برقوقي",
    "Chromeblue": "أزرق كروم",
    
    # Yoke Styles
    "Back": "خلفي",
    
    # ========== NOTIFICATION MESSAGES ==========
    
    # Order Status Notifications
    "Your order #{order_number} has been placed successfully": "تم تقديم طلبك رقم #{order_number} بنجاح",
    "New order #{order_number} received from {customer_name}": "طلب جديد رقم #{order_number} من {customer_name}",
    "Tailor has accepted your order #{order_number}": "قبل الخياط طلبك رقم #{order_number}",
    "You have confirmed order #{order_number}": "لقد أكدت الطلب رقم #{order_number}",
    "Your order #{order_number} is now in progress": "طلبك رقم #{order_number} قيد التنفيذ الآن",
    "Order #{order_number} is now in progress": "الطلب رقم #{order_number} قيد التنفيذ الآن",
    "Rider is on the way to take your measurements for order #{order_number}": "السائق في الطريق لأخذ مقاساتك للطلب رقم #{order_number}",
    "Please take measurements for order #{order_number}": "يرجى أخذ المقاسات للطلب رقم #{order_number}",
    "Fabric cutting has started for your order #{order_number}": "بدأ قص القماش لطلبك رقم #{order_number}",
    "Order #{order_number} is ready for cutting": "الطلب رقم #{order_number} جاهز للقص",
    "Your garment is being stitched for order #{order_number}": "جاري خياطة ثوبك للطلب رقم #{order_number}",
    "Order #{order_number} is ready for stitching": "الطلب رقم #{order_number} جاهز للخياطة",
    "Your order #{order_number} is ready for delivery": "طلبك رقم #{order_number} جاهز للتوصيل",
    "Order #{order_number} is ready for pickup": "الطلب رقم #{order_number} جاهز للاستلام",
    "Order #{order_number} is ready for pickup from tailor": "الطلب رقم #{order_number} جاهز للاستلام من الخياط",
    "Your order #{order_number} is ready for pickup at the shop": "طلبك رقم #{order_number} جاهز للاستلام في المحل",
    "Order #{order_number} is ready for customer pickup": "الطلب رقم #{order_number} جاهز لاستلام العميل",
    "Your order #{order_number} has been delivered": "تم توصيل طلبك رقم #{order_number}",
    "Order #{order_number} has been delivered to customer": "تم توصيل الطلب رقم #{order_number} للعميل",
    "Order #{order_number} delivery completed": "تم إكمال توصيل الطلب رقم #{order_number}",
    "Thank you for collecting your order #{order_number}!": "شكراً لاستلامك طلبك رقم #{order_number}!",
    "Order #{order_number} has been collected by customer": "تم استلام الطلب رقم #{order_number} من قبل العميل",
    "Your order #{order_number} has been cancelled": "تم إلغاء طلبك رقم #{order_number}",
    "Order #{order_number} has been cancelled by customer": "تم إلغاء الطلب رقم #{order_number} من قبل العميل",
    "Order #{order_number} has been cancelled": "تم إلغاء الطلب رقم #{order_number}",
    "Order #{order_number} Update": "تحديث الطلب رقم #{order_number}",
    
    # Payment Notifications
    "Your order #{order_number} has been placed successfully! Payment of SAR {total_amount} confirmed.": "تم تقديم طلبك رقم #{order_number} بنجاح! تم تأكيد الدفع {total_amount} ريال",
    "New order #{order_number} received from {customer}. Payment of SAR {total_amount} confirmed.": "طلب جديد رقم #{order_number} من {customer}. تم تأكيد الدفع {total_amount} ريال",
    "Payment pending for order #{order_number}": "الدفع معلق للطلب رقم #{order_number}",
    "Refund of SAR {total_amount} has been processed for order #{order_number}": "تمت معالجة استرداد {total_amount} ريال للطلب رقم #{order_number}",
    "Refund issued for order #{order_number}": "تم إصدار استرداد للطلب رقم #{order_number}",
    "Payment Update": "تحديث الدفع",
    
    # Tailor Status Notifications
    "You have accepted order #{order_number}": "لقد قبلت الطلب رقم #{order_number}",
    "Order #{order_number} has been accepted by tailor and is ready for pickup": "تم قبول الطلب رقم #{order_number} من قبل الخياط وجاهز للاستلام",
    "Tailor is working on your order #{order_number}": "الخياط يعمل على طلبك رقم #{order_number}",
    "You have marked order #{order_number} as in progress": "لقد عينت الطلب رقم #{order_number} كقيد التنفيذ",
    "Tailor has started stitching your garment for order #{order_number}": "بدأ الخياط خياطة ثوبك للطلب رقم #{order_number}",
    "You have started stitching order #{order_number}": "لقد بدأت خياطة الطلب رقم #{order_number}",
    "Stitching has started for order #{order_number}": "بدأت الخياطة للطلب رقم #{order_number}",
    "Your garment stitching is complete for order #{order_number}": "اكتملت خياطة ثوبك للطلب رقم #{order_number}",
    "Stitching completed for order #{order_number}": "اكتملت الخياطة للطلب رقم #{order_number}",
    "Order #{order_number} stitching is complete and ready for pickup": "اكتملت خياطة الطلب رقم #{order_number} وجاهز للاستلام",
    "Your measurements have been completed for order #{order_number}. Your order is ready for pickup.": "تم إكمال قياساتك للطلب رقم #{order_number}. طلبك جاهز للاستلام",
    "Measurements completed for order #{order_number}. Order is ready for customer pickup.": "تم إكمال القياسات للطلب رقم #{order_number}. الطلب جاهز لاستلام العميل",
    
    # Rider Status Notifications
    "Rider has accepted your order #{order_number}": "قبل السائق طلبك رقم #{order_number}",
    "Rider has accepted order #{order_number}": "قبل السائق الطلب رقم #{order_number}",
    "Rider is on the way to customer for measurements - order #{order_number}": "السائق في الطريق للعميل لأخذ القياسات - الطلب رقم #{order_number}",
    "You are on the way to take measurements for order #{order_number}": "أنت في الطريق لأخذ القياسات للطلب رقم #{order_number}",
    "Rider is taking your measurements now for order #{order_number}": "السائق يأخذ قياساتك الآن للطلب رقم #{order_number}",
    "Rider is currently taking customer measurements - order #{order_number}": "السائق يأخذ قياسات العميل حالياً - الطلب رقم #{order_number}",
    "Measurements in progress for order #{order_number}": "القياسات قيد التنفيذ للطلب رقم #{order_number}",
    "Your measurements have been completed for order #{order_number}": "تم إكمال قياساتك للطلب رقم #{order_number}",
    "Your measurements have been completed for order #{order_number}. Tailor will now start stitching.": "تم إكمال قياساتك للطلب رقم #{order_number}. سيبدأ الخياط الخياطة الآن",
    "Measurements ready for order #{order_number}": "القياسات جاهزة للطلب رقم #{order_number}",
    "Measurements ready for order #{order_number}. You can now start stitching.": "القياسات جاهزة للطلب رقم #{order_number}. يمكنك الآن بدء الخياطة",
    "Measurements successfully recorded for order #{order_number}": "تم تسجيل القياسات بنجاح للطلب رقم #{order_number}",
    "Measurements successfully recorded for order #{order_number}. Waiting for tailor to complete stitching.": "تم تسجيل القياسات بنجاح للطلب رقم #{order_number}. في انتظار الخياط لإكمال الخياطة",
    "Rider is on the way to pickup your order #{order_number} from tailor": "السائق في الطريق لاستلام طلبك رقم #{order_number} من الخياط",
    "Rider is on the way to pickup order #{order_number}": "السائق في الطريق لاستلام الطلب رقم #{order_number}",
    "You are on the way to pickup order #{order_number} from tailor": "أنت في الطريق لاستلام الطلب رقم #{order_number} من الخياط",
    "Rider has picked up your order #{order_number} and is preparing for delivery": "استلم السائق طلبك رقم #{order_number} ويستعد للتوصيل",
    "Rider has picked up order #{order_number}": "استلم السائق الطلب رقم #{order_number}",
    "You have picked up order #{order_number} from tailor": "لقد استلمت الطلب رقم #{order_number} من الخياط",
    "Your order #{order_number} is on the way! Rider will arrive soon.": "طلبك رقم #{order_number} في الطريق! سيصل السائق قريباً",
    "Order #{order_number} is now out for delivery": "الطلب رقم #{order_number} الآن في طريقه للتوصيل",
    "You are delivering order #{order_number} to customer": "أنت توصل الطلب رقم #{order_number} للعميل",
    
    # Notification Titles
    "Measurements Taken": "تم أخذ القياسات",
    "Measurements Ready": "القياسات جاهزة",
    "Measurements Recorded": "تم تسجيل القياسات",
    
    # Test Notifications
    "Test Notification": "إشعار تجريبي",
    "Hello {username}! This is a test notification from Zthob.": "مرحباً {username}! هذا إشعار تجريبي من ثوب.",
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




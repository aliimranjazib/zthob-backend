"""
Fast in-memory translation system for API responses.
Uses dictionary lookups for O(1) performance - no external calls or DB queries.
"""

from zthob.languages import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, TRANSLATABLE_LANGUAGES
from zthob.translations_ur import TRANSLATIONS_UR

# Translation dictionary: English -> Arabic
TRANSLATIONS_AR = {
    # Success messages
    "OTP sent to {phone_number}": "تم إرسال رمز التحقق إلى {phone_number}",
    "OTP resent to {phone_number}": "تم إعادة إرسال رمز التحقق إلى {phone_number}",
    "Failed to send OTP to {phone_number}": "فشل إرسال رمز التحقق إلى {phone_number}",
    "Failed to send OTP": "فشل إرسال رمز التحقق",
    "Failed to resend OTP": "فشل إعادة إرسال رمز التحقق",
    "OTP generated for {phone_number}, but SMS sending failed. Please check server logs.": "تم إنشاء رمز التحقق لـ {phone_number}، لكن فشل إرسال الرسالة. يرجى مراجعة سجلات الخادم.",
    "Registration and login successful": "تم التسجيل وتسجيل الدخول بنجاح",
    "OTP verification failed": "فشل التحقق من رمز التحقق",
    "Verification failed": "فشل التحقق",
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
    "Profile fetched successfully": "تم جلب الملف الشخصي بنجاح",
    "Profile updated successfully": "تم تحديث الملف الشخصي بنجاح",
    "Profile update failed": "فشل تحديث الملف الشخصي",
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
    "Invalid verification code": "رمز التحقق غير صحيح",
    "OTP expired": "انتهت صلاحية رمز التحقق",
    "Code expired. Request a new one": "انتهت صلاحية الرمز. اطلب رمزاً جديداً",
    "No active verification. Request a new code": "لا يوجد تحقق نشط. اطلب رمزاً جديداً",
    "Too many attempts. Try again later": "محاولات كثيرة جداً. حاول مرة أخرى لاحقاً",
    "Please wait before requesting another code": "يرجى الانتظار قبل طلب رمز آخر",
    "Too many requests for this number": "طلبات كثيرة جداً لهذا الرقم",
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
    "Notification marked as read": "تم تعيين الإشعار كمقروء",
    "Notification not found": "الإشعار غير موجود",
    "All notifications marked as read": "تم تعيين جميع الإشعارات كمقروءة",
    "Test Notification": "إشعار تجريبي",
    "Test notification sent successfully": "تم إرسال الإشعار التجريبي بنجاح",
    "Failed to send test notification. Check your FCM token.": "فشل إرسال الإشعار التجريبي. تحقق من رمز FCM.",
    "This endpoint is only for customers": "هذا المسار مخصص للعملاء فقط",
    "This endpoint is only for tailors": "هذا المسار مخصص للخياطين فقط",
    "This endpoint is only for riders": "هذا المسار مخصص للسائقين فقط",
    "FCM token registered successfully": "تم تسجيل رمز FCM بنجاح",
    "Order #{order_number} Update": "تحديث الطلب رقم {order_number}",
    "Payment Update": "تحديث الدفع",
    "Rider Assigned": "تم تعيين السائق",
    "New Order Assignment": "تعيين طلب جديد",
    "Measurements Taken": "تم أخذ المقاسات",
    "Measurements Ready": "المقاسات جاهزة",
    "Measurements Recorded": "تم تسجيل المقاسات",
    "Payout Approved": "تمت الموافقة على طلب السحب",
    "Payout Rejected": "تم رفض طلب السحب",
    "Payout Processed": "تمت معالجة طلب السحب",
    "New order #{order_number} assigned to you": "تم تعيين طلب جديد رقم {order_number} لك",
    "New available order #{order_number}": "طلب جديد متاح رقم {order_number}",
    "New order #{order_number} received from {customer_name}": "تم استلام طلب جديد رقم {order_number} من {customer_name}",
    "Your order #{order_number} has been confirmed and is being prepared.": "تم تأكيد طلبك رقم {order_number} وجار تجهيزه.",
    "You have accepted order #{order_number}.": "لقد قبلت الطلب رقم {order_number}.",
    "Order #{order_number} has been accepted and is being prepared by the tailor.": "تم قبول الطلب رقم {order_number} وجار تجهيزه من قبل الخياط.",
    "Your order #{order_number} is now in progress": "طلبك رقم {order_number} قيد التنفيذ الآن",
    "Order #{order_number} is now in progress": "الطلب رقم {order_number} قيد التنفيذ الآن",
    "Rider is on the way to take your measurements for order #{order_number}": "السائق في الطريق لأخذ مقاساتك للطلب رقم {order_number}",
    "Please take measurements for order #{order_number}": "يرجى أخذ المقاسات للطلب رقم {order_number}",
    "Fabric cutting has started for your order #{order_number}": "بدأ قص القماش لطلبك رقم {order_number}",
    "Order #{order_number} is ready for cutting": "الطلب رقم {order_number} جاهز للقص",
    "Your garment is being stitched for order #{order_number}": "تتم خياطة ثوبك للطلب رقم {order_number}",
    "Order #{order_number} is ready for stitching": "الطلب رقم {order_number} جاهز للخياطة",
    "Your order #{order_number} is ready for delivery": "طلبك رقم {order_number} جاهز للتوصيل",
    "Order #{order_number} is ready for pickup": "الطلب رقم {order_number} جاهز للاستلام",
    "Order #{order_number} is ready for pickup from tailor": "الطلب رقم {order_number} جاهز للاستلام من الخياط",
    "Your order #{order_number} is ready for pickup at the shop": "طلبك رقم {order_number} جاهز للاستلام من المتجر",
    "Order #{order_number} is ready for customer pickup": "الطلب رقم {order_number} جاهز لاستلام العميل",
    "Your order #{order_number} has been delivered": "تم تسليم طلبك رقم {order_number}",
    "Order #{order_number} has been delivered to customer": "تم تسليم الطلب رقم {order_number} إلى العميل",
    "Order #{order_number} delivery completed": "اكتمل توصيل الطلب رقم {order_number}",
    "Thank you for collecting your order #{order_number}!": "شكراً لاستلام طلبك رقم {order_number}!",
    "Order #{order_number} has been collected by customer": "تم استلام الطلب رقم {order_number} من قبل العميل",
    "Your order #{order_number} has been cancelled": "تم إلغاء طلبك رقم {order_number}",
    "Order #{order_number} has been cancelled by customer": "تم إلغاء الطلب رقم {order_number} من قبل العميل",
    "Order #{order_number} has been cancelled": "تم إلغاء الطلب رقم {order_number}",
    "Order #{order_number} Rejected": "تم رفض الطلب رقم {order_number}",
    "Your order #{order_number} was declined by the tailor. Reason: {rejection_reason}": "تم رفض طلبك رقم {order_number} من قبل الخياط. السبب: {rejection_reason}",
    "You rejected order #{order_number} from {customer_name}. Reason: {rejection_reason}": "لقد رفضت الطلب رقم {order_number} من {customer_name}. السبب: {rejection_reason}",
    "Only Cash on Delivery (COD) orders can be rejected. Paid online orders require a refund process.": "يمكن رفض طلبات الدفع عند الاستلام فقط. الطلبات المدفوعة عبر الإنترنت تتطلب عملية استرداد.",
    "Cannot reject an order where payment has already been collected.": "لا يمكن رفض طلب تم تحصيل دفعه بالفعل.",
    "Only pending orders can be rejected.": "يمكن رفض الطلبات المعلقة فقط.",
    "Cannot reject an order that is already accepted.": "لا يمكن رفض طلب تم قبوله بالفعل.",
    "You cannot reject this order.": "لا يمكنك رفض هذا الطلب.",
    "A rejection reason is required.": "سبب الرفض مطلوب.",
    "Invalid rejection reason code.": "رمز سبب الرفض غير صالح.",
    "Please provide details for the rejection reason (min 10 characters).": "يرجى تقديم تفاصيل سبب الرفض (10 أحرف على الأقل).",
    "Rejection reason is required (min 10 characters).": "سبب الرفض مطلوب (10 أحرف على الأقل).",
    "Shop is at full capacity": "المتجر ممتلئ بالطلبات حالياً",
    "Cannot meet the requested delivery date": "لا يمكن الالتزام بموعد التسليم المطلوب",
    "Required fabric is not available": "القماش المطلوب غير متوفر",
    "Service is not available at the moment": "الخدمة غير متاحة حالياً",
    "Customer request cannot be fulfilled": "لا يمكن تنفيذ طلب العميل",
    "Other reason": "سبب آخر",
    "Reject Order": "رفض الطلب",
    "Tailor has accepted your order #{order_number}.": "قبل الخياط طلبك رقم {order_number}.",
    "Order #{order_number} has been accepted by the tailor and is being prepared.": "تم قبول الطلب رقم {order_number} من قبل الخياط وجار تجهيزه.",
    "Tailor is working on your order #{order_number}": "الخياط يعمل على طلبك رقم {order_number}",
    "You have marked order #{order_number} as in progress": "لقد عينت الطلب رقم {order_number} كقيد التنفيذ",
    "Tailor has started stitching your garment for order #{order_number}": "بدأ الخياط خياطة ثوبك للطلب رقم {order_number}",
    "You have started stitching order #{order_number}": "لقد بدأت خياطة الطلب رقم {order_number}",
    "Stitching has started for order #{order_number}": "بدأت الخياطة للطلب رقم {order_number}",
    "Your garment stitching is complete for order #{order_number}": "اكتملت خياطة ثوبك للطلب رقم {order_number}",
    "Stitching completed for order #{order_number}": "اكتملت الخياطة للطلب رقم {order_number}",
    "Order #{order_number} stitching is complete and ready for pickup": "اكتملت خياطة الطلب رقم {order_number} وهو جاهز للاستلام",
    "Your measurements have been completed for order #{order_number}. Your order is ready for pickup.": "اكتملت مقاساتك للطلب رقم {order_number}. طلبك جاهز للاستلام.",
    "Measurements completed for order #{order_number}. Order is ready for customer pickup.": "اكتملت المقاسات للطلب رقم {order_number}. الطلب جاهز لاستلام العميل.",
    "Rider has accepted order #{order_number} and will handle the task": "قبل السائق الطلب رقم {order_number} وسيتولى المهمة",
    "Rider is taking your measurements now for order #{order_number}": "السائق يأخذ مقاساتك الآن للطلب رقم {order_number}",
    "Your measurements have been completed for order #{order_number}": "اكتملت مقاساتك للطلب رقم {order_number}",
    "Your measurements have been completed. Tailor will now start stitching.": "اكتملت مقاساتك. سيبدأ الخياط الخياطة الآن.",
    "Measurements ready for order #{order_number}. You can now start stitching.": "المقاسات جاهزة للطلب رقم {order_number}. يمكنك بدء الخياطة الآن.",
    "Rider is on the way to pickup order #{order_number}": "السائق في الطريق لاستلام الطلب رقم {order_number}",
    "Rider has picked up your order #{order_number} and is preparing for delivery": "استلم السائق طلبك رقم {order_number} ويستعد للتوصيل",
    "Your order #{order_number} is on the way! Rider will arrive soon.": "طلبك رقم {order_number} في الطريق! سيصل السائق قريباً.",
    "Your order #{order_number} has been delivered successfully": "تم تسليم طلبك رقم {order_number} بنجاح",
    "Your order #{order_number} has been placed successfully! Payment of SAR {total_amount} confirmed.": "تم إنشاء طلبك رقم {order_number} بنجاح! تم تأكيد دفع {total_amount} ريال.",
    "New order #{order_number} received from {customer}. Payment of SAR {total_amount} confirmed.": "تم استلام طلب جديد رقم {order_number} من {customer}. تم تأكيد دفع {total_amount} ريال.",
    "Payment pending for order #{order_number}": "الدفع معلق للطلب رقم {order_number}",
    "Refund of SAR {total_amount} has been processed for order #{order_number}": "تمت معالجة استرداد {total_amount} ريال للطلب رقم {order_number}",
    "Refund issued for order #{order_number}": "تم إصدار استرداد للطلب رقم {order_number}",
    "Rider {rider_name} has been assigned to deliver your order #{order_number}": "تم تعيين السائق {rider_name} لتوصيل طلبك رقم {order_number}",
    "Rider {rider_name} will pick up order #{order_number}": "سيستلم السائق {rider_name} الطلب رقم {order_number}",
    "You have been assigned to order #{order_number}": "تم تعيينك للطلب رقم {order_number}",
    "Your measurements have been completed for order #{order_number}. Thank you!": "اكتملت مقاساتك للطلب رقم {order_number}. شكراً لك!",
    "Measurements have been taken for your order #{order_number}. Tailor will now start stitching.": "تم أخذ مقاسات طلبك رقم {order_number}. سيبدأ الخياط الخياطة الآن.",
    "Measurements have been completed for order #{order_number}.": "اكتملت المقاسات للطلب رقم {order_number}.",
    "Measurements have been taken for order #{order_number}. You can now start stitching.": "تم أخذ المقاسات للطلب رقم {order_number}. يمكنك بدء الخياطة الآن.",
    "Measurements successfully recorded for order #{order_number}": "تم تسجيل المقاسات بنجاح للطلب رقم {order_number}",
    "Your payout request of SAR {amount} has been approved and is being processed": "تمت الموافقة على طلب السحب بقيمة {amount} ريال وجار معالجته",
    "Your payout request of SAR {amount} has been rejected": "تم رفض طلب السحب بقيمة {amount} ريال",
    "Your payout request of SAR {amount} has been processed": "تمت معالجة طلب السحب بقيمة {amount} ريال",
    "You have been specifically assigned to this order by the tailor": "تم تعيينك خصيصاً لهذا الطلب من قبل الخياط",
    "A new order is available for pickup. Check your available orders list.": "يوجد طلب جديد متاح للاستلام. تحقق من قائمة الطلبات المتاحة.",
    
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
    "Mark Ready": "تعيين جاهز",
    "Pickup Order": "استلام الطلب",
    "Collect Order": "تحصيل الطلب",
    "Collect Remaining Payment": "تحصيل المبلغ المتبقي",
    "Record Measurements": "تسجيل القياسات",
    "Start Measuring": "بدء القياس",
    "Mark Collected": "تعيين تم الاستلام",
    "Mark Ready for Pickup": "تعيين جاهز للاستلام",
    "Taking Measurements": "أخذ القياسات",
    
    # Order/Tailor Statuses
    "New": "جديد",
    "Accepted Order": "تم قبول الطلب",
    "In Progress": "قيد التنفيذ",
    "Started Stitching": "بدأ الخياطة",
    "Finished Stitching": "تمت الخياطة",
    "Measurements Complete": "اكتملت المقاسات",
    "Ready for Delivery": "جاهز للتوصيل",
    
    # Rider Statuses
    "On Way to Pickup": "في الطريق للاستلام",
    "Picked Up": "تم الاستلام من الخياط",
    "On Way to Delivery": "في الطريق للتوصيل",
    "On Way to Measurement": "في الطريق لأخذ القياسات",
    "Measuring": "جاري أخذ القياسات",
    "Measurement Taken": "تم أخذ القياسات",
    
    # Main Order Statuses
    "Pending": "معلق",
    "Confirmed": "مؤكد",
    "Ready for Pickup": "جاهز للاستلام",
    "Delivered": "تم التوصيل",
    "Collected": "تم الاستلام",
    "Cancelled": "ملغي",
    
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
    "New available order #{order_number}": "طلب جديد متاح #{order_number}",
    "A new order is available for pickup. Check your available orders list.": "طلب جديد متاح للاستلام. تحقق من قائمة الطلبات المتاحة.",
    
    "Measurements Taken": "تم أخذ القياسات",
    "Measurements Ready": "القياسات جاهزة",
    "Measurements Recorded": "تم تسجيل القياسات",
    
    # Test Notifications
    "Test Notification": "إشعار تجريبي",
    "Hello {username}! This is a test notification from Zthob.": "مرحباً {username}! هذا إشعار تجريبي من ثوب.",
    
    # Payout Notifications
    "Payout Processed": "تمت معالجة الدفع",
    "Your payout request of SAR {amount} has been processed": "تمت معالجة طلب الدفع الخاص بك بمبلغ {amount} ريال",
    "Payout Approved": "تمت الموافقة على طلب الدفع",
    "Your payout request of SAR {amount} has been approved and is being processed": "تمت الموافقة على طلب الدفع الخاص بك بمبلغ {amount} ريال وجاري المعالجة",
    "Payout Rejected": "تم رفض طلب الدفع",
    "Your payout request of SAR {amount} has been rejected": "تم رفض طلب الدفع الخاص بك بمبلغ {amount} ريال",

    # ========== EMPLOYEE ROLES ==========
    "Manager": "مدير",
    "Manages the shop on behalf of the owner. Has access to orders, catalog, and staff.": "يدير المحل نيابةً عن المالك. لديه صلاحية الوصول إلى الطلبات والكتالوج والموظفين.",
    "Stitcher": "خياط",
    "Responsible for stitching garments. Can view and update assigned orders.": "مسؤول عن خياطة الملابس. يمكنه عرض وتحديث الطلبات المُسندة إليه.",
    "Cutter": "قاطع",
    "Responsible for cutting fabric. Can view catalog and assigned orders.": "مسؤول عن قص الأقمشة. يمكنه عرض الكتالوج والطلبات المُسندة إليه.",
    "Receptionist": "موظف استقبال",
    "Handles customer interactions and POS. Can manage orders and customers.": "يتعامل مع العملاء ونقطة البيع. يمكنه إدارة الطلبات والعملاء.",
    "Finisher": "مشطّب",
    "Handles final touches and quality checks before delivery.": "مسؤول عن اللمسات الأخيرة وفحص الجودة قبل التسليم.",

    # ========== EMPLOYEE PERMISSIONS ==========
    "Manage Orders": "إدارة الطلبات",
    "Can view, accept, and update order statuses.": "يمكنه عرض الطلبات وقبولها وتحديث حالاتها.",
    "Manage Catalog": "إدارة الكتالوج",
    "Can add, edit, and delete fabrics and categories.": "يمكنه إضافة الأقمشة والتصنيفات وتعديلها وحذفها.",
    "View Analytics": "عرض الإحصائيات",
    "Can view shop performance reports and statistics.": "يمكنه عرض تقارير وإحصائيات أداء المحل.",
    "Manage Employees": "إدارة الموظفين",
    "Can add, edit, and remove other employees. Only grant to trusted staff.": "يمكنه إضافة الموظفين وتعديلهم وإزالتهم. امنح هذه الصلاحية للموظفين الموثوقين فقط.",
    "Manage POS & Customers": "إدارة نقطة البيع والعملاء",
    "Can use the point-of-sale system and manage customer records.": "يمكنه استخدام نظام نقطة البيع وإدارة سجلات العملاء.",

    # ========== EMPLOYEE MANAGEMENT MESSAGES ==========
    "Employees retrieved successfully": "تم استرجاع الموظفين بنجاح",
    "Employee retrieved successfully": "تم استرجاع الموظف بنجاح",
    "Employee added successfully": "تم إضافة الموظف بنجاح",
    "Employee updated successfully": "تم تحديث الموظف بنجاح",
    "Employee removed successfully": "تم إزالة الموظف بنجاح",
    "Failed to add employee": "فشل إضافة الموظف",
    "Employee not found": "الموظف غير موجود",
    "This phone number is already an employee at another shop": "رقم الهاتف هذا مسجل موظفاً في محل آخر",
    "Tailor profile not found": "ملف الخياط غير موجود",
    
    # Express Delivery
    "Day": "يوم",
    "Days": "أيام",

    # Tailor Dashboard Home
    "Today's Revenue": "إيرادات اليوم",
    "Weekly Revenue": "الإيرادات الأسبوعية",
    "Overdue": "متأخر",
    "{count} Overdue": "{count} متأخر",
    "Due Today ({count})": "استحقاق اليوم ({count})",
    "Due this Week ({count})": "استحقاق هذا الأسبوع ({count})",
    "New Requests": "طلبات جديدة",
    "Accept new delivery orders": "قبول طلبات التوصيل الجديدة",
    "Make Progress": "متابعة التنفيذ",
    "Ready for processing": "جاهز للمعالجة",
    "Stitching": "جاري الخياطة",
    "Sewing and finishing": "خياطة وتشطيب",
    "Ready for Rider": "جاهز للسائق",
    "Waiting for rider handover": "في انتظار تسليم السائق",
    "New Shop Orders": "طلبات متجر جديدة",
    "Accept walk-in customers": "قبول زبائن المتجر",
    "To Measure": "للقياس",
    "Record shop measurements": "تسجيل مقاسات المتجر",
    "Shop orders being sewn": "طلبات المتجر قيد الخياطة",
    "Ready for Customer": "جاهز للزبون",
    "Waiting for shop collection": "في انتظار استلام الزبون",
    "Waiting for Acceptance": "في انتظار القبول",
    "Stitching": "جاري الخياطة",
    "New orders waiting for your approval": "طلبات جديدة في انتظار موافقتك",
    "Orders currently being worked on": "طلبات قيد العمل حالياً",
    "Orders ready for customer pickup": "طلبات جاهزة لاستلام العملاء",
    "Tailor Plus is required for this action.": "يتطلب خياط بلس لهذا الإجراء.",
    "Free shops can list up to 30 owner-catalog fabrics. Tailor Plus unlocks unlimited fabrics for this shop.": "يمكن للمتجر المجاني إدراج حتى 30 قماشاً من قائمة أقمشة المالك على هذا الفرع. خياط بلس يتيح عدداً غير محدوداً.",
    "Free shops can add up to 30 shop-created fabrics. Tailor Plus unlocks unlimited fabrics for this shop.": "المتاجر المجانية يمكنها إضافة حتى 30 قماشاً من المتجر. خياط بلس يفتح عدداً غير محدود لهذا المتجر.",
    "Tailor Plus is required for analytics longer than 7 days.": "يتطلب خياط بلس للتحليلات لأكثر من 7 أيام.",
    "Tailor Plus is required for this report period on this shop.": "يتطلب خياط بلس لفترة التقرير هذه على هذا المتجر.",
    "Tailor Plus is required for report date ranges longer than 7 days.": "يتطلب خياط بلس لفترات التقرير أطول من 7 أيام.",
    "Reusable shop measurements loaded": "تم تحميل مقاسات المتجر القابلة لإعادة الاستخدام",
    "Shop measurement template loaded": "تم تحميل قالب مقاسات المتجر",
    "Shop measurement template saved": "تم حفظ قالب مقاسات المتجر",
    "Shop measurement template reset to platform default": "تمت إعادة قالب مقاسات المتجر إلى الافتراضي",
    "Tailor Plus is required to customize measurement fields for this shop.": "يتطلب خياط بلس لتخصيص حقول المقاسات لهذا المتجر.",
    "Measurement template not configured": "قالب المقاسات غير مهيأ",
    "Tailor Plus": "خياط بلس",
    "Owner Plus": "مالك بلس",
    "Upgrade to {plan}": "الترقية إلى {plan}",
    "Shop plans": "خطط المتجر",
    "Tap a plan to see what's included": "اضغط على خطة لمعرفة ما يشمله",
    "Compare plans and see what's included": "قارن الخطط واطّلع على ما يشمله كل منها",
    "What's included": "ما الذي يشمله",
    "Current": "الحالي",
    "Recommended": "موصى به",
    "Free plan": "الخطة المجانية",
    "Add up to {limit} fabrics in the shop": "إضافة حتى {limit} قماشاً في المتجر",
    "Shop fabric catalog: up to {limit} fabrics you add": "قائمة أقمشة المتجر: حتى {limit} قماش تضيفها",
    "Owner can assign up to {limit} fabrics to the shop": "يمكن للمالك تعيين حتى {limit} قماشاً للمتجر",
    "Owner-assigned catalog fabrics: up to {limit} per shop": "أقمشة قائمة المالك: حتى {limit} لكل متجر",
    "Fabric inventory and stock tracking — Tailor Plus": "مخزون الأقمشة وتتبّع المخزون — خياط بلس",
    "Earnings analytics for {days_list} only": "تحليلات الأرباح لـ {days_list} فقط",
    "Earnings analytics: {days_list} only": "تحليلات الأرباح: {days_list} فقط",
    "Owner reports: today, yesterday, or custom range up to {max_days} days (per branch)": "تقارير المالك: اليوم، أمس، أو نطاق مخصص حتى {max_days} يوماً (لكل فرع)",
    "Branch reports: today, yesterday, or up to {max_days} days custom": "تقارير الفرع: اليوم، أمس، أو نطاق مخصص حتى {max_days} يوم",
    "Walk-in measurements saved in customer app history": "مقاسات الزيارة محفوظة في سجل تطبيق العميل",
    "Walk-in measurements saved in the customer app": "مقاسات الزيارة محفوظة في تطبيق العميل",
    "Customize App Theme": "تخصيص مظهر التطبيق",
    "Add unlimited fabrics in the shop": "إضافة عدد غير محدود من الأقمشة في المتجر",
    "Fabric inventory: stock, sales, movements, and shop insights": "مخزون الأقمشة: المخزون والمبيعات والحركات ورؤى المتجر",
    "Unlimited shop-added fabrics": "أقمشة غير محدودة يضيفها المتجر",
    "Owner can assign unlimited fabrics to the shop": "يمكن للمالك تعيين عدد غير محدود من الأقمشة للمتجر",
    "Unlimited owner-assigned fabrics per shop": "أقمشة غير محدودة من المالك لكل متجر",
    "Custom measurement fields for your shop": "حقول مقاسات مخصصة لمتجرك",
    "Earnings analytics for {days_list}": "تحليلات الأرباح لـ {days_list}",
    "Full earnings analytics: {days_list}": "تحليلات أرباح كاملة: {days_list}",
    "All owner report periods for each branch": "جميع فترات تقارير المالك لكل فرع",
    "All report periods for every branch": "جميع فترات التقارير لكل فرع",
    "Customers can reuse walk-in measurements at Plus shops (faster re-orders)": "يمكن للعملاء إعادة استخدام مقاسات الزيارة في متاجر خياط بلس (طلبات أسرع)",
    "Customers can reuse walk-in measurements (faster re-orders)": "يمكن للعملاء إعادة استخدام مقاسات الزيارة (طلبات أسرع)",
    "Fast payout processing for eligible wallet settlements": "معالجة سريعة للمدفوعات لتسويات المحفظة المؤهلة",
    "Customize App Theme": "تخصيص مظهر التطبيق",
    "Priority fabric review and operational support": "أولوية مراجعة الأقمشة والدعم التشغيلي",
    "Priority fabric review and support": "أولوية مراجعة الأقمشة والدعم",
    "Business plans": "خطط الأعمال",
    "Free business plan": "الخطة المجانية للأعمال",
    "Up to {max_shops} shop branches": "حتى {max_shops} فروع للمتجر",
    "Up to {max_staff} employees on your roster": "حتى {max_staff} موظفين في قائمتك",
    "Up to {max_staff} employees": "حتى {max_staff} موظفين",
    "Up to {catalog_limit} fabrics in your business catalog": "حتى {catalog_limit} قماشاً في قائمة أقمشة أعمالك",
    "Business fabric catalog: up to {catalog_limit} products": "قائمة أقمشة الأعمال: حتى {catalog_limit} منتجاً",
    "Fabric inventory and business-wide stock insights — Owner Plus": "مخزون الأقمشة ورؤى المخزون على مستوى الأعمال — مالك بلس",
    "Each branch: up to {shop_limit} fabrics per shop (see Shop plans)": "كل فرع: حتى {shop_limit} قماشاً لكل متجر (انظر خطط المتجر)",
    "Business dashboard reports for {days_list}-day views": "تقارير لوحة الأعمال لعروض {days_list} يوم",
    "Dashboard reports: {days_list}-day views only": "تقارير لوحة التحكم: عروض {days_list} يوم فقط",
    "Each branch uses the free shop plan unless you upgrade with Tailor Plus": "كل فرع يستخدم الخطة المجانية للمتجر ما لم تترقّ إلى خياط بلس",
    "Branches use the free shop plan unless you add Tailor Plus per branch": "الفروع تستخدم الخطة المجانية للمتجر ما لم تضف خياط بلس لكل فرع",
    "Unlimited shop branches": "فروع متجر غير محدودة",
    "Unlimited employees": "موظفون غير محدودون",
    "Unlimited fabrics in your business catalog": "أقمشة غير محدودة في قائمة أقمشة أعمالك",
    "Tailor Plus on every branch you own — unlimited fabrics per shop, full analytics and report periods, custom measurement fields, walk-in measurement reuse": "خياط بلس على كل فرع تملكه — أقمشة غير محدودة لكل متجر، تحليلات وفترات تقارير كاملة، حقول مقاسات مخصصة، إعادة استخدام مقاسات الزيارة",
    "Tailor Plus on every branch you own (full shop benefits without separate upgrades)": "خياط بلس على كل فرع تملكه (مزايا المتجر الكاملة دون ترقيات منفصلة)",
    "Fabric inventory: stock, movements, and owner-level fabric insights": "مخزون الأقمشة: المخزون والحركات ورؤى الأقمشة على مستوى المالك",
    "Full business reports on all branches (all standard periods)": "تقارير أعمال كاملة على جميع الفروع (جميع الفترات القياسية)",
    "Full dashboard reports on all branches": "تقارير لوحة تحكم كاملة على جميع الفروع",
    "Priority support and faster fabric review": "دعم ذو أولوية ومراجعة أسرع للأقمشة",
    "Free business accounts can have up to {max} shop branches. Owner Plus unlocks unlimited branches.": "يمكن للحسابات المجانية حتى {max} فروع. مالك بلس يفتح فروعاً غير محدودة.",
    "Free business accounts can have up to {max} employees. Owner Plus unlocks unlimited staff.": "يمكن للحسابات المجانية حتى {max} موظفين. مالك بلس يفتح موظفين غير محدودين.",
    "Free business accounts can create up to {max} fabrics in the business catalog. Owner Plus unlocks unlimited fabrics.": "يمكن للحسابات المجانية إنشاء حتى {max} قماشاً في قائمة أقمشة الأعمال. مالك بلس يفتح أقمشة غير محدودة.",
    "Owner Plus is required for this report period on the business dashboard.": "يتطلب مالك بلس لفترة التقرير هذه على لوحة الأعمال.",
    "Free business accounts can view dashboard reports for 1-day or 7-day ranges only. Owner Plus unlocks all report periods.": "يمكن للحسابات المجانية عرض تقارير لوحة 1 أو 7 أيام فقط. مالك بلس يفتح جميع فترات التقارير.",
    "Owner Plus is required for this action.": "يتطلب مالك بلس لهذا الإجراء.",
    "Free business accounts can have up to 3 shop branches. Owner Plus unlocks unlimited branches.": "يمكن للحسابات المجانية حتى 3 فروع. مالك بلس يفتح فروعاً غير محدودة.",
    "Free business accounts can have up to 3 employees. Owner Plus unlocks unlimited staff.": "يمكن للحسابات المجانية حتى 3 موظفين. مالك بلس يفتح موظفين غير محدودين.",
    "Free business accounts can create up to 30 fabrics in the business catalog. Owner Plus unlocks unlimited fabrics.": "يمكن للحسابات المجانية إنشاء حتى 30 قماشاً في قائمة أقمشة الأعمال. مالك بلس يفتح أقمشة غير محدودة.",
    "Open and set up a store through our sales platform": "افتح متجرك وهيّئه عبر منصة المبيعات",
    "Owner-assigned catalog fabrics: up to {limit} for this shop": "أقمشة قائمة المالك: حتى {limit} لهذا المتجر",
    "Receive and manage app orders": "استقبل وأدر طلبات التطبيق",
    "Measurements for app orders": "مقاسات طلبات التطبيق",
    "Choose a driver for orders": "اختر سائقاً للطلبات",
    "Online sales paid out every week": "تحويل مبيعات الإنترنت كل أسبوع",
    "Basic shop dashboard: {days_list} only": "لوحة المتجر الأساسية: {days_list} فقط",
    "Shop reports: today, yesterday, or up to {max_days} days": "تقارير المتجر: اليوم، أمس، أو حتى {max_days} أيام",
    "Delivery handled by your shop": "التوصيل يتم بواسطة متجرك",
    "Add in-store orders and walk-in customers": "أضف طلبات المتجر وعملاء الزيارة",
    "Customer management (CRM) for this shop": "إدارة العملاء (CRM) لهذا المتجر",
    "Order stages: measuring, cutting, sewing, fitting, ready, delivered": "مراحل الطلب: قياس، قص، خياطة، تجربة، جاهز، تم التسليم",
    "Shop-only products": "منتجات المتجر فقط",
    "Shop-only measurements": "مقاسات المتجر فقط",
    "Customisable measurement sheet (PDF) for this shop": "ورقة مقاسات قابلة للتخصيص (PDF) لهذا المتجر",
    "Unlimited owner-assigned fabrics for this shop": "أقمشة غير محدودة من المالك لهذا المتجر",
    "Full shop dashboard and earnings analytics: {days_list}": "لوحة المتجر الكاملة وتحليلات الأرباح: {days_list}",
    "All shop report periods": "جميع فترات تقارير المتجر",
    "Customer reports for this shop": "تقارير العملاء لهذا المتجر",
    "Custom WhatsApp messages to your customers": "رسائل واتساب مخصصة لعملائك",
    "Custom design for this shop's branding and storefront": "تصميم مخصص لهوية هذا المتجر وواجهته",
    "Lower commission on platform orders": "عمولة أقل على طلبات المنصة",
    "Priority support for this shop": "دعم ذو أولوية لهذا المتجر",
    "Dedicated payment gateway (add-on)": "بوابة دفع مخصصة (إضافة)",
    "Delivery and measurement-taking by Mgask (as agreed)": "التوصيل وأخذ المقاسات بواسطة مقاسك (حسب الاتفاق)",
    "One branch": "فرع واحد",
    "Up to {max_staff} staff": "حتى {max_staff} موظفين",
    "Owner dashboard: {days_list}-day views only": "لوحة المالك: عروض {days_list} يوم فقط",
    "Up to {plus_max_shops} branches": "حتى {plus_max_shops} فروع",
    "Up to {plus_max_staff} staff": "حتى {plus_max_staff} موظفين",
    "Fabric inventory: stock, movements, and owner-level insights": "مخزون الأقمشة: المخزون والحركات ورؤى على مستوى المالك",
    "Tailor Plus on every branch you own (full shop benefits, no separate upgrades)": "خياط بلس على كل فرع تملكه (مزايا المتجر الكاملة دون ترقيات منفصلة)",
    "Dedicated owner dashboard for all branches": "لوحة مالك مخصصة لجميع الفروع",
    "Branch performance comparison": "مقارنة أداء الفروع",
    "Daily reports on the dashboard and WhatsApp": "تقارير يومية على لوحة التحكم وواتساب",
    "Customer reports across branches": "تقارير العملاء عبر الفروع",
    "Account statements and financial reports": "كشوف الحساب والتقارير المالية",
    "Smart analytics across the business": "تحليلات ذكية على مستوى الأعمال",
    "Custom design for your business branding": "تصميم مخصص لهوية أعمالك",
    "Advanced technical support with higher priority": "دعم فني متقدم بأولوية أعلى",
    "Onboarding help and data migration": "مساعدة في الانضمام وترحيل البيانات",
    "Add products": "أضف المنتجات",
    "Basic dashboard": "لوحة تحكم أساسية",
    "Delivery and measurements managed by the tailor": "التوصيل والمقاسات يديرها الخياط",
    "Customer management (CRM)": "إدارة العملاء (CRM)",
    "Inventory management": "إدارة المخزون",
    "Customisable measurement sheet (PDF)": "ورقة مقاسات قابلة للتخصيص (PDF)",
    "Full dashboard": "لوحة تحكم كاملة",
    "Customer reports": "تقارير العملاء",
    "Custom design for your store's branding and storefront": "تصميم مخصص لهوية متجرك وواجهته",
    "Dedicated owner dashboard": "لوحة مالك مخصصة",
    "Account statements and reports": "كشوف الحساب والتقارير",
    "Smart analytics": "تحليلات ذكية",
    "Manage its fabrics, add, update, Assign": "إدارة الأقمشة: إضافة وتحديث وتعيين",
    "Basic Dashboard Order and sales indicators": "لوحة تحكم أساسية لمؤشرات الطلبات والمبيعات",
    "Fabric inventory Management": "إدارة مخزون الأقمشة",
    "All shops enjoy the tailor plus status in owner Plus.": "جميع المتاجر تحصل على حالة خياط بلس مع مالك بلس.",
    "Tailor Plus is required to add in-store orders and walk-in customers.": "يتطلب خياط بلس لإضافة طلبات المتجر وعملاء الزيارة.",
    "Tailor Plus is required for customer management (CRM).": "يتطلب خياط بلس لإدارة العملاء (CRM).",
    "Tailor Plus is required for full shop order stages.": "يتطلب خياط بلس لمراحل الطلب الكاملة في المتجر.",
    "Tailor Plus is required for inventory management.": "يتطلب خياط بلس لإدارة المخزون.",
    "Tailor Plus is required for shop-only products.": "يتطلب خياط بلس لمنتجات المتجر فقط.",
    "Tailor Plus is required for shop-only measurements.": "يتطلب خياط بلس لمقاسات المتجر فقط.",
    "Tailor Plus is required for the full shop dashboard.": "يتطلب خياط بلس للوحة المتجر الكاملة.",
    "Tailor Plus is required for customer reports.": "يتطلب خياط بلس لتقارير العملاء.",
    "Tailor Plus is required for custom WhatsApp messages.": "يتطلب خياط بلس لرسائل واتساب المخصصة.",
    "Tailor Plus is required to customize store branding.": "يتطلب خياط بلس لتخصيص هوية المتجر.",
    "Tailor Plus is required for delivery and measurement-taking by Mgask.": "يتطلب خياط بلس للتوصيل وأخذ المقاسات بواسطة مقاسك.",
    "Owner Plus allows up to {plus_max} shop branches.": "مالك بلس يتيح حتى {plus_max} فروع.",
    "Owner Plus allows up to 10 shop branches.": "مالك بلس يتيح حتى 10 فروع.",
    "Owner Plus allows up to {plus_max} staff.": "مالك بلس يتيح حتى {plus_max} موظفين.",
    "Owner Plus allows up to 40 staff.": "مالك بلس يتيح حتى 40 موظفاً.",
    "Free business accounts can have up to {max} shop branch. Owner Plus unlocks up to {plus_max} branches.": "يمكن للحسابات المجانية فرع واحد. مالك بلس يفتح حتى {plus_max} فروع.",
    "Free business accounts can have up to 1 shop branch. Owner Plus unlocks up to 10 branches.": "يمكن للحسابات المجانية فرع واحد. مالك بلس يفتح حتى 10 فروع.",
    "Free business accounts can have up to {max} staff. Owner Plus unlocks up to {plus_max} staff.": "يمكن للحسابات المجانية حتى {max} موظفين. مالك بلس يفتح حتى {plus_max} موظفين.",
    "Free business accounts can have up to 4 staff. Owner Plus unlocks up to 40 staff.": "يمكن للحسابات المجانية حتى 4 موظفين. مالك بلس يفتح حتى 40 موظفاً.",
    "Owner Plus is required for branch performance comparison.": "يتطلب مالك بلس لمقارنة أداء الفروع.",
    "Owner Plus is required for the dedicated owner dashboard.": "يتطلب مالك بلس للوحة المالك المخصصة.",
    "Owner Plus is required for the full owner dashboard.": "يتطلب مالك بلس للوحة المالك الكاملة.",
    "Owner Plus is required for daily reports on the dashboard and WhatsApp.": "يتطلب مالك بلس للتقارير اليومية على لوحة التحكم وواتساب.",
    "Owner Plus is required for account statements and reports.": "يتطلب مالك بلس لكشوف الحساب والتقارير.",
    "Owner Plus is required for smart analytics.": "يتطلب مالك بلس للتحليلات الذكية.",
    "Owner Plus is required for fabric inventory management.": "يتطلب مالك بلس لإدارة مخزون الأقمشة.",
    "Owner Plus is required to customize store branding.": "يتطلب مالك بلس لتخصيص هوية المتجر.",
    "3,200 SAR / year": "3,200 ريال / سنوياً",
    "excl. VAT – about SAR 267 a month": "غير شامل ضريبة القيمة المضافة – يعني حوالي 267 ريال شهرياً",
    "Run your shop with us": "أدر محلك معنا",
    "The subscription is annual and renews after we notify you, and you are entitled to a full refund within 7 days of activation.": "الاشتراك سنوي ويُجدد بعد إشعارك، ويحق لك الاسترداد الكامل خلال 7 أيام من التفعيل.",
    "Free": "مجاناً",
}

TRANSLATIONS = TRANSLATIONS_AR

LOCALE_TABLES = {
    'ar': TRANSLATIONS_AR,
    'ur': TRANSLATIONS_UR,
}


def _accept_language_from_request(request):
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    if not accept_language:
        return None
    primary_lang = accept_language.split(',')[0].split(';')[0].strip()[:2].lower()
    if primary_lang in SUPPORTED_LANGUAGES:
        return primary_lang
    return None


def get_language_from_request(request):
    """
    Detect language from the request.

    Explicit ``ar`` / ``ur`` Accept-Language wins (in-app language switch).
    Otherwise authenticated ``user.language`` wins so Flutter's default
    ``Accept-Language: en`` does not hide Arabic copy.
    Then English Accept-Language, then DEFAULT_LANGUAGE.
    """
    if not request:
        return 'en'

    header_lang = _accept_language_from_request(request)
    if header_lang in TRANSLATABLE_LANGUAGES:
        return header_lang

    if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
        user_language = getattr(request.user, 'language', None)
        if user_language in SUPPORTED_LANGUAGES:
            return user_language

    if header_lang in SUPPORTED_LANGUAGES:
        return header_lang

    return DEFAULT_LANGUAGE



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
    
    table = LOCALE_TABLES.get(language, {})
    translated = table.get(message)
    
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


def add_translation(message_key, translation, language='ar'):
    """Dynamically add a new translation at runtime."""
    if language == 'ur':
        TRANSLATIONS_UR[message_key] = translation
    else:
        TRANSLATIONS_AR[message_key] = translation
        TRANSLATIONS[message_key] = translation


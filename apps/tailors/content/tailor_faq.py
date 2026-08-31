"""Static tailor FAQ content for the public /tailor-help/ page."""

SUPPORTED_FAQ_LANGUAGES = ('en', 'ar', 'ur')
DEFAULT_FAQ_LANGUAGE = 'ar'

TAILOR_FAQ = {
    'en': {
        'page_title': 'Tailor Help & FAQs | Mgask',
        'heading': 'Help & FAQs',
        'subtitle': 'Quick answers for managing orders, shop workflow, riders, and payments.',
        'search_placeholder': 'Search help topics...',
        'no_results': 'No matching questions found.',
        'still_need_help': 'Still need help?',
        'contact_support': 'Contact support on WhatsApp',
        'support_hint': 'Our team can help with account, order, and payment issues.',
        'categories': [
            {
                'key': 'getting_started',
                'title': 'Getting started',
                'items': [
                    {
                        'q': 'How do I complete my shop profile?',
                        'a': 'Open Profile, fill shop details, upload your shop image, set working hours, and submit for review. You can start receiving orders after approval.',
                    },
                    {
                        'q': 'Why is my shop still pending or rejected?',
                        'a': 'New shops are reviewed by the Mgask team. If rejected, check the reason shown in the app, update your profile, and submit again.',
                    },
                    {
                        'q': 'How do I go online or offline?',
                        'a': 'Use the shop status toggle in the app header or profile settings. When offline, customers cannot place new orders with your shop.',
                    },
                ],
            },
            {
                'key': 'orders',
                'title': 'Orders & pipeline',
                'items': [
                    {
                        'q': 'What is the difference between Home Delivery and Walk-in orders?',
                        'a': 'Home Delivery orders are placed by customers online and may involve rider pickup and delivery. Walk-in orders are created in your shop through POS for customers who visit in person.',
                    },
                    {
                        'q': 'How do I accept or reject a new order?',
                        'a': 'Open the order from Home, review details, then tap Accept or Reject. Rejected orders should include a reason when prompted.',
                    },
                    {
                        'q': 'What are express orders?',
                        'a': 'Express orders have a shorter delivery timeline. They appear with an express badge and should be prioritized in your workflow.',
                    },
                    {
                        'q': 'How do I filter orders by status?',
                        'a': 'On Home, choose Home Delivery or Walk-in, then use the pipeline chips (New, Accepted, Stitching, Ready, etc.) to filter your order list.',
                    },
                ],
            },
            {
                'key': 'measurements',
                'title': 'Measurements',
                'items': [
                    {
                        'q': 'When should measurements be recorded?',
                        'a': 'For stitching orders, measurements must be recorded before stitching starts. Walk-in orders are usually measured in the shop. Home delivery orders may use rider measurements or shop measurements depending on the order type.',
                    },
                    {
                        'q': 'How do I add or update measurements?',
                        'a': 'Open the order, tap the measurement action, enter values for each item, and save. Review the preview before confirming.',
                    },
                ],
            },
            {
                'key': 'stitching',
                'title': 'Stitching workflow',
                'items': [
                    {
                        'q': 'How do I move an order through stitching stages?',
                        'a': 'Use the primary action button on each order card (for example: Start stitching, Mark stitched, Ready for delivery/pickup). Actions depend on the current order status.',
                    },
                    {
                        'q': 'Can I assign an order to an employee?',
                        'a': 'Yes, if your shop uses employees with stitching permissions. Open the order and assign the relevant stitcher when the action is available.',
                    },
                    {
                        'q': 'When is an order ready for the customer or rider?',
                        'a': 'Home delivery orders become Ready for Delivery when finished. Walk-in orders become Ready for Pickup when the customer can collect from your shop.',
                    },
                ],
            },
            {
                'key': 'riders',
                'title': 'Riders',
                'items': [
                    {
                        'q': 'How do I assign a rider?',
                        'a': 'For eligible home delivery orders, use the rider assignment action when accepting an order or when marking ready for delivery, depending on the workflow step shown.',
                    },
                    {
                        'q': 'What if no rider is available?',
                        'a': 'Keep the order in the correct status and contact support if delivery is delayed. You can also manage your linked riders from the riders section in profile.',
                    },
                ],
            },
            {
                'key': 'payments',
                'title': 'Payments & wallet',
                'items': [
                    {
                        'q': 'When do I receive money for completed orders?',
                        'a': 'Completed paid orders are reflected in your wallet and sales reports. Payout timing depends on your shop settlement settings shown in the finance section.',
                    },
                    {
                        'q': 'What is COD (Cash on Delivery)?',
                        'a': 'For COD orders, payment may be collected on delivery. Follow the payment status shown on the order and wallet screens.',
                    },
                ],
            },
            {
                'key': 'catalog',
                'title': 'Fabrics & catalog',
                'items': [
                    {
                        'q': 'How do I add fabrics to my catalog?',
                        'a': 'Open Fabrics, add fabric details, images, price, and stock. Active fabrics become available for customer and POS orders.',
                    },
                ],
            },
            {
                'key': 'account',
                'title': 'Account & app',
                'items': [
                    {
                        'q': 'How do I change app language?',
                        'a': 'Open Profile or Settings and select your preferred language (Arabic, English, or Urdu).',
                    },
                    {
                        'q': 'Why am I not receiving notifications?',
                        'a': 'Ensure notifications are enabled in device settings and you are logged in. Log out and log in again if token registration fails.',
                    },
                ],
            },
        ],
    },
    'ar': {
        'page_title': 'مساعدة الخياط والأسئلة الشائعة | مقاسك',
        'heading': 'المساعدة والأسئلة الشائعة',
        'subtitle': 'إجابات سريعة لإدارة الطلبات وسير العمل في المحل والمندوبين والمدفوعات.',
        'search_placeholder': 'ابحث في مواضيع المساعدة...',
        'no_results': 'لم يتم العثور على أسئلة مطابقة.',
        'still_need_help': 'ما زلت بحاجة إلى مساعدة؟',
        'contact_support': 'تواصل مع الدعم عبر واتساب',
        'support_hint': 'يمكن لفريقنا مساعدتك في الحساب والطلبات والمدفوعات.',
        'categories': [
            {
                'key': 'getting_started',
                'title': 'البدء',
                'items': [
                    {
                        'q': 'كيف أكمل ملف المحل؟',
                        'a': 'افتح الملف الشخصي، أدخل بيانات المحل، ارفع صورة المحل، حدد ساعات العمل، ثم أرسل للمراجعة. يمكنك استقبال الطلبات بعد الموافقة.',
                    },
                    {
                        'q': 'لماذا محلي ما زال قيد المراجعة أو مرفوضاً؟',
                        'a': 'يتم مراجعة المحلات الجديدة من فريق مقاسك. إذا رُفض الطلب، راجع السبب في التطبيق، حدّث الملف، وأعد الإرسال.',
                    },
                    {
                        'q': 'كيف أفعّل أو أوقف المحل؟',
                        'a': 'استخدم مفتاح حالة المحل في رأس التطبيق أو الإعدادات. عند الإيقاف، لا يمكن للعملاء إنشاء طلبات جديدة.',
                    },
                ],
            },
            {
                'key': 'orders',
                'title': 'الطلبات وسير العمل',
                'items': [
                    {
                        'q': 'ما الفرق بين التوصيل للمنزل وطلبات المحل؟',
                        'a': 'طلبات التوصيل للمنزل تُنشأ عبر التطبيق وقد تتطلب مندوباً. طلبات المحل تُنشأ من نقطة البيع للزبائن الحاضرين في المحل.',
                    },
                    {
                        'q': 'كيف أقبل أو أرفض طلباً جديداً؟',
                        'a': 'افتح الطلب من الرئيسية، راجع التفاصيل، ثم اضغط قبول أو رفض. عند الرفض قد يُطلب منك ذكر السبب.',
                    },
                    {
                        'q': 'ما هي الطلبات السريعة (Express)؟',
                        'a': 'الطلبات السريعة لها مدة تسليم أقصر وتظهر بشارة Express ويجب إعطاؤها أولوية في التنفيذ.',
                    },
                    {
                        'q': 'كيف أفلتر الطلبات حسب الحالة؟',
                        'a': 'من الرئيسية اختر التوصيل للمنزل أو طلبات المحل، ثم استخدم شرائح الحالة (جديد، مقبول، خياطة، جاهز، إلخ).',
                    },
                ],
            },
            {
                'key': 'measurements',
                'title': 'القياسات',
                'items': [
                    {
                        'q': 'متى يجب تسجيل القياسات؟',
                        'a': 'في طلبات الخياطة يجب تسجيل القياسات قبل بدء الخياطة. طلبات المحل تُقاس عادة داخل المحل. طلبات التوصيل قد تستخدم قياس المندوب أو قياس المحل حسب نوع الطلب.',
                    },
                    {
                        'q': 'كيف أضيف أو أحدّث القياسات؟',
                        'a': 'افتح الطلب، اضغط إجراء القياس، أدخل القيم لكل قطعة، ثم احفظ وراجع المعاينة قبل التأكيد.',
                    },
                ],
            },
            {
                'key': 'stitching',
                'title': 'سير الخياطة',
                'items': [
                    {
                        'q': 'كيف أنقل الطلب بين مراحل الخياطة؟',
                        'a': 'استخدم الزر الرئيسي في بطاقة الطلب (مثل: بدء الخياطة، تم الخياطة، جاهز للتوصيل/الاستلام). الإجراءات تعتمد على حالة الطلب الحالية.',
                    },
                    {
                        'q': 'هل يمكنني إسناد الطلب لموظف؟',
                        'a': 'نعم إذا كان لديك موظفون بصلاحية الخياطة. افتح الطلب وأسند الخياط المناسب عند توفر الإجراء.',
                    },
                    {
                        'q': 'متى يصبح الطلب جاهزاً للعميل أو المندوب؟',
                        'a': 'طلبات التوصيل تصبح جاهزة للتوصيل عند الانتهاء. طلبات المحل تصبح جاهزة للاستلام عندما يمكن للعميل الاستلام من المحل.',
                    },
                ],
            },
            {
                'key': 'riders',
                'title': 'المندوبون',
                'items': [
                    {
                        'q': 'كيف أعيّن مندوباً؟',
                        'a': 'في طلبات التوصيل المؤهلة، استخدم إجراء تعيين المندوب عند القبول أو عند الجاهزية للتوصيل حسب الخطوة الظاهرة.',
                    },
                    {
                        'q': 'ماذا أفعل إذا لم يتوفر مندوب؟',
                        'a': 'أبقِ الطلب في الحالة الصحيحة وتواصل مع الدعم عند التأخير. يمكنك إدارة المندوبين المرتبطين من قسم المندوبين في الملف الشخصي.',
                    },
                ],
            },
            {
                'key': 'payments',
                'title': 'المدفوعات والمحفظة',
                'items': [
                    {
                        'q': 'متى أستلم أموال الطلبات المكتملة؟',
                        'a': 'تظهر الطلبات المدفوعة المكتملة في المحفظة وتقارير المبيعات. موعد التحويل يعتمد على إعدادات التسوية في قسم المالية.',
                    },
                    {
                        'q': 'ما هو الدفع عند الاستلام (COD)؟',
                        'a': 'في طلبات COD قد يُحصّل المبلغ عند التسليم. اتبع حالة الدفع الظاهرة في الطلب والمحفظة.',
                    },
                ],
            },
            {
                'key': 'catalog',
                'title': 'الأقمشة والكتالوج',
                'items': [
                    {
                        'q': 'كيف أضيف أقمشة إلى الكتالوج؟',
                        'a': 'افتح الأقمشة، أضف التفاصيل والصور والسعر والمخزون. الأقمشة النشطة تصبح متاحة لطلبات العملاء ونقطة البيع.',
                    },
                ],
            },
            {
                'key': 'account',
                'title': 'الحساب والتطبيق',
                'items': [
                    {
                        'q': 'كيف أغيّر لغة التطبيق؟',
                        'a': 'افتح الملف الشخصي أو الإعدادات واختر اللغة (العربية، الإنجليزية، أو الأردية).',
                    },
                    {
                        'q': 'لماذا لا تصلني الإشعارات؟',
                        'a': 'تأكد من تفعيل الإشعارات في إعدادات الجهاز وأنك مسجل الدخول. أعد تسجيل الدخول إذا فشل تسجيل التوكن.',
                    },
                ],
            },
        ],
    },
    'ur': {
        'page_title': 'درزی کی مدد اور عمومی سوالات | مقاسک',
        'heading': 'مدد اور عمومی سوالات',
        'subtitle': 'آرڈرز، دکان کے کام، رائیڈرز اور ادائیگیوں کے لیے فوری جوابات۔',
        'search_placeholder': 'مدد کے موضوعات تلاش کریں...',
        'no_results': 'کوئی مماثل سوال نہیں ملا۔',
        'still_need_help': 'اب بھی مدد چاہیے؟',
        'contact_support': 'واٹس ایپ پر سپورٹ سے رابطہ کریں',
        'support_hint': 'ہماری ٹیم اکاؤنٹ، آرڈر اور ادائیگی کے مسائل میں مدد کر سکتی ہے۔',
        'categories': [
            {
                'key': 'getting_started',
                'title': 'شروعات',
                'items': [
                    {
                        'q': 'میں اپنی دکان کی پروفائل کیسے مکمل کروں؟',
                        'a': 'پروفائل کھولیں، دکان کی تفصیلات بھریں، تصویر اپ لوڈ کریں، اوقات کار سیٹ کریں، اور جائزے کے لیے جمع کرائیں۔ منظوری کے بعد آرڈرز وصول ہو سکتے ہیں۔',
                    },
                    {
                        'q': 'میری دکان ابھی زیرِ غور یا مسترد کیوں ہے؟',
                        'a': 'نئی دکانوں کا جائزہ مقاسک ٹیم لیتی ہے۔ اگر مسترد ہو تو ایپ میں وجہ دیکھیں، پروفائل اپ ڈیٹ کریں، اور دوبارہ جمع کرائیں۔',
                    },
                    {
                        'q': 'میں دکان آن لائن یا آف لائن کیسے کروں؟',
                        'a': 'ایپ ہیڈر یا سیٹنگز میں دکان کی حیثیت کا ٹوگل استعمال کریں۔ آف لائن ہونے پر نئے آرڈرز نہیں آئیں گے۔',
                    },
                ],
            },
            {
                'key': 'orders',
                'title': 'آرڈرز اور ورک فلو',
                'items': [
                    {
                        'q': 'ہوم ڈیلیوری اور واک اِن آرڈرز میں کیا فرق ہے؟',
                        'a': 'ہوم ڈیلیوری آرڈرز آن لائن بنتے ہیں اور رائیڈر کی ضرورت ہو سکتی ہے۔ واک اِن آرڈرز دکان میں POS سے بنتے ہیں۔',
                    },
                    {
                        'q': 'میں نیا آرڈر کیسے قبول یا مسترد کروں؟',
                        'a': 'ہوم سے آرڈر کھولیں، تفصیلات دیکھیں، پھر قبول یا مسترد دبائیں۔ مسترد کرتے وقت وجہ درکار ہو سکتی ہے۔',
                    },
                    {
                        'q': 'ایکسپریس آرڈرز کیا ہیں؟',
                        'a': 'ایکسپریس آرڈرز کی ڈیلیوری کا وقت کم ہوتا ہے۔ انہیں فوری ترجیح دیں۔',
                    },
                    {
                        'q': 'میں آرڈرز کو حالت کے مطابق کیسے فلٹر کروں؟',
                        'a': 'ہوم پر ہوم ڈیلیوری یا واک اِن منتخب کریں، پھر پائپ لائن چپس (نیا، قبول شدہ، سلائی، تیار وغیرہ) استعمال کریں۔',
                    },
                ],
            },
            {
                'key': 'measurements',
                'title': 'پیمائش',
                'items': [
                    {
                        'q': 'پیمائش کب ریکارڈ کرنی چاہیے؟',
                        'a': 'سلائی والے آرڈرز میں سلائی سے پہلے پیمائش ضروری ہے۔ واک اِن عام طور پر دکان میں ہوتی ہے۔ ہوم ڈیلیوری میں رائیڈر یا دکان کی پیمائش آرڈر کی قسم پر منحصر ہے۔',
                    },
                    {
                        'q': 'میں پیمائش کیسے شامل یا اپ ڈیٹ کروں؟',
                        'a': 'آرڈر کھولیں، پیمائش کا ایکشن دبائیں، ہر آئٹم کی قدریں درج کریں، پھر محفوظ کریں اور تصدیق سے پہلے جائزہ لیں۔',
                    },
                ],
            },
            {
                'key': 'stitching',
                'title': 'سلائی کا عمل',
                'items': [
                    {
                        'q': 'میں آرڈر کو سلائی کے مراحل میں کیسے آگے بڑھاؤں؟',
                        'a': 'آرڈر کارڈ پر بنیادی بٹن استعمال کریں (جیسے سلائی شروع کریں، سلائی مکمل، ڈیلیوری/پک اپ کے لیے تیار)۔',
                    },
                    {
                        'q': 'کیا میں آرڈر کسی ملازم کو دے سکتا ہوں؟',
                        'a': 'جی ہاں، اگر ملازمین کو سلائی کی اجازت ہو۔ آرڈر کھول کر مناسب سلائی کار تفویض کریں۔',
                    },
                    {
                        'q': 'آرڈر کب گاہک یا رائیڈر کے لیے تیار ہوتا ہے؟',
                        'a': 'ہوم ڈیلیوری مکمل ہونے پر ڈیلیوری کے لیے تیار ہوتی ہے۔ واک اِن گاہک کے دکان سے لینے کے لیے تیار ہوتی ہے۔',
                    },
                ],
            },
            {
                'key': 'riders',
                'title': 'رائیڈرز',
                'items': [
                    {
                        'q': 'میں رائیڈر کیسے تفویض کروں؟',
                        'a': 'اہل ہوم ڈیلیوری آرڈرز میں قبولیت یا ڈیلیوری کی تیاری کے مرحلے پر رائیڈر تفویض کا ایکشن استعمال کریں۔',
                    },
                    {
                        'q': 'اگر رائیڈر دستیاب نہ ہو تو کیا کروں؟',
                        'a': 'آرڈر کو درست حالت میں رکھیں اور تاخیر پر سپورٹ سے رابطہ کریں۔ پروفائل میں رائیڈرز سیکشن سے منسلک رائیڈرز منظم کریں۔',
                    },
                ],
            },
            {
                'key': 'payments',
                'title': 'ادائیگیاں اور والیٹ',
                'items': [
                    {
                        'q': 'مکمل آرڈرز کی رقم مجھے کب ملتی ہے؟',
                        'a': 'ادا شدہ مکمل آرڈرز والیٹ اور سیلز رپورٹس میں نظر آتے ہیں۔ ادائیگی کا وقت مالی سیٹنگز پر منحصر ہے۔',
                    },
                    {
                        'q': 'COD (کیش آن ڈیلیوری) کیا ہے؟',
                        'a': 'COD آرڈرز میں ادائیگی ڈیلیوری پر وصول ہو سکتی ہے۔ آرڈر اور والیٹ میں ادائیگی کی حالت دیکھیں۔',
                    },
                ],
            },
            {
                'key': 'catalog',
                'title': 'کپڑے اور کیٹلاگ',
                'items': [
                    {
                        'q': 'میں کیٹلاگ میں کپڑے کیسے شامل کروں؟',
                        'a': 'کپڑے سیکشن کھولیں، تفصیلات، تصاویر، قیمت اور اسٹاک شامل کریں۔ فعال کپڑے آرڈرز کے لیے دستیاب ہو جاتے ہیں۔',
                    },
                ],
            },
            {
                'key': 'account',
                'title': 'اکاؤنٹ اور ایپ',
                'items': [
                    {
                        'q': 'میں ایپ کی زبان کیسے بدلوں؟',
                        'a': 'پروفائل یا سیٹنگز میں جا کر زبان منتخب کریں (عربی، انگریزی، یا اردو)۔',
                    },
                    {
                        'q': 'مجھے نوٹیفکیشنز کیوں نہیں آ رہیں؟',
                        'a': 'ڈیوائس سیٹنگز میں نوٹیفکیشنز فعال کریں اور لاگ اِن رہیں۔ اگر مسئلہ رہے تو دوبارہ لاگ اِن کریں۔',
                    },
                ],
            },
        ],
    },
}


def resolve_faq_language(language: str | None) -> str:
    lang = (language or DEFAULT_FAQ_LANGUAGE).strip().lower()
    if lang not in SUPPORTED_FAQ_LANGUAGES:
        return DEFAULT_FAQ_LANGUAGE
    return lang


def get_tailor_faq_content(language: str | None) -> dict:
    lang = resolve_faq_language(language)
    return TAILOR_FAQ[lang]

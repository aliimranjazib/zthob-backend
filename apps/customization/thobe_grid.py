"""Thobe measurement sequence and PDF grid layout (client-approved)."""

THOBE_FIELDS = [
    # name, display_name, display_name_ar, display_order, pdf_grid_row, pdf_grid_col
    ('sleeve_width', 'Sleeve Width (Bicep)', 'وسع الكم (الباي)', 1, 1, 1),
    ('takhalis', 'Takhalis', 'تخاليص', 2, 2, 1),
    ('waist', 'Waist', 'الوسط (الخصر)', 3, 4, 1),
    ('teek', 'Teek', 'تيك', 4, 1, 2),
    ('hips', 'Hips', 'هيف (الارداف)', 5, 2, 2),
    ('khbna', 'Khbna', 'الخبنة', 6, 4, 2),
    ('upper_chest', 'Upper Chest', 'صدر علوي', 7, 1, 4),
    ('lower_chest', 'Lower Chest', 'صدر اسفل', 8, 2, 4),
    ('chest_circumference', 'Chest Circumference', 'محيط الصدر', 9, 3, 4),
    ('front_length', 'Front Length', 'طول امامي', 10, 4, 4),
    ('back_length', 'Back Length', 'طول خلف', 11, 3, 1),
    ('cuff_sleeve', 'Cuff Sleeve', 'يد كبك', 12, 1, 5),
    ('front_shoulder', 'Front Shoulder', 'كتف امام', 13, 2, 5),
    ('collar_flip', 'Flip Collar', 'رقبه قلاب', 14, 1, 3),
    ('plain_sleeve', 'Plain Sleeve', 'يد ساده', 15, 2, 3),
    ('shoulder_drop', 'Shoulder Drop', 'داونينك (نزول الكتف)', 16, 3, 3),
    ('back_shoulder', 'Back Shoulder', 'كتف خلف', 17, 3, 2),
    ('step_width', 'Step Width', 'وسع الخطوه', 18, 4, 3),
    ('armhole', 'Armhole', 'ارمود (فتحة الكتف)', 19, 3, 5),
    ('plain_neck', 'Plain Neck', 'رقبه ساده', 20, 4, 5),
]

THOBE_FIELD_ORDER = [row[0] for row in THOBE_FIELDS]

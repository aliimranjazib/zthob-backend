from django.db import migrations, models


FABRIC_COUNTRY_LOCALE_BACKFILL = {
    "JP": {
        "description": "Known for premium fabrics such as Shikibo and Teijin",
        "name_ur": "جاپان",
        "description_ur": "شیکوبو اور ٹیجین جیسے اعلیٰ معیار کے کپڑوں کے لیے مشہور",
    },
    "KR": {
        "description": "Known for high-quality and wrinkle-resistant fabrics",
        "name_ur": "جنوبی کوریا",
        "description_ur": "اعلیٰ معیار اور سلوٹ مزاحم کپڑوں کے لیے مشہور",
    },
    "CN": {
        "description": "Largest global fabric producer across price tiers",
        "name_ur": "چین",
        "description_ur": "مختلف قیمتوں میں دنیا کا سب سے بڑا کپڑا پیدا کنندہ",
    },
    "IN": {
        "description": "Strong in cotton and blended fabrics",
        "name_ur": "بھارت",
        "description_ur": "کپاس اور مخلوط کپڑوں میں مضبوط",
    },
    "ID": {
        "description": "Widely used in economy and mid-range thobes",
        "name_ur": "انڈونیشیا",
        "description_ur": "اقتصادی اور درمیانی قیمت والی ثیاب میں کثرت سے استعمال",
    },
    "TH": {
        "description": "Produces polyester and blends suited for thobes",
        "name_ur": "تھائی لینڈ",
        "description_ur": "پولی ایسٹر اور ثیاب کے لیے موزوں مخلوط کپڑے تیار کرتا ہے",
    },
    "IT": {
        "description": "For very premium fabrics and luxury brands",
        "name_ur": "اٹلی",
        "description_ur": "انتہائی اعلیٰ معیار کے کپڑوں اور لگژری برانڈز کے لیے",
    },
    "UK": {
        "description": "Known for classic premium fabrics",
        "name_ur": "برطانیہ",
        "description_ur": "کلاسک اعلیٰ معیار کے کپڑوں کے لیے مشہور",
    },
}


def backfill_fabric_country_locales(apps, schema_editor):
    FabricCountry = apps.get_model("tailors", "FabricCountry")
    for code, fields in FABRIC_COUNTRY_LOCALE_BACKFILL.items():
        FabricCountry.objects.filter(code=code).update(**fields)


class Migration(migrations.Migration):

    dependencies = [
        ("tailors", "0026_unique_fabric_name_per_shop"),
    ]

    operations = [
        migrations.AddField(
            model_name="fabriccountry",
            name="name_ur",
            field=models.CharField(
                blank=True,
                help_text="Country name in Urdu",
                max_length=100,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="fabriccountry",
            name="description_ur",
            field=models.TextField(
                blank=True,
                help_text="Short description in Urdu",
                null=True,
            ),
        ),
        migrations.RunPython(
            backfill_fabric_country_locales,
            migrations.RunPython.noop,
        ),
    ]

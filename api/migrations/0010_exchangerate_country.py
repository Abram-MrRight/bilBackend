from django.db import migrations, models
import django.db.models.deletion

def populate_country(apps, schema_editor):
    Country = apps.get_model("api", "Country")
    ExchangeRate = apps.get_model("api", "ExchangeRate")
    
    uganda, created = Country.objects.get_or_create(name="Uganda", defaults={"code": "UG"})
    
    # Assign Uganda to all existing ExchangeRate rows
    ExchangeRate.objects.all().update(country=uganda)

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_exchangerate'),
    ]

    operations = [
        migrations.AddField(
            model_name='exchangerate',
            name='country',
            field=models.ForeignKey(
                to='api.Country',
                on_delete=django.db.models.deletion.CASCADE,
                null=True,  # temporary so migration works
            ),
        ),
        migrations.RunPython(populate_country),
        migrations.AlterField(
            model_name='exchangerate',
            name='country',
            field=models.ForeignKey(
                to='api.Country',
                on_delete=django.db.models.deletion.CASCADE,
                null=False,  # now enforce non-null
            ),
        ),
    ]

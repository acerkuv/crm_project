from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0006_scheduledevent_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='hobby',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='Хобби'),
        ),
    ]

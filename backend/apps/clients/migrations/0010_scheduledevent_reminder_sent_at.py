from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0009_normalize_phones'),
    ]
    operations = [
        migrations.AddField(
            model_name='scheduledevent',
            name='reminder_sent_at',
            field=models.DateTimeField(
                blank=True, null=True,
                verbose_name='Напоминание отправлено',
            ),
        ),
    ]
from django.db import migrations
import re


def normalize_phones(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    for client in Client.objects.all():
        raw = client.phone or ''
        digits = re.sub(r'\D', '', raw)
        if not digits:
            continue
        if len(digits) == 10:
            new = f'+7{digits}'
        elif len(digits) == 11 and digits[0] in ('7', '8'):
            new = f'+7{digits[1:]}'
        else:
            continue
        if new != raw:
            if not Client.objects.exclude(pk=client.pk).filter(phone=new).exists():
                client.phone = new
                client.save(update_fields=['phone'])


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0008_customfield_address_is_deleted'),
    ]
    operations = [
        migrations.RunPython(normalize_phones, migrations.RunPython.noop),
    ]
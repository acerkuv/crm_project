from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0007_client_hobby'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='address',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='Адрес'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='Удалено'),
        ),
        migrations.CreateModel(
            name='CustomField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Название поля')),
                ('field_type', models.CharField(choices=[('text', 'Текст'), ('date', 'Дата'), ('number', 'Число')], default='text', max_length=20, verbose_name='Тип')),
                ('value', models.TextField(blank=True, default='', verbose_name='Значение')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_fields', to='clients.client')),
            ],
            options={
                'verbose_name': 'Кастомное поле',
                'verbose_name_plural': 'Кастомные поля',
                'ordering': ['name'],
                'unique_together': {('client', 'name')},
            },
        ),
    ]
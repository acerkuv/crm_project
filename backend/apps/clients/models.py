from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Client(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients', null=True, blank=True)
    first_name = models.CharField('Имя', max_length=100)
    last_name = models.CharField('Фамилия', max_length=100, blank=True)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    phone = models.CharField('Телефон', max_length=20, unique=True)
    email = models.EmailField('Email', blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/%Y/%m/', blank=True, null=True)
    company = models.CharField('Компания', max_length=200, blank=True)
    position = models.CharField('Должность', max_length=200, blank=True)
    telegram_id = models.CharField(max_length=100, blank=True, null=True)
    max_id = models.CharField(max_length=100, blank=True, null=True)
    comment = models.TextField('Комментарий', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contact = models.DateTimeField('Последний контакт', null=True, blank=True)
    hobby = models.CharField('Хобби', max_length=500, blank=True, default='')
    address = models.CharField('Адрес', max_length=500, blank=True, default='')
    status = models.CharField('Статус', max_length=20, choices=[
        ('lead', 'Лид'),
        ('active', 'Активный'),
        ('regular', 'Постоянный'),
        ('vip', 'VIP'),
        ('inactive', 'Неактивный'),
    ], default='lead')
    
    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Tag(models.Model):
    """Теги для клиентов"""
    name = models.CharField('Название', max_length=50, unique=True)
    color = models.CharField('Цвет', max_length=7, default='#007bff')
    clients = models.ManyToManyField(Client, related_name='tags', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
    
    def __str__(self):
        return self.name


class Interaction(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='interactions')
    type = models.CharField('Тип', max_length=20, choices=[
        ('call', 'Звонок'),
        ('message', 'Сообщение'),
        ('meeting', 'Встреча'),
        ('email', 'Email'),
        ('note', 'Заметка'),
        ('birthday', 'Поздравление'),
        ('reminder', 'Напоминание'),
    ])
    content = models.TextField('Содержание')
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField('Запланировано на', null=True, blank=True)
    completed_at = models.DateTimeField('Выполнено', null=True, blank=True)
    is_ai_generated = models.BooleanField('Сгенерировано ИИ', default=False)
    sent_via_telegram = models.BooleanField('Отправлено в Telegram', default=False)
    sent_via_max = models.BooleanField('Отправлено в MAX', default=False)
    is_deleted = models.BooleanField('Удалено', default=False)
    
    class Meta:
        verbose_name = 'Взаимодействие'
        verbose_name_plural = 'Взаимодействия'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.client}"


class ScheduledEvent(models.Model):
    """Запланированное событие для клиента"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_events', null=True, blank=True)  # ДОБАВИТЬ ЭТО
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='scheduled_events')
    title = models.CharField('Заголовок', max_length=200)
    description = models.TextField('Описание', blank=True)
    event_type = models.CharField('Тип события', max_length=20, choices=[
        ('call', 'Звонок'),
        ('meeting', 'Встреча'),
        ('birthday', 'Поздравление'),
        ('reminder', 'Напоминание'),
        ('custom', 'Своё'),
    ])
    scheduled_date = models.DateTimeField('Запланированная дата')
    is_completed = models.BooleanField('Выполнено', default=False)
    is_ai_generated = models.BooleanField('Сгенерировано ИИ', default=False)
    ai_content = models.TextField('Содержание от ИИ', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField('Выполнено в', null=True, blank=True)
    reminder_sent_at = models.DateTimeField('Напоминание отправлено', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Запланированное событие'
        verbose_name_plural = 'Запланированные события'
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.client} - {self.scheduled_date}"
    
class CustomField(models.Model):
    """Произвольное поле карточки клиента."""
    FIELD_TYPES = [
        ('text', 'Текст'),
        ('date', 'Дата'),
        ('number', 'Число'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='custom_fields')
    name = models.CharField('Название поля', max_length=100)
    field_type = models.CharField('Тип', max_length=20, choices=FIELD_TYPES, default='text')
    value = models.TextField('Значение', blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Кастомное поле'
        verbose_name_plural = 'Кастомные поля'
        unique_together = [('client', 'name')]
        ordering = ['name']

    def __str__(self):
        return f"{self.client}: {self.name}={self.value[:30]}"
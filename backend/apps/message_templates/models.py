from django.db import models
from apps.clients.models import Client

class MessageTemplate(models.Model):
    name = models.CharField('Название', max_length=100)
    subject = models.CharField('Тема', max_length=200, blank=True)
    content = models.TextField('Содержание')
    use_ai = models.BooleanField('Использовать ИИ', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Шаблон сообщения'
        verbose_name_plural = 'Шаблоны сообщений'
    
    def __str__(self):
        return self.name

class BroadcastMessage(models.Model):
    template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True)
    recipients = models.ManyToManyField(Client, related_name='broadcasts')
    content = models.TextField('Текст рассылки')
    sent_at = models.DateTimeField('Отправлено', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField('Отправлено', default=False)
    
    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Рассылка от {self.created_at}'

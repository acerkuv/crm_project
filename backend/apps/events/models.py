from django.db import models
from apps.clients.models import Client

class Event(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='events')
    title = models.CharField('Заголовок', max_length=200)
    description = models.TextField('Описание', blank=True)
    event_date = models.DateTimeField('Дата и время события')
    is_completed = models.BooleanField('Выполнено', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Событие'
        verbose_name_plural = 'События'
        ordering = ['event_date']
    
    def __str__(self):
        return f"{self.title} - {self.client}"

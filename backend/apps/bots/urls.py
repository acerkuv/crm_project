from django.urls import path
from .telegram import views as telegram_views
from .max import views as max_views

urlpatterns = [
    path('webhook/telegram/', telegram_views.webhook, name='telegram_webhook'),
    path('webhook/max/', max_views.webhook, name='max_webhook'),
]

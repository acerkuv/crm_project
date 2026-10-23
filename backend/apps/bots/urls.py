from django.urls import path
from .max import views as max_views

urlpatterns = [
    path('webhook/max/', max_views.webhook, name='max_webhook'),
]
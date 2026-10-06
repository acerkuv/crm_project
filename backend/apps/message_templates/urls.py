from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.MessageTemplateViewSet)
router.register(r'broadcasts', views.BroadcastMessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, TagViewSet, InteractionViewSet, ScheduledEventViewSet

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'tags', TagViewSet)
router.register(r'interactions', InteractionViewSet)
router.register(r'scheduled-events', ScheduledEventViewSet, basename='scheduled-event')

urlpatterns = [
    path('', include(router.urls)),
]
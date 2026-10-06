from django.urls import path
from .views import verify_login_code, get_subscription_status, user_profile

urlpatterns = [
    path('verify-code/', verify_login_code, name='verify-code'),
    path('subscription/', get_subscription_status, name='subscription'),
    path('profile/', user_profile, name='user-profile'),  # Добавить эту строку
]

from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .models import TelegramUser

def check_subscription_limit(limit_type='clients'):
    """
    Декоратор для проверки лимитов подписки
    
    Использование:
    @check_subscription_limit('clients')
    def create_client(request):
        ...
    
    @check_subscription_limit('events')
    def create_event(request):
        ...
    
    @check_subscription_limit('ai')
    def use_ai(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(self, request, *args, **kwargs):
            user = request.user
            
            try:
                telegram_user = user.telegram_profile
            except TelegramUser.DoesNotExist:
                return Response(
                    {'error': 'Пользователь не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Проверяем активность подписки
            if not telegram_user.is_subscription_active():
                return Response(
                    {
                        'error': 'Подписка истекла',
                        'details': 'Продлите подписку для доступа к функциям',
                        'plan': telegram_user.subscription_plan,
                        'expires_at': telegram_user.subscription_expires_at,
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Проверяем конкретный лимит
            if limit_type == 'clients':
                if not telegram_user.can_add_client():
                    max_clients = telegram_user.get_max_clients()
                    return Response(
                        {
                            'error': f'Достигнут лимит клиентов ({max_clients})',
                            'details': 'Обновите тариф для добавления большего количества клиентов',
                            'current': telegram_user.user.clients.count(),
                            'max': max_clients if max_clients > 0 else 'безлимит',
                            'plan': telegram_user.subscription_plan,
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
                    
            elif limit_type == 'events':
                if not telegram_user.can_add_event():
                    max_events = telegram_user.get_max_events()
                    return Response(
                        {
                            'error': f'Достигнут лимит событий в этом месяце ({max_events})',
                            'details': 'Обновите тариф для создания большего количества событий',
                            'current': telegram_user.events_this_month,
                            'max': max_events if max_events > 0 else 'безлимит',
                            'plan': telegram_user.subscription_plan,
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
                    
            elif limit_type == 'ai':
                if not telegram_user.can_use_ai():
                    max_ai = telegram_user.get_max_ai_requests()
                    return Response(
                        {
                            'error': f'Достигнут лимит AI запросов в этом месяце ({max_ai})',
                            'details': 'Обновите тариф для использования AI',
                            'current': telegram_user.ai_requests_used,
                            'max': max_ai if max_ai > 0 else 'безлимит',
                            'plan': telegram_user.subscription_plan,
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            return view_func(self, request, *args, **kwargs)
        return wrapped_view
    return decorator

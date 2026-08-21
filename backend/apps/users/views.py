from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import TelegramUser, LoginCode
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@api_view(['POST'])
@permission_classes([])  # AllowAny для входа
def verify_login_code(request):
    """
    Проверка кода входа и возврат токена
    Ожидает: {'code': '123456'} или {'telegram_id': '123', 'code': '123456'}
    """
    try:
        code = request.data.get('code')
        telegram_id = request.data.get('telegram_id')
        
        if not code:
            return Response(
                {'error': 'Код не предоставлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ищем код в базе
        try:
            login_code = LoginCode.objects.get(
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            )
        except LoginCode.DoesNotExist:
            return Response(
                {'error': 'Недействительный или просроченный код'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем TelegramUser
        telegram_user = login_code.telegram_user
        
        # Отмечаем код как использованный
        login_code.is_used = True
        login_code.save()
        
        # Получаем или создаем User
        user = telegram_user.user
        
        # Создаем или получаем токен
        token, created = Token.objects.get_or_create(user=user)
        
        # Обновляем время последнего входа
        telegram_user.last_login = timezone.now()
        telegram_user.save()
        
        return Response({
            'success': True,
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'telegram_id': telegram_user.telegram_id,
                'first_name': telegram_user.first_name,
                'last_name': telegram_user.last_name,
            }
        })
        
    except Exception as e:
        logger.error(f"Ошибка при верификации кода: {str(e)}")
        return Response(
            {'error': 'Внутренняя ошибка сервера'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription_status(request):
    """Получить статус подписки текущего пользователя"""
    try:
        user = request.user
        telegram_user = user.telegram_profile
        
        stats = telegram_user.get_usage_stats()
        
        return Response({
            'success': True,
            'subscription': {
                'plan': stats['plan'],
                'is_active': stats['active'],
                'expires_at': stats['expires_at'],
            },
            'limits': {
                'clients': {
                    'used': stats['clients']['used'],
                    'max': stats['clients']['max'],
                    'percent': stats['clients']['percent'],
                },
                'events': {
                    'used': stats['events']['used'],
                    'max': stats['events']['max'],
                    'percent': stats['events']['percent'],
                },
                'ai': {
                    'used': stats['ai']['used'],
                    'max': stats['ai']['max'],
                    'percent': stats['ai']['percent'],
                }
            }
        })
        
    except TelegramUser.DoesNotExist:
        return Response(
            {'error': 'Профиль Telegram не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Получить или обновить профиль пользователя"""
    try:
        user = request.user
        telegram_user = user.telegram_profile
        
        if request.method == 'GET':
            # Получить профиль
            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                },
                'telegram': {
                    'telegram_id': telegram_user.telegram_id,
                    'username': telegram_user.username,
                    'first_name': telegram_user.first_name,
                    'last_name': telegram_user.last_name,
                    'phone': telegram_user.phone,
                    'role': telegram_user.role,
                },
                'subscription': {
                    'plan': telegram_user.subscription_plan,
                    'is_active': telegram_user.is_subscription_active(),
                    'expires_at': telegram_user.subscription_expires_at,
                }
            })
        
        elif request.method in ['PUT', 'PATCH']:
            # Обновить профиль
            data = request.data
            
            # Обновляем User модель
            if 'email' in data:
                user.email = data['email']
                user.save()
            
            # Обновляем TelegramUser модель
            if 'first_name' in data:
                telegram_user.first_name = data['first_name']
            if 'last_name' in data:
                telegram_user.last_name = data['last_name']
            if 'phone' in data:
                telegram_user.phone = data['phone']
            
            telegram_user.save()
            
            return Response({
                'success': True,
                'message': 'Профиль обновлен',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                },
                'telegram': {
                    'telegram_id': telegram_user.telegram_id,
                    'username': telegram_user.username,
                    'first_name': telegram_user.first_name,
                    'last_name': telegram_user.last_name,
                    'phone': telegram_user.phone,
                    'role': telegram_user.role,
                }
            })
            
    except TelegramUser.DoesNotExist:
        return Response(
            {'error': 'Профиль Telegram не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Ошибка при работе с профилем: {str(e)}")
        return Response(
            {'error': 'Внутренняя ошибка сервера'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
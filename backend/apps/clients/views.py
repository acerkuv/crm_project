from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image
from io import BytesIO
import os
from django.conf import settings
from .models import Client, Tag, Interaction, ScheduledEvent  # ДОБАВЛЯЕМ ScheduledEvent
from .serializers import ClientSerializer, TagSerializer, InteractionSerializer, ScheduledEventSerializer  # ДОБАВЛЯЕМ ScheduledEventSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
    
    @action(detail=True, methods=['patch'], url_path='upload_avatar')
    def upload_avatar(self, request, pk=None):
        """Загрузка аватарки для клиента"""
        client = self.get_object()
        
        if 'avatar' not in request.FILES:
            return Response(
                {'error': 'Файл не найден'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['avatar']
        
        # Проверяем тип файла
        if not file.content_type.startswith('image/'):
            return Response(
                {'error': 'Можно загружать только изображения'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем размер (максимум 2MB)
        if file.size > 2 * 1024 * 1024:
            return Response(
                {'error': 'Изображение должно быть меньше 2MB'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Обрабатываем изображение
            img = Image.open(file)
            
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Ресайзим до 300x300
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Сохраняем в BytesIO
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            # Создаем имя файла
            filename = f"avatar_{client.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            # Сохраняем в модель
            client.avatar.save(filename, ContentFile(output.read()), save=True)
            
            return Response({
                'message': 'Аватарка успешно загружена',
                'avatar_url': client.avatar.url if client.avatar else None
            })
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка обработки изображения: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

class InteractionViewSet(viewsets.ModelViewSet):
    queryset = Interaction.objects.all()
    serializer_class = InteractionSerializer
    permission_classes = [permissions.IsAuthenticated]

# ===================== ДОБАВЛЯЕМ НОВЫЙ ViewSet =====================

class ScheduledEventViewSet(viewsets.ModelViewSet):
    """
    API для работы с запланированными событиями
    """
    queryset = ScheduledEvent.objects.all().order_by('scheduled_date')
    serializer_class = ScheduledEventSerializer
    # permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Фильтрация событий по параметрам запроса"""
        queryset = super().get_queryset()
        
        # Фильтр по статусу выполнения
        completed = self.request.query_params.get('completed')
        if completed is not None:
            if completed.lower() == 'true':
                queryset = queryset.filter(is_completed=True)
            elif completed.lower() == 'false':
                queryset = queryset.filter(is_completed=False)
        
        # Фильтр по клиенту
        client_id = self.request.query_params.get('client')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        # Фильтр по типу события
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Фильтр по дате (от и до)
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='complete')
    def mark_complete(self, request, pk=None):
        """Отметить событие как выполненное"""
        event = self.get_object()
        if event.is_completed:
            return Response(
                {'error': 'Событие уже выполнено'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.is_completed = True
        event.completed_at = timezone.now()
        event.save()
        
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='uncomplete')
    def mark_uncomplete(self, request, pk=None):
        """Отметить событие как невыполненное"""
        event = self.get_object()
        event.is_completed = False
        event.completed_at = None
        event.save()
        
        serializer = self.get_serializer(event)
        return Response(serializer.data)

    
from rest_framework import viewsets, permissions
from .models import MessageTemplate, BroadcastMessage
from .serializers import MessageTemplateSerializer, BroadcastMessageSerializer

class MessageTemplateViewSet(viewsets.ModelViewSet):
    queryset = MessageTemplate.objects.all()
    serializer_class = MessageTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

class BroadcastMessageViewSet(viewsets.ModelViewSet):
    queryset = BroadcastMessage.objects.all()
    serializer_class = BroadcastMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

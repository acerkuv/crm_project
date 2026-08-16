from rest_framework import serializers
from .models import MessageTemplate, BroadcastMessage

class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = '__all__'
        read_only_fields = ('created_at',)

class BroadcastMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BroadcastMessage
        fields = '__all__'
        read_only_fields = ('created_at', 'sent_at')

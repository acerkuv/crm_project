from rest_framework import serializers
from django.utils import timezone 
from .models import Client, Tag, Interaction, ScheduledEvent

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class InteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = '__all__'
        read_only_fields = ('created_at',)

class ScheduledEventSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.first_name', read_only=True)
    client_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ScheduledEvent
        fields = '__all__'
        read_only_fields = ('created_at', 'user')
    
    def get_client_full_name(self, obj):
        return f"{obj.client.first_name} {obj.client.last_name}".strip()

class ClientSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    interactions = InteractionSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField()
    days_until_birthday = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'user')
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_days_until_birthday(self, obj):
        if not obj.birth_date:
            return None
        from apps.bots.telegram.birthday_utils import days_until_birthday
        return days_until_birthday(obj.birth_date, timezone.now().date())
    
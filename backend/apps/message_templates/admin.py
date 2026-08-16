from django.contrib import admin
from .models import MessageTemplate, BroadcastMessage

@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'use_ai', 'created_at')
    search_fields = ('name', 'content')

@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ('template', 'sent_at', 'is_sent', 'created_at')
    list_filter = ('is_sent', 'created_at')

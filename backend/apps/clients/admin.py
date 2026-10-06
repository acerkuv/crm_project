from django.contrib import admin
from .models import Client, Tag, Interaction, ScheduledEvent

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'phone', 'email', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone', 'email', 'company')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('first_name', 'last_name', 'middle_name', 'phone', 'email', 'avatar')
        }),
        ('Дополнительная информация', {
            'fields': ('company', 'position', 'birth_date', 'comment')
        }),
        ('Мессенджеры', {
            'fields': ('telegram_id', 'max_id')
        }),
        ('Статус', {
            'fields': ('status', 'last_contact')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at', 'user')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'created_at')
    search_fields = ('name',)


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('client', 'type', 'created_at', 'scheduled_at', 'completed_at')
    list_filter = ('type', 'sent_via_telegram', 'sent_via_max')
    search_fields = ('client__first_name', 'client__last_name', 'content')


@admin.register(ScheduledEvent)
class ScheduledEventAdmin(admin.ModelAdmin):
    list_display = ('client', 'title', 'event_type', 'scheduled_date', 'is_completed', 'is_ai_generated')
    list_filter = ('event_type', 'is_completed', 'is_ai_generated')
    search_fields = ('client__first_name', 'client__last_name', 'title')
    readonly_fields = ('created_at',)

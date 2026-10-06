from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'event_date', 'is_completed')
    list_filter = ('is_completed', 'event_date')
    search_fields = ('title', 'client__first_name', 'client__last_name')

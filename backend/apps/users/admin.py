from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from .models import TelegramUser, LoginCode

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'telegram_id', 'user', 
        'subscription_plan',  # ДОБАВИЛИ subscription_plan в list_display
        'subscription_status_display',
        'clients_count',
        'is_active', 
        'created_at'
    )
    list_filter = ('subscription_plan', 'is_active', 'role')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'last_active')
    list_editable = ('subscription_plan', 'is_active')  # Теперь subscription_plan есть в list_display
    list_per_page = 25
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'telegram_id', 'username', 'first_name', 'last_name', 'phone')
        }),
        ('Права и доступ', {
            'fields': ('role', 'is_active', 'is_verified')
        }),
        ('📊 Подписка', {
            'fields': (
                'subscription_plan',
                'subscription_status_display',
                'subscription_expires_at',
                'subscription_auto_renew',
                'clients_count',
            ),
            'classes': ('wide',)
        }),
        ('💰 Лимиты и использование', {
            'fields': (
                'max_clients', 'max_events', 'max_ai_requests',
                'ai_requests_used', 'events_this_month', 'last_reset',
                'usage_stats_display'
            ),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'last_active'),
            'classes': ('collapse',)
        }),
    )

    def subscription_status_display(self, obj):
        """Отображение статуса подписки"""
        if obj.subscription_plan == 'free':
            return format_html('<span style="color: #52c41a;">✅ Активен</span>')
        
        if obj.is_subscription_active():
            days_left = (obj.subscription_expires_at - timezone.now()).days
            if days_left < 7:
                return format_html(
                    '<span style="color: #faad14;">⚠️ Истекает через {} дней</span>',
                    days_left
                )
            return format_html(
                '<span style="color: #52c41a;">✅ Активен (до {})</span>',
                obj.subscription_expires_at.strftime('%d.%m.%Y')
            )
        return format_html('<span style="color: #ff4d4f;">❌ Истекла</span>')
    subscription_status_display.short_description = 'Статус'

    def clients_count(self, obj):
        """Количество клиентов"""
        count = obj.user.clients.count() if obj.user else 0
        max_count = obj.max_clients or '∞'
        color = '#52c41a' if count < obj.max_clients else '#ff4d4f'
        return format_html(
            '<span style="color: {};">{} / {}</span>',
            color, count, max_count
        )
    clients_count.short_description = 'Клиенты'

    def usage_stats_display(self, obj):
        """Статистика использования"""
        stats = obj.get_usage_stats()
        
        return format_html(
            '''
            <div style="background: #f5f5f5; padding: 12px; border-radius: 4px;">
                <div style="margin-bottom: 4px;">
                    <strong>👥 Клиенты:</strong> {} / {} ({}%)
                </div>
                <div style="margin-bottom: 4px;">
                    <strong>📅 События (мес):</strong> {} / {} ({}%)
                </div>
                <div>
                    <strong>🤖 AI запросы (мес):</strong> {} / {} ({}%)
                </div>
            </div>
            ''',
            stats['clients']['used'],
            stats['clients']['max'] or '∞',
            round(stats['clients']['percent']),
            stats['events']['used'],
            stats['events']['max'] or '∞',
            round(stats['events']['percent']),
            stats['ai']['used'],
            stats['ai']['max'] or '∞',
            round(stats['ai']['percent']),
        )
    usage_stats_display.short_description = '📊 Использование'

@admin.register(LoginCode)
class LoginCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_user', 'code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used',)
    readonly_fields = ('created_at',)
    search_fields = ('telegram_user__telegram_id', 'code')
    raw_id_fields = ('telegram_user',)

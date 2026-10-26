from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TelegramUser(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='telegram_profile'
    )
    telegram_id = models.CharField(
        'Telegram ID',
        max_length=100,
        unique=True
    )
    username = models.CharField(
        'Username',
        max_length=100,
        blank=True,
        null=True
    )
    first_name = models.CharField(
        'Имя',
        max_length=100,
        default='Пользователь'
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=100,
        blank=True,
        null=True
    )
    phone = models.CharField(
        'Телефон',
        max_length=20,
        blank=True,
        null=True
    )
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=[
            ('owner', 'Владелец'),
            ('admin', 'Администратор'),
            ('manager', 'Менеджер'),
            ('viewer', 'Наблюдатель'),
        ],
        default='owner'
    )
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField('Последняя активность', default=timezone.now)
    
    # ============ ПЛАТНЫЕ ПОДПИСКИ ============
    SUBSCRIPTION_CHOICES = [
        ('free', 'Бесплатный'),
        ('basic', 'Базовый'),
        ('pro', 'Про'),
        ('enterprise', 'Корпоративный'),
    ]
    subscription_plan = models.CharField(
        'Тарифный план',
        max_length=20,
        choices=SUBSCRIPTION_CHOICES,
        default='free'
    )
    subscription_expires_at = models.DateTimeField(
        'Подписка действует до',
        null=True,
        blank=True
    )
    subscription_auto_renew = models.BooleanField(
        'Автопродление',
        default=False
    )
    
    # ============ ЛИМИТЫ ============
    max_clients = models.IntegerField(
        'Максимум клиентов',
        default=10,
        help_text='0 = безлимит'
    )
    max_events = models.IntegerField(
        'Максимум событий в месяц',
        default=50,
        help_text='0 = безлимит'
    )
    max_ai_requests = models.IntegerField(
        'Максимум AI запросов в месяц',
        default=0,
        help_text='0 = недоступно'
    )
    
    # ============ ИСПОЛЬЗОВАНИЕ ============
    ai_requests_used = models.IntegerField(
        'Использовано AI запросов в этом месяце',
        default=0
    )
    last_reset = models.DateTimeField(
        'Последний сброс лимитов',
        default=timezone.now
    )
    events_this_month = models.IntegerField(
        'Событий в этом месяце',
        default=0
    )
    
    class Meta:
        verbose_name = 'Пользователь Telegram'
        verbose_name_plural = 'Пользователи Telegram'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} (@{self.username or 'no_username'})"
    
    def get_full_name(self):
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    # ============ МЕТОДЫ ПОДПИСКИ ============
    
    def get_subscription_display(self):
        """Название тарифа"""
        return dict(self.SUBSCRIPTION_CHOICES).get(self.subscription_plan, 'Бесплатный')
    
    def is_subscription_active(self):
        """Проверка активности подписки"""
        if self.subscription_plan == 'free':
            return True
        if self.subscription_expires_at is None:
            return True  # бессрочная подписка (платная без даты = ок)
        return self.subscription_expires_at > timezone.now()
    
    def get_max_clients(self):
        """Получить максимальное количество клиентов"""
        limits = {
            'free': 10,
            'basic': 50,
            'pro': 200,
            'enterprise': 0,  # 0 = безлимит
        }
        return limits.get(self.subscription_plan, 10)
    
    def get_max_events(self):
        """Получить максимальное количество событий в месяц"""
        limits = {
            'free': 50,
            'basic': 200,
            'pro': 500,
            'enterprise': 0,  # 0 = безлимит
        }
        return limits.get(self.subscription_plan, 50)
    
    def get_max_ai_requests(self):
        """Получить максимальное количество AI запросов в месяц"""
        limits = {
            'free': 0,
            'basic': 10,
            'pro': 100,
            'enterprise': 1000,
        }
        return limits.get(self.subscription_plan, 0)
    
    def can_add_client(self):
        """Может ли пользователь добавить нового клиента"""
        if not self.is_subscription_active():
            return False
        max_clients = self.get_max_clients()
        if max_clients == 0:  # 0 = безлимит
            return True
        current_clients = self.user.clients.count()
        return current_clients < max_clients
    
    def can_add_event(self):
        """Может ли пользователь добавить новое событие"""
        if not self.is_subscription_active():
            return False
        max_events = self.get_max_events()
        if max_events == 0:  # 0 = безлимит
            return True
        
        # Сбрасываем счётчик если новый месяц
        self.reset_monthly_limits_if_needed()
        
        return self.events_this_month < max_events
    
    def can_use_ai(self):
        """Может ли пользователь использовать AI"""
        if not self.is_subscription_active():
            return False
        max_ai = self.get_max_ai_requests()
        if max_ai == 0:
            return False
        
        # Сбрасываем счётчик если новый месяц
        self.reset_monthly_limits_if_needed()
        
        return self.ai_requests_used < max_ai
    
    def reset_monthly_limits_if_needed(self):
        """Сбросить месячные лимиты если начался новый месяц"""
        now = timezone.now()
        if self.last_reset.month != now.month or self.last_reset.year != now.year:
            self.events_this_month = 0
            self.ai_requests_used = 0
            self.last_reset = now
            self.save(update_fields=['events_this_month', 'ai_requests_used', 'last_reset'])
    
    def increment_ai_usage(self):
        """Увеличить счётчик AI запросов"""
        self.reset_monthly_limits_if_needed()
        self.ai_requests_used += 1
        self.save(update_fields=['ai_requests_used'])
    
    def increment_event_usage(self):
        """Увеличить счётчик событий в месяце"""
        self.reset_monthly_limits_if_needed()
        self.events_this_month += 1
        self.save(update_fields=['events_this_month'])
    
    def get_usage_stats(self):
        """Получить статистику использования"""
        self.reset_monthly_limits_if_needed()
        
        clients = self.user.clients.count()
        max_clients = self.get_max_clients()
        
        return {
            'clients': {
                'used': clients,
                'max': max_clients if max_clients > 0 else None,
                'percent': (clients / max_clients * 100) if max_clients > 0 else 0,
            },
            'events': {
                'used': self.events_this_month,
                'max': self.get_max_events() if self.get_max_events() > 0 else None,
                'percent': (self.events_this_month / self.get_max_events() * 100) if self.get_max_events() > 0 else 0,
            },
            'ai': {
                'used': self.ai_requests_used,
                'max': self.get_max_ai_requests() if self.get_max_ai_requests() > 0 else None,
                'percent': (self.ai_requests_used / self.get_max_ai_requests() * 100) if self.get_max_ai_requests() > 0 else 0,
            },
            'plan': self.get_subscription_display(),
            'active': self.is_subscription_active(),
            'expires_at': self.subscription_expires_at,
        }

class LoginCode(models.Model):
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='login_codes'
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Код входа'
        verbose_name_plural = 'Коды входа'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.telegram_user.telegram_id} - {self.code}"
    
    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

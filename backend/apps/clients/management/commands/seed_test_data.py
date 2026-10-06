"""
Management-команда для наполнения БД тестовыми данными.

Примеры:
    python manage.py seed_test_data
    python manage.py seed_test_data --clients 50 --events 100
    python manage.py seed_test_data --clear
"""

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from apps.clients.models import Client, Tag, Interaction, ScheduledEvent


FIRST_NAMES_M = ['Александр', 'Дмитрий', 'Сергей', 'Андрей', 'Максим', 'Иван',
                 'Михаил', 'Николай', 'Евгений', 'Владимир', 'Артём', 'Роман',
                 'Павел', 'Денис', 'Кирилл', 'Антон', 'Виктор', 'Григорий']
FIRST_NAMES_F = ['Анна', 'Мария', 'Елена', 'Ольга', 'Наталья', 'Татьяна',
                 'Ирина', 'Екатерина', 'Светлана', 'Юлия', 'Дарья', 'Ксения',
                 'Алиса', 'Полина', 'София', 'Вероника', 'Виктория', 'Алиса']
LAST_NAMES_M = ['Иванов', 'Петров', 'Смирнов', 'Кузнецов', 'Соколов', 'Попов',
                'Лебедев', 'Козлов', 'Новиков', 'Морозов', 'Волков', 'Соловьёв',
                'Васильев', 'Зайцев', 'Павлов', 'Семёнов', 'Голубев', 'Виноградов']
LAST_NAMES_F = ['Иванова', 'Петрова', 'Смирнова', 'Кузнецова', 'Соколова', 'Попова',
                'Лебедева', 'Козлова', 'Новикова', 'Морозова', 'Волкова', 'Соловьёва',
                'Васильева', 'Зайцева', 'Павлова', 'Семёнова', 'Голубева', 'Виноградова']
MIDDLE_NAMES_M = ['Александрович', 'Дмитриевич', 'Сергеевич', 'Андреевич',
                  'Максимович', 'Иванович', 'Михайлович', 'Николаевич']
MIDDLE_NAMES_F = ['Александровна', 'Дмитриевна', 'Сергеевна', 'Андреевна',
                  'Максимовна', 'Ивановна', 'Михайловна', 'Николаевна']

COMPANIES = ['ООО Ромашка', 'ИП Смирнов', 'АО ТехноПром', 'ООО СтройМастер',
             'ИП Кузнецова', 'ЗАО АвтоТрейд', 'ООО МедСервис', 'ООО Логистика+',
             'ИП Петров', 'ООО СтройИнвест', 'ООО Мебель-Сити', 'АО ЭнергоСбыт']

POSITIONS = ['Директор', 'Менеджер', 'Бухгалтер', 'Инженер', 'Руководитель отдела',
             'Специалист', 'Аналитик', 'Логист', 'Маркетолог', 'Юрист']

TAGS = [
    ('VIP', '#dc3545'),
    ('Постоянный', '#28a745'),
    ('Новый', '#17a2b8'),
    ('Проблемный', '#ffc107'),
    ('Оптовик', '#6f42c1'),
    ('Розница', '#fd7e14'),
    ('Онлайн', '#20c997'),
    ('Офлайн', '#6c757d'),
    ('Рекомендация', '#007bff'),
    ('Реклама', '#e83e8c'),
]

INTERACTION_CONTENTS = {
    'call': ['Обсудили условия поставки', 'Уточнили сроки', 'Договорились о встрече',
             'Подтвердили заказ', 'Обсудили цены', 'Уточнили детали договора'],
    'message': ['Отправили коммерческое предложение', 'Напомнили о встрече',
                'Скинули прайс-лист', 'Поздравили с праздником'],
    'meeting': ['Провели переговоры в офисе', 'Встретились на выставке',
                'Подписали договор', 'Обсудили планы на квартал'],
    'email': ['Отправили счёт', 'Подтвердили заказ по email', 'Выслали документацию'],
    'note': ['Клиент просил перезвонить через неделю', 'Уточнить наличие товара',
             'Согласовать скидку с руководством', 'Подготовить КП'],
    'birthday': ['Поздравили с днём рождения', 'Отправили открытку'],
    'reminder': ['Напомнили про оплату', 'Напомнили про встречу'],
}

EVENT_TITLES = {
    'call': ['Звонок клиенту', 'Обсудить заказ', 'Уточнить детали', 'Перезвонить'],
    'meeting': ['Встреча в офисе', 'Переговоры', 'Презентация', 'Обсуждение договора'],
    'birthday': ['День рождения клиента', 'Поздравить'],
    'reminder': ['Напомнить про оплату', 'Напомнить о встрече', 'Проверить статус заказа'],
    'custom': ['Отправить документы', 'Подготовить КП', 'Согласовать скидку'],
}


class Command(BaseCommand):
    help = 'Наполнить БД тестовыми данными (клиенты, события, взаимодействия, теги)'

    def add_arguments(self, parser):
        parser.add_argument('--clients', type=int, default=30,
                            help='Сколько клиентов создать (по умолчанию 30)')
        parser.add_argument('--events', type=int, default=50,
                            help='Сколько событий создать (по умолчанию 50)')
        parser.add_argument('--interactions', type=int, default=100,
                            help='Сколько взаимодействий создать (по умолчанию 100)')
        parser.add_argument('--clear', action='store_true',
                            help='Удалить все созданные тестовые данные')

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        if options['clear']:
            self._clear()
            return

        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stderr.write(self.style.ERROR('Нет суперпользователя — создай сначала admin'))
            return

        self.stdout.write(self.style.WARNING(f'Используем пользователя: {user.username}'))

        tags = self._create_tags()
        self.stdout.write(self.style.SUCCESS(f'✓ Создано тегов: {len(tags)}'))

        clients = self._create_clients(user, tags, options['clients'])
        self.stdout.write(self.style.SUCCESS(f'✓ Создано клиентов: {len(clients)}'))

        events = self._create_events(user, clients, options['events'])
        self.stdout.write(self.style.SUCCESS(f'✓ Создано событий: {len(events)}'))

        interactions = self._create_interactions(clients, options['interactions'])
        self.stdout.write(self.style.SUCCESS(f'✓ Создано взаимодействий: {len(interactions)}'))

        self.stdout.write(self.style.SUCCESS('\n🎉 Готово! Проверь в админке.'))

    def _clear(self):
        self.stdout.write(self.style.WARNING('Удаляем тестовые данные...'))
        ScheduledEvent.objects.all().delete()
        Interaction.objects.all().delete()
        Client.objects.all().delete()
        Tag.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✓ Все тестовые данные удалены'))

    def _create_tags(self):
        tags = []
        for name, color in TAGS:
            tag, _ = Tag.objects.get_or_create(name=name, defaults={'color': color})
            tags.append(tag)
        return tags

    def _create_clients(self, user, tags, count):
        clients = []
        for i in range(count):
            is_female = random.choice([True, False])
            if is_female:
                first = random.choice(FIRST_NAMES_F)
                last = random.choice(LAST_NAMES_F)
                middle = random.choice(MIDDLE_NAMES_F)
            else:
                first = random.choice(FIRST_NAMES_M)
                last = random.choice(LAST_NAMES_M)
                middle = random.choice(MIDDLE_NAMES_M)

            phone = f'+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}'
            email = f'{first.lower()}.{last.lower()}{i}@example.com'

            days_old = random.randint(25 * 365, 65 * 365)
            birth = timezone.now().date() - timedelta(days=days_old)

            client = Client.objects.create(
                user=user,
                first_name=first,
                last_name=last,
                middle_name=middle,
                phone=phone,
                email=email,
                birth_date=birth,
                company=random.choice(COMPANIES),
                position=random.choice(POSITIONS),
                status=random.choice(['lead', 'active', 'regular', 'vip', 'inactive']),
                comment=random.choice(['', 'Постоянный клиент', 'Интересуется оптом',
                                       'Просил скидку', 'Нашёл через рекламу', '']),
                telegram_id=str(random.randint(100000000, 999999999)) if random.random() > 0.5 else '',
                last_contact=timezone.now() - timedelta(days=random.randint(0, 60)),
            )
            client.tags.set(random.sample(tags, random.randint(0, 3)))
            clients.append(client)
        return clients

    def _create_events(self, user, clients, count):
        events = []
        for _ in range(count):
            client = random.choice(clients)
            event_type = random.choice(['call', 'meeting', 'birthday', 'reminder', 'custom'])
            title = random.choice(EVENT_TITLES[event_type])

            offset_days = random.randint(-30, 30)
            scheduled_date = timezone.now() + timedelta(days=offset_days, hours=random.randint(-5, 5))

            is_completed = offset_days < 0
            is_ai = random.random() > 0.7

            event = ScheduledEvent.objects.create(
                user=user,
                client=client,
                title=title,
                description=random.choice(['', 'Обсудить детали', 'Подготовиться заранее',
                                           'Согласовать с руководством', '']),
                event_type=event_type,
                scheduled_date=scheduled_date,
                is_completed=is_completed,
                is_ai_generated=is_ai,
                ai_content='Сгенерировано ИИ: ' + random.choice(['напомнить', 'подготовить', 'уточнить']) if is_ai else '',
                completed_at=scheduled_date if is_completed else None,
            )
            events.append(event)
        return events

    def _create_interactions(self, clients, count):
        interactions = []
        for _ in range(count):
            client = random.choice(clients)
            i_type = random.choice(['call', 'message', 'meeting', 'email', 'note',
                                    'birthday', 'reminder'])
            content = random.choice(INTERACTION_CONTENTS[i_type])

            created_at = timezone.now() - timedelta(days=random.randint(1, 60), hours=random.randint(0, 23))
            is_completed = random.random() > 0.2

            interaction = Interaction.objects.create(
                client=client,
                type=i_type,
                content=content,
                created_at=created_at,
                scheduled_at=created_at,
                completed_at=created_at if is_completed else None,
                is_ai_generated=random.random() > 0.8,
                sent_via_telegram=random.random() > 0.5,
                sent_via_max=random.random() > 0.8,
            )
            interactions.append(interaction)
        return interactions
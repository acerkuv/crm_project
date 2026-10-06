#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import django
from datetime import datetime, timedelta

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.clients.models import Client, Tag, Interaction
from apps.events.models import Event
from django.utils import timezone

User = get_user_model()

def create_test_data():
    """Создание тестовых данных"""
    print("📊 Загрузка тестовых данных...")
    
    # Получаем пользователя
    user = User.objects.first()
    if not user:
        print("❌ Пользователь не найден! Сначала создайте суперпользователя.")
        return
    
    print(f"👤 Пользователь: {user.username}")
    
    # Создаем теги
    tags_data = [
        {'name': 'VIP', 'color': '#FFD700'},
        {'name': 'Партнер', 'color': '#00BFFF'},
        {'name': 'Постоянный', 'color': '#FF6B6B'},
        {'name': 'Новый', 'color': '#32CD32'},
        {'name': 'Важный', 'color': '#FF4500'},
    ]
    
    tags = []
    for tag_data in tags_data:
        tag, created = Tag.objects.get_or_create(
            name=tag_data['name'],
            defaults={'color': tag_data['color']}
        )
        tags.append(tag)
        print(f"  {'✅' if created else '🔄'} Тег: {tag.name}")
    
    # Создаем клиентов
    clients_data = [
        {
            'first_name': 'Анна',
            'last_name': 'Смирнова',
            'phone': '+79161234567',
            'email': 'anna.smirnova@example.com',
            'birth_date': '1985-08-15',
            'company': 'ООО ТехноПро',
            'position': 'CEO',
            'comment': 'Любит современные технологии и кофе. Постоянный партнер.',
            'status': 'vip',
            'tags': ['VIP', 'Партнер']
        },
        {
            'first_name': 'Михаил',
            'last_name': 'Иванов',
            'phone': '+79269876543',
            'email': 'mikhail.ivanov@example.com',
            'birth_date': '1990-03-22',
            'company': 'ИП Иванов',
            'position': 'Владелец',
            'comment': 'Интересуется новыми разработками. Активный клиент.',
            'status': 'active',
            'tags': ['Постоянный']
        },
        {
            'first_name': 'Елена',
            'last_name': 'Козлова',
            'phone': '+79265554433',
            'email': 'elena.kozlova@example.com',
            'birth_date': '1978-12-01',
            'company': 'ООО БухгалтерСервис',
            'position': 'Главный бухгалтер',
            'comment': 'Постоянный клиент, нуждается в индивидуальном подходе.',
            'status': 'regular',
            'tags': ['Постоянный', 'Важный']
        },
        {
            'first_name': 'Петр',
            'last_name': 'Сидоров',
            'phone': '+79265556677',
            'email': 'petr.sidorov@example.com',
            'birth_date': '1980-11-05',
            'company': 'ООО СтройИнвест',
            'position': 'Директор',
            'comment': 'Постоянный партнер. Строительная компания.',
            'status': 'regular',
            'tags': ['Партнер']
        },
        {
            'first_name': 'Ольга',
            'last_name': 'Петрова',
            'phone': '+79169876543',
            'email': 'olga.petrova@example.com',
            'birth_date': '1995-07-20',
            'company': 'ООО МаркетингПро',
            'position': 'Маркетолог',
            'comment': 'Новый клиент. Интересуется digital-услугами.',
            'status': 'lead',
            'tags': ['Новый']
        },
        {
            'first_name': 'Дмитрий',
            'last_name': 'Соколов',
            'phone': '+79263332211',
            'email': 'dmitry.sokolov@example.com',
            'birth_date': '1988-09-15',
            'company': 'ООО Инновации',
            'position': 'Технический директор',
            'comment': 'Технический партнер. IT-интеграции.',
            'status': 'vip',
            'tags': ['VIP', 'Партнер']
        },
        {
            'first_name': 'Наталья',
            'last_name': 'Морозова',
            'phone': '+79163334455',
            'email': 'natalia.morozova@example.com',
            'birth_date': '1992-04-10',
            'company': 'ООО Консалтинг',
            'position': 'Консультант',
            'comment': 'Постоянный клиент. Консультационные услуги.',
            'status': 'active',
            'tags': ['Постоянный']
        },
        {
            'first_name': 'Алексей',
            'last_name': 'Волков',
            'phone': '+79266667788',
            'email': 'alexey.volkov@example.com',
            'birth_date': '1983-06-25',
            'company': 'ИП Волков',
            'position': 'Директор',
            'comment': 'Важный клиент. Требует внимания.',
            'status': 'vip',
            'tags': ['VIP', 'Важный']
        }
    ]
    
    created_clients = []
    for client_data in clients_data:
        tag_names = client_data.pop('tags', [])
        client, created = Client.objects.get_or_create(
            phone=client_data['phone'],
            defaults={
                **client_data,
                'user': user
            }
        )
        
        if created:
            # Добавляем теги
            for tag_name in tag_names:
                tag = Tag.objects.filter(name=tag_name).first()
                if tag:
                    client.tags.add(tag)
            created_clients.append(client)
            print(f"  ✅ Клиент: {client.first_name} {client.last_name} ({client.phone})")
        else:
            print(f"  🔄 Клиент уже существует: {client.first_name} {client.last_name}")
    
    # Создаем события
    events_data = [
        {
            'client': Client.objects.get(phone='+79161234567'),
            'title': 'Презентация нового продукта',
            'description': 'Показать новый функционал CRM для Анны',
            'event_date': timezone.now() + timedelta(days=3),
            'is_completed': False
        },
        {
            'client': Client.objects.get(phone='+79269876543'),
            'title': 'Встреча по сотрудничеству',
            'description': 'Обсудить новые условия работы',
            'event_date': timezone.now() + timedelta(days=5),
            'is_completed': False
        },
        {
            'client': Client.objects.get(phone='+79265554433'),
            'title': 'Консультация по бухгалтерии',
            'description': 'Подготовка отчетности',
            'event_date': timezone.now() + timedelta(days=7),
            'is_completed': False
        }
    ]
    
    for event_data in events_data:
        event, created = Event.objects.get_or_create(
            title=event_data['title'],
            defaults=event_data
        )
        if created:
            print(f"  ✅ Событие: {event.title}")
        else:
            print(f"  🔄 Событие уже существует: {event.title}")
    
    # Создаем взаимодействия
    print("\n📝 Создание взаимодействий...")
    
    # Для каждого клиента создаем историю взаимодействий
    for client in Client.objects.all():
        interactions = [
            {
                'type': 'call',
                'content': f'Первичный звонок клиенту {client.first_name}',
                'created_at': timezone.now() - timedelta(days=10)
            },
            {
                'type': 'message',
                'content': f'Отправлено коммерческое предложение',
                'created_at': timezone.now() - timedelta(days=7)
            },
            {
                'type': 'note',
                'content': f'Заметка: {client.first_name} интересуется продуктом',
                'created_at': timezone.now() - timedelta(days=3)
            }
        ]
        
        for inter_data in interactions:
            Interaction.objects.get_or_create(
                client=client,
                type=inter_data['type'],
                content=inter_data['content'],
                defaults={'created_at': inter_data['created_at']}
            )
        print(f"  ✅ Взаимодействия для {client.first_name} {client.last_name}")
    
    print("\n" + "="*50)
    print("📊 СТАТИСТИКА:")
    print(f"  👥 Клиентов: {Client.objects.count()}")
    print(f"  🏷️ Тегов: {Tag.objects.count()}")
    print(f"  📅 Событий: {Event.objects.count()}")
    print(f"  💬 Взаимодействий: {Interaction.objects.count()}")
    print("="*50)
    print("\n✅ Тестовые данные загружены успешно!")

if __name__ == "__main__":
    create_test_data()

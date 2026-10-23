"""Сервисы для работы с карточкой клиента (используются ботом и API)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.db import transaction

from .models import Client, CustomField, Interaction

logger = logging.getLogger(__name__)

EDITABLE_CLIENT_FIELDS = {
    'first_name', 'last_name', 'middle_name', 'phone', 'email',
    'birth_date', 'company', 'position', 'comment', 'hobby',
    'address', 'status',
}

FIELD_LABELS_RU = {
    'first_name': 'Имя', 'last_name': 'Фамилия', 'middle_name': 'Отчество',
    'phone': 'Телефон', 'email': 'Email', 'birth_date': 'Дата рождения',
    'company': 'Компания', 'position': 'Должность', 'comment': 'Комментарий',
    'hobby': 'Хобби', 'address': 'Адрес', 'status': 'Статус',
}


@transaction.atomic
def create_client_full(data: dict[str, Any]) -> Client:
    custom = data.pop('custom_fields', []) or []
    birth = data.get('birth_date')
    if isinstance(birth, str) and birth:
        try:
            data['birth_date'] = datetime.strptime(birth, '%Y-%m-%d').date()
        except ValueError:
            data['birth_date'] = None
    if not data.get('phone'):
        from django.utils import timezone
        data['phone'] = f"unknown_{int(timezone.now().timestamp())}"

    client = Client.objects.create(**data)
    for cf in custom:
        if cf.get('name'):
            CustomField.objects.create(
                client=client, name=cf['name'],
                field_type=cf.get('field_type', 'text'),
                value=str(cf.get('value', '')),
            )
    return client


def update_client_field(client: Client, field: str, value: Any) -> Client:
    if field not in EDITABLE_CLIENT_FIELDS:
        raise ValueError(f"Поле '{field}' не редактируется")
    if field == 'birth_date':
        if value in (None, '', '—'):
            value = None
        elif isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m-%d').date()
    if field == 'status':
        valid = dict(Client._meta.get_field('status').choices)
        if value not in valid:
            raise ValueError(f"Неизвестный статус: {value}")
    setattr(client, field, value or (None if field == 'birth_date' else ''))
    client.save(update_fields=[field, 'updated_at'])
    return client


def add_note(client: Client, text: str) -> Interaction:
    return Interaction.objects.create(client=client, type='note', content=text)


def list_notes(client: Client, include_deleted: bool = False):
    qs = Interaction.objects.filter(client=client, type='note')
    if not include_deleted:
        qs = qs.filter(is_deleted=False)
    return qs.order_by('-created_at')


def delete_note(note_id: int) -> bool:
    return bool(Interaction.objects.filter(
        id=note_id, type='note', is_deleted=False
    ).update(is_deleted=True))


def set_custom_field(client, name: str, value: str, field_type: str = 'text') -> CustomField:
    obj, _ = CustomField.objects.update_or_create(
        client=client, name=name,
        defaults={'value': value, 'field_type': field_type},
    )
    return obj


def delete_custom_field(client, name: str) -> bool:
    deleted, _ = CustomField.objects.filter(client=client, name=name).delete()
    return bool(deleted)
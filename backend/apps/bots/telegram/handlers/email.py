"""Mixin: email."""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.clients.models import Client, Interaction, ScheduledEvent

logger = logging.getLogger(__name__)


class EmailMixin:
    """Методы: email."""
    pass

"""Mixin-модули для TelegramBot.

Каждый файл — отдельный класс с методами для одного сценария.
TelegramBot наследует их все:

    class TelegramBot(
        HelpersMixin,
        CommandsMixin,
        PhotosMixin,
        ClientsMixin,
        EventsMixin,
        EmailMixin,
        CallbacksMixin,
    ):
        def __init__(self):
            ...
"""

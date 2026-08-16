#!/bin/bash

# Переименовываем приложение messages -> message_templates
mv backend/apps/messages backend/apps/message_templates

# Обновляем imports во всех файлах
find backend -type f -name "*.py" -exec sed -i 's/apps\.messages/apps.message_templates/g' {} \;
find backend -type f -name "*.py" -exec sed -i "s/'apps.messages'/'apps.message_templates'/g" {} \;
find backend -type f -name "*.py" -exec sed -i 's/apps\.messages/apps.message_templates/g' {} \;

# Обновляем название приложения в apps.py
cat > backend/apps/message_templates/apps.py << 'EOF'
from django.apps import AppConfig

class MessageTemplatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.message_templates'
    verbose_name = 'Шаблоны сообщений'

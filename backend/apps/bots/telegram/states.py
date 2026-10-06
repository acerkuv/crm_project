# Хранилище состояний пользователей
user_states = {}

def clear_user_state(chat_id):
    """Очистка состояния пользователя"""
    if chat_id in user_states:
        del user_states[chat_id]

def get_user_state(chat_id):
    """Получение состояния пользователя"""
    return user_states.get(chat_id, {})

def set_user_state(chat_id, state):
    """Установка состояния пользователя"""
    user_states[chat_id] = state

def update_user_state(chat_id, **kwargs):
    """Обновление состояния пользователя"""
    if chat_id not in user_states:
        user_states[chat_id] = {}
    user_states[chat_id].update(kwargs)

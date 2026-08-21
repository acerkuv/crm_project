from django.db import connection

with connection.cursor() as cursor:
    cursor.execute('DROP TABLE IF EXISTS users_telegramuser CASCADE')
    cursor.execute('DROP TABLE IF EXISTS users_logincode CASCADE')
    cursor.execute("DELETE FROM django_migrations WHERE app = 'users'")
    
    cursor.execute("""
        CREATE TABLE users_telegramuser (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
            telegram_id VARCHAR(100) NOT NULL UNIQUE,
            username VARCHAR(100) NULL,
            first_name VARCHAR(100) NOT NULL DEFAULT 'Пользователь',
            last_name VARCHAR(100) NULL,
            phone VARCHAR(20) NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'owner',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_active TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    
    cursor.execute("""
        CREATE TABLE users_logincode (
            id SERIAL PRIMARY KEY,
            telegram_user_id INTEGER NOT NULL REFERENCES users_telegramuser(id) ON DELETE CASCADE,
            code VARCHAR(6) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            is_used BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    
    print('✅ Tables created successfully!')

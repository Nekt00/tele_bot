-- Создание таблиц при инициализации БД
CREATE TABLE IF NOT EXISTS sessions (
    user_id BIGINT PRIMARY KEY,
    step INTEGER DEFAULT 0,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username VARCHAR(255),
    group_chat_id BIGINT,
    router_model TEXT,
    firmware TEXT,
    protocol TEXT,
    os TEXT,
    problem_description TEXT,
    extra_data JSONB,
    ticket_type VARCHAR(50) DEFAULT 'quiz',
    status VARCHAR(50) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_groups (
    chat_id BIGINT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    invite_link VARCHAR(512),
    is_active BOOLEAN DEFAULT TRUE,
    member_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_group_chat_id ON tickets(group_chat_id);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_bot_groups_is_active ON bot_groups(is_active);

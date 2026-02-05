# 🤖 Aunt Polly Bot

**Telegram бот для поддержки пользователей с AI-ассистентом, админ-панелью и защитой от спама.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.4+-green.svg)](https://aiogram.dev)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📑 Содержание

- [Возможности](#-возможности)
- [Системные требования](#-системные-требования)
- [Быстрая установка](#-быстрая-установка-docker)
- [Ручная установка](#-ручная-установка-без-docker)
- [Продакшен с Caddy](#-продакшен-с-caddy)
- [Продакшен с Nginx](#-продакшен-с-nginx)
- [Конфигурация](#️-конфигурация)
- [Использование](#-использование)
- [Документация](#-документация)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Возможности

### 🎛️ Админ-панель
- **Дашборд** — статистика в реальном времени
- **Управление пользователями** — список, блокировка, прямые сообщения
- **Рассылка** — массовые уведомления с историей
- **Бэкапы** — автоматические ежедневные и ручные, с восстановлением

### 🗂️ FAQ-система
- Автоматический поиск по базе знаний (fuzzy matching)
- Настраиваемый порог сходства (10-100%)
- Поддержка медиа-файлов (фото, видео, документы)

### 🧠 Искусственный интеллект
- **Groq** — Llama 3.3 70B, Mixtral 8x7B (быстрые ответы)
- **Google Gemini** — Gemini 1.5 Flash/Pro (расширенные возможности)
- Настраиваемый системный промпт
- Автоматический fallback между моделями

### 🛡️ Многоуровневая защита
- **Уровень 1**: Reverse Proxy (Nginx/Caddy) — Rate limiting, IP filtering
- **Уровень 2**: Webhook Secret Token — проверка подлинности
- **Уровень 3**: Rate Limiter в боте — Token Bucket алгоритм
- **Уровень 4**: User Manager — ручная блокировка, auto-ban

### 🌍 Мультиязычность
- 🇷🇺 Русский, 🇬🇧 English, 🇺🇦 Українська
- Автоопределение языка из Telegram

---

## 💻 Системные требования

### Поддерживаемые ОС

| ОС | Версия | Статус |
|----|--------|:------:|
| **Ubuntu** | 20.04, 22.04, 24.04 LTS | ✅ Рекомендуется |
| **Debian** | 11, 12 | ✅ Рекомендуется |
| **CentOS/Rocky/Alma** | 8, 9 | ✅ Поддерживается |

### Минимальные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| **CPU** | 1 vCPU | 2 vCPU |
| **RAM** | 512 MB | 1 GB |
| **Диск** | 5 GB SSD | 10 GB SSD |

---

## 🚀 Быстрая установка (Docker)

Самый простой способ — не требует домен.

### Ubuntu / Debian

```bash
# 1. Установите Docker
sudo apt update
sudo curl -fsSL https://get.docker.com | sh

# 2. Клонируйте репозиторий
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

# 3. Создайте конфигурацию
cp env.example .env
nano .env
```

Заполните обязательные поля в `.env`:
```env
BOT_TOKEN=123456789:AABBccDDeeFFggHHiiJJkkLLmmNNoo
ADMIN_ID=123456789
BOT_MODE=polling
```

```bash
# 4. Запустите
sudo docker compose up -d

# 5. Проверьте логи
sudo docker compose logs -f

# 6. Готово! Отправьте /admin боту
```

**Управление:**
```bash
sudo docker compose down      # Остановить
sudo docker compose restart   # Перезапустить
sudo docker compose logs -f   # Логи
```

---

## 🔧 Ручная установка (без Docker)

Для разработки или когда Docker недоступен.

### Ubuntu / Debian

```bash
# 1. Обновите систему
sudo apt update && sudo apt upgrade -y

# 2. Установите Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip git

# 3. Клонируйте репозиторий
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

# 4. Создайте виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# 5. Установите зависимости
pip install --upgrade pip
pip install -r bot/requirements.txt

# 6. Настройте конфигурацию
cp env.example .env
nano .env

# 7. Запустите бота
python main.py
```

### Запуск как systemd-сервис

```bash
# Создайте файл сервиса
sudo nano /etc/systemd/system/aunt-polly-bot.service
```

```ini
[Unit]
Description=Aunt Polly Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/aunt-polly-bot
Environment=PATH=/home/YOUR_USER/aunt-polly-bot/venv/bin
ExecStart=/home/YOUR_USER/aunt-polly-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Активируйте и запустите
sudo systemctl daemon-reload
sudo systemctl enable aunt-polly-bot
sudo systemctl start aunt-polly-bot

# Проверьте статус
sudo systemctl status aunt-polly-bot
```

---

## 🌐 Продакшен с Caddy

**Caddy** автоматически получает SSL-сертификаты от Let's Encrypt.

### Требования
- VPS с публичным IP
- Домен с A-записью на IP сервера
- Открытые порты 80 и 443

### Установка

```bash
# 1. Установите Docker (если не установлен)
sudo curl -fsSL https://get.docker.com | sh

# 2. Клонируйте репозиторий
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

# 3. Настройте .env для webhook
cp env.example .env
nano .env
```

Заполните `.env`:
```env
# Основные
BOT_TOKEN=YOUR_BOT_TOKEN
ADMIN_ID=YOUR_TELEGRAM_ID

# Режим webhook
BOT_MODE=webhook
WEBHOOK_HOST=https://bot.yourdomain.com
WEBHOOK_PATH=/bot/
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=8081

# Безопасность (сгенерируйте: openssl rand -hex 32)
WEBHOOK_SECRET_TOKEN=your_secret_token_here
```

```bash
# 4. Настройте Caddyfile
nano Caddyfile
```

Пример `Caddyfile`:
```caddyfile
{
    email your@email.com
}

bot.yourdomain.com {
    handle_path /bot/* {
        reverse_proxy aunt-polly-bot:8081
    }
    handle {
        respond "Not Found" 404
    }
}
```

```bash
# 5. Запустите с профилем caddy
sudo docker compose --profile caddy up -d

# 6. Проверьте логи
sudo docker compose logs caddy
sudo docker compose logs aunt-polly-bot

# 7. Проверьте webhook
curl https://bot.yourdomain.com/bot/health
```

---

## ⚙️ Продакшен с Nginx

**Nginx** требует ручной настройки SSL-сертификатов.

### Требования
- VPS с публичным IP
- Домен с A-записью на IP сервера
- Открытые порты 80 и 443

### Установка

```bash
# 1. Установите Docker (если не установлен)
sudo curl -fsSL https://get.docker.com | sh

# 2. Клонируйте репозиторий
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

# 3. Настройте .env для webhook
cp env.example .env
nano .env
```

Заполните `.env`:
```env
# Основные
BOT_TOKEN=YOUR_BOT_TOKEN
ADMIN_ID=YOUR_TELEGRAM_ID

# Режим webhook
BOT_MODE=webhook
WEBHOOK_HOST=https://bot.yourdomain.com
WEBHOOK_PATH=/bot/
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=8081

# Безопасность
WEBHOOK_SECRET_TOKEN=your_secret_token_here
```

```bash
# 4. Настройте nginx.conf
nano nginx/nginx.conf
```

Замените `BOTDOMAIN.COM` на ваш домен:
```nginx
# HTTP -> HTTPS редирект
server {
    listen 80;
    listen [::]:80;
    server_name bot.yourdomain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name bot.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/bot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.yourdomain.com/privkey.pem;
    
    location /bot/ {
        proxy_pass http://aunt-polly-bot:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location / {
        return 404;
    }
}
```

```bash
# 5. Запустите временно nginx для получения сертификата
sudo docker compose up -d aunt-polly-bot
sudo docker compose up -d nginx

# 6. Получите SSL-сертификат
sudo docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d bot.yourdomain.com \
  --email your@email.com \
  --agree-tos \
  --no-eff-email

# 7. Перезапустите nginx
sudo docker compose restart nginx

# 8. Проверьте webhook
curl https://bot.yourdomain.com/bot/health
```

**Обновление сертификата (автоматически каждые 12 часов):**
```bash
# Сертификаты обновляются автоматически контейнером certbot
sudo docker compose logs certbot
```

---

## ⚙️ Конфигурация

### Получение токенов

#### Telegram Bot Token
1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите имя и username бота
4. Скопируйте токен

#### Ваш Telegram ID
1. Откройте [@userinfobot](https://t.me/userinfobot)
2. Отправьте `/start`
3. Скопируйте ID

#### Groq API Key (бесплатно)
1. Зарегистрируйтесь на [console.groq.com](https://console.groq.com)
2. Создайте API ключ

#### Google Gemini API Key (бесплатно)
1. Откройте [aistudio.google.com](https://aistudio.google.com)
2. Создайте API ключ

#### Webhook Secret Token
```bash
openssl rand -hex 32
```

---

## 📖 Использование

### Команды бота

#### Для пользователей
| Команда | Описание |
|---------|----------|
| `/start` | Начать диалог |
| `/help` | Показать справку |
| `/faq` | Список FAQ |

#### Для администратора
| Команда | Описание |
|---------|----------|
| `/admin` | Открыть админ-панель |
| `/stats` | Быстрая статистика |
| `/backup` | Создать бэкап |

### Health Check

```bash
# Локально
curl http://localhost:8081/health

# Продакшен
curl https://bot.yourdomain.com/bot/health
```

---

## 📚 Документация

| Документ | Описание |
|----------|----------|
| [ADMIN_PANEL_GUIDE.md](ADMIN_PANEL_GUIDE.md) | Руководство по админ-панели |
| [SECURITY.md](SECURITY.md) | Настройка защиты |
| [env.example](env.example) | Пример конфигурации |

---

## 🔧 Troubleshooting

### Бот не отвечает

```bash
# Проверьте статус
sudo docker compose ps

# Проверьте логи
sudo docker compose logs aunt-polly-bot

# Проверьте .env
cat .env | grep -E "BOT_TOKEN|ADMIN_ID"
```

**Частые причины:**
- Неверный `BOT_TOKEN`
- Неверный `ADMIN_ID`
- Бот не запущен

### Webhook не работает

```bash
# Проверьте DNS
dig bot.yourdomain.com +short

# Проверьте SSL
curl -I https://bot.yourdomain.com

# Проверьте endpoint
curl https://bot.yourdomain.com/bot/health

# Проверьте логи
sudo docker compose logs caddy  # или nginx
```

**Частые причины:**
- DNS не настроен
- Порты 80/443 закрыты
- Неверный домен в конфигурации
- SSL-сертификат не получен

### Проблема с Nginx

Если при запуске Nginx возникает ошибка:

```bash
# 1. Проверьте, что nginx.conf корректен
sudo docker compose config

# 2. Убедитесь, что домен указан правильно
grep "server_name" nginx/nginx.conf

# 3. Проверьте, что порты свободны
sudo netstat -tulpn | grep -E ':80|:443'

# 4. Для первого запуска временно закомментируйте SSL
# в nginx.conf и получите сертификат, затем раскомментируйте
```

**Порядок первого запуска с Nginx:**

1. В `nginx.conf` временно оставьте только HTTP (порт 80)
2. Запустите контейнеры: `sudo docker compose --profile nginx up -d`
3. Получите сертификат через certbot
4. Раскомментируйте HTTPS в `nginx.conf`
5. Перезапустите: `sudo docker compose restart nginx`

---

## 🔄 Обновление

```bash
cd aunt-polly-bot
git pull

# Для polling
sudo docker compose down
sudo docker compose up -d --build

# Для Caddy
sudo docker compose --profile caddy down
sudo docker compose --profile caddy up -d --build

# Для Nginx
sudo docker compose --profile nginx down
sudo docker compose --profile nginx up -d --build
```

---

## 📝 Лицензия

MIT License — см. [LICENSE](LICENSE)

---

## 📞 Поддержка

- 🐛 **Баги**: [GitHub Issues](https://github.com/SkunkBG/aunt-polly-bot/issues)
- 💬 **Вопросы**: [GitHub Discussions](https://github.com/SkunkBG/aunt-polly-bot/discussions)

---

<p align="center">
  Made with ❤️ for support teams
</p>

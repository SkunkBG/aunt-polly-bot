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
- [Варианты установки](#-варианты-установки)
  - [🚀 Быстрая установка (Docker)](#-быстрая-установка-docker)
  - [🔧 Ручная установка (без Docker)](#-ручная-установка-без-docker)
  - [🌐 Продакшен с Caddy](#-продакшен-с-caddy-рекомендуется)
  - [⚙️ Продакшен с Nginx](#️-продакшен-с-nginx)
- [Подготовка VPS](#-подготовка-vps)
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
- **Уведомления** — о новых пользователях в реальном времени

### 🗂️ FAQ-система
- Автоматический поиск по базе знаний (fuzzy matching)
- Настраиваемый порог сходства (10-100%)
- Поддержка медиа-файлов (фото, видео, документы)
- Экспорт/импорт в JSON и CSV

### 🧠 Искусственный интеллект
- **Groq** — Llama 3.3 70B, Mixtral 8x7B (быстрые ответы)
- **Google Gemini** — Gemini 1.5 Flash/Pro (расширенные возможности)
- Настраиваемый системный промпт
- Тестирование прямо в админке
- Автоматический fallback между моделями

### 🛡️ Многоуровневая защита
- **Уровень 1**: Reverse Proxy (Nginx/Caddy) — Rate limiting, IP filtering
- **Уровень 2**: Webhook Secret Token — проверка подлинности
- **Уровень 3**: Rate Limiter в боте — Token Bucket алгоритм
- **Уровень 4**: User Manager — ручная блокировка, auto-ban

### 🌍 Мультиязычность
- 🇷🇺 Русский, 🇬🇧 English, 🇺🇦 Українська
- Автоопределение языка из Telegram
- Настраиваемый язык по умолчанию

### ⚡ Дополнительно
- **Триггеры** — автоответы по ключевым словам
- **Быстрые ответы** — шаблоны для админа
- **Режим группы** — поддержка в групповых чатах
- **Remnawave** — интеграция с VPN-панелью

---

## 💻 Системные требования

### Поддерживаемые ОС

| ОС | Версия | Статус |
|----|--------|:------:|
| **Ubuntu** | 20.04, 22.04, 24.04 LTS | ✅ Рекомендуется |
| **Debian** | 11, 12 | ✅ Полная поддержка |
| **CentOS** | Stream 8, 9 | ✅ Полная поддержка |
| **Rocky Linux** | 8, 9 | ✅ Полная поддержка |
| **AlmaLinux** | 8, 9 | ✅ Полная поддержка |
| **Fedora** | 38, 39, 40 | ✅ Полная поддержка |
| **macOS** | 12+ (для разработки) | ⚠️ Только Docker |
| **Windows** | 10/11 + WSL2 | ⚠️ Только Docker |

### Минимальные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| **CPU** | 1 vCPU | 2 vCPU |
| **RAM** | 512 MB | 1 GB |
| **Диск** | 5 GB SSD | 10 GB SSD |
| **Сеть** | 100 Mbit/s | 1 Gbit/s |

### Программные требования

**Для Docker-установки:**
- Docker 20.10+
- Docker Compose 2.0+

**Для ручной установки:**
- Python 3.11+
- pip 21+
- Git

**Для продакшена:**
- Домен с DNS A-записью
- Открытые порты 80, 443

---

## 📦 Варианты установки

### 🚀 Быстрая установка (Docker)

Самый простой способ — polling режим, не требует домен.

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

# 2. Создайте конфигурацию
cp env.example .env

# 3. Отредактируйте .env (минимум BOT_TOKEN и ADMIN_ID)
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
docker-compose up -d

# 5. Проверьте логи
docker-compose logs -f

# 6. Готово! Отправьте /admin боту
```

**Управление:**
```bash
docker-compose down      # Остановить
docker-compose restart   # Перезапустить
docker-compose pull      # Обновить образы
docker-compose logs -f   # Логи в реальном времени
```

---

### 🔧 Ручная установка (без Docker)

Для разработки или когда Docker недоступен.

#### Ubuntu / Debian

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

#### CentOS / Rocky / Alma

```bash
# 1. Установите EPEL и Python
sudo dnf install -y epel-release
sudo dnf install -y python3.11 python3.11-pip git

# 2. Клонируйте и настройте
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

python3.11 -m venv venv
source venv/bin/activate
pip install -r bot/requirements.txt

cp env.example .env
nano .env

# 3. Запустите
python main.py
```

#### Fedora

```bash
# 1. Установите Python
sudo dnf install -y python3.11 python3-pip git

# 2. Клонируйте и настройте
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

python3.11 -m venv venv
source venv/bin/activate
pip install -r bot/requirements.txt

cp env.example .env
nano .env

# 3. Запустите
python main.py
```

#### Запуск как systemd-сервис

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

# Логи
sudo journalctl -u aunt-polly-bot -f
```

---

### 🌐 Продакшен с Caddy (рекомендуется)

**Caddy** автоматически получает SSL-сертификаты от Let's Encrypt.

#### Преимущества Caddy
- ✅ Автоматический HTTPS (Let's Encrypt)
- ✅ Автообновление сертификатов
- ✅ Простая конфигурация
- ✅ HTTP/2 и HTTP/3 из коробки

#### Требования
- VPS с публичным IP
- Домен, направленный на VPS (A-запись)
- Открытые порты 80 и 443

#### Установка

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/SkunkBG/aunt-polly-bot.git
cd aunt-polly-bot

# 2. Настройте .env для webhook
cp env.example .env
nano .env
```

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
# 3. Настройте Caddyfile
nano Caddyfile
```

Замените `BOTDOMAIN.COM` на ваш домен и укажите email:
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
# 4. Запустите с профилем caddy
docker-compose --profile caddy up -d

# 5. Проверьте, что сертификат получен
docker-compose logs caddy

# 6. Проверьте webhook
curl https://bot.yourdomain.com/bot/health
```

#### Обновление

```bash
cd aunt-polly-bot
git pull
docker-compose --profile caddy down
docker-compose --profile caddy up -d --build
```

---

### ⚙️ Продакшен с Nginx

**Nginx** даёт больше контроля, но требует ручной настройки SSL.

#### Преимущества Nginx
- ✅ Детальная настройка rate limiting
- ✅ IP whitelist для Telegram серверов
- ✅ Подробные логи и мониторинг
- ✅ Гибкая конфигурация

#### Шаг 1: Настройка .env

```bash
cp env.example .env
nano .env
```

```env
BOT_TOKEN=YOUR_BOT_TOKEN
ADMIN_ID=YOUR_TELEGRAM_ID
BOT_MODE=webhook
WEBHOOK_HOST=https://bot.yourdomain.com
WEBHOOK_PATH=/bot/
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=8081
WEBHOOK_SECRET_TOKEN=your_secret_token_here
```

#### Шаг 2: Настройка Nginx

```bash
nano nginx/nginx.conf
```

Замените все `BOTDOMAIN.COM` на ваш домен (4 места в файле).

#### Шаг 3: Получение SSL-сертификата

```bash
# Сначала запустите nginx без SSL для ACME challenge
# Временно закомментируйте HTTPS server block в nginx.conf

docker-compose --profile nginx up -d nginx

# Получите сертификат
docker-compose run --rm certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d bot.yourdomain.com \
  --email your@email.com \
  --agree-tos \
  --no-eff-email

# Раскомментируйте HTTPS server block в nginx.conf
nano nginx/nginx.conf
```

#### Шаг 4: Запуск

```bash
# Перезапустите с полной конфигурацией
docker-compose --profile nginx down
docker-compose --profile nginx up -d

# Проверьте
curl https://bot.yourdomain.com/bot/health
```

#### Автообновление сертификатов

Certbot в docker-compose автоматически обновляет сертификаты. Для применения добавьте в crontab:

```bash
crontab -e
```

```cron
0 0 1 * * cd /path/to/aunt-polly-bot && docker-compose --profile nginx exec nginx nginx -s reload
```

---

## 🖥️ Подготовка VPS

### Выбор провайдера

| Провайдер | Минимальный тариф | Рекомендация |
|-----------|-------------------|--------------|
| **Hetzner** | €3.79/мес (CX22) | ⭐ Лучшее соотношение цена/качество |
| **DigitalOcean** | $6/мес (Basic) | Простой интерфейс |
| **Vultr** | $6/мес (Cloud) | Много локаций |
| **Linode** | $5/мес (Nanode) | Хорошая документация |
| **AWS Lightsail** | $5/мес | Интеграция с AWS |
| **Timeweb** | ₽179/мес | Для РФ |
| **FirstVDS** | ₽99/мес | Для РФ, бюджетно |

### Первоначальная настройка Ubuntu 22.04/24.04

```bash
# 1. Подключитесь к серверу
ssh root@YOUR_SERVER_IP

# 2. Обновите систему
apt update && apt upgrade -y

# 3. Создайте пользователя (не работайте под root!)
adduser botuser
usermod -aG sudo botuser

# 4. Настройте SSH-ключи
mkdir -p /home/botuser/.ssh
cp ~/.ssh/authorized_keys /home/botuser/.ssh/
chown -R botuser:botuser /home/botuser/.ssh
chmod 700 /home/botuser/.ssh
chmod 600 /home/botuser/.ssh/authorized_keys

# 5. Настройте firewall
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# 6. Установите Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker botuser

# 7. Установите Docker Compose
apt install -y docker-compose-plugin

# 8. Перезайдите под новым пользователем
exit
ssh botuser@YOUR_SERVER_IP

# 9. Проверьте Docker
docker --version
docker compose version
```

### Первоначальная настройка Debian 12

```bash
# 1. Подключитесь к серверу
ssh root@YOUR_SERVER_IP

# 2. Обновите систему
apt update && apt upgrade -y

# 3. Установите sudo и создайте пользователя
apt install -y sudo
adduser botuser
usermod -aG sudo botuser

# 4. Настройте firewall
apt install -y ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# 5. Установите Docker
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 6. Добавьте пользователя в группу docker
usermod -aG docker botuser

# 7. Перезайдите под новым пользователем
exit
ssh botuser@YOUR_SERVER_IP
```

### Первоначальная настройка CentOS Stream 9 / Rocky 9 / Alma 9

```bash
# 1. Подключитесь к серверу
ssh root@YOUR_SERVER_IP

# 2. Обновите систему
dnf update -y

# 3. Создайте пользователя
adduser botuser
passwd botuser
usermod -aG wheel botuser

# 4. Настройте firewall
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

# 5. Установите Docker
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

# 6. Добавьте пользователя в группу docker
usermod -aG docker botuser

# 7. Перезайдите под новым пользователем
exit
ssh botuser@YOUR_SERVER_IP
```

### Настройка DNS

1. Войдите в панель управления доменом (Cloudflare, Namecheap, GoDaddy и т.д.)
2. Перейдите в раздел DNS
3. Создайте A-запись:
   - **Имя/Host**: `bot` (для bot.yourdomain.com) или `@` (для yourdomain.com)
   - **Тип**: A
   - **Значение/Points to**: IP вашего VPS
   - **TTL**: 300 (или Auto)
   - **Proxy**: отключить (если Cloudflare)

4. Дождитесь распространения DNS (5-30 минут):
```bash
# Проверка
dig bot.yourdomain.com +short
# Должен показать IP вашего VPS

# Или через nslookup
nslookup bot.yourdomain.com
```

### Настройка swap (для VPS с малым RAM)

```bash
# Проверьте текущий swap
free -h

# Создайте swap 1GB
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Сделайте постоянным
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Настройте swappiness (10 = использовать swap только при необходимости)
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Проверьте
free -h
```

### Автоматические обновления безопасности

#### Ubuntu/Debian
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

#### CentOS/Rocky/Alma
```bash
sudo dnf install -y dnf-automatic
sudo systemctl enable --now dnf-automatic.timer
```

### Безопасность SSH

```bash
# Отключите вход по паролю (только после настройки SSH-ключей!)
sudo nano /etc/ssh/sshd_config
```

Измените:
```
PasswordAuthentication no
PermitRootLogin no
```

```bash
sudo systemctl restart sshd
```

---

## ⚙️ Конфигурация

### Полный список переменных .env

```env
# ============================================================================
# ОСНОВНЫЕ (обязательные)
# ============================================================================

# Токен бота от @BotFather
BOT_TOKEN="123456789:AABBccDDeeFFggHHiiJJkkLLmmNNoo"

# Ваш Telegram ID (узнать: @userinfobot)
ADMIN_ID="123456789"

# Режим: "polling" (разработка) или "webhook" (продакшен)
BOT_MODE="polling"

# ============================================================================
# WEBHOOK (только для BOT_MODE=webhook)
# ============================================================================

# Ваш домен с HTTPS
WEBHOOK_HOST="https://bot.yourdomain.com"

# Путь webhook (должен совпадать с конфигом Caddy/Nginx)
WEBHOOK_PATH="/bot/"

# Внутренний сервер (обычно не менять)
WEB_SERVER_HOST="0.0.0.0"
WEB_SERVER_PORT=8081

# Секретный токен для защиты webhook
# Генерация: openssl rand -hex 32
WEBHOOK_SECRET_TOKEN=""

# ============================================================================
# ПРИВЕТСТВИЕ И АВТООТВЕТЧИК
# ============================================================================

# Приветственное сообщение (поддерживает HTML)
WELCOME_MESSAGE="Здравствуйте! 👋 Я бот-помощник. Чем могу помочь?"

# Путь к изображению приветствия
WELCOME_IMAGE_PATH="bot/assets/welcome.jpg"

# Рабочие часы (для режима "по часам")
WORK_HOUR_START=9
WORK_HOUR_END=18

# Часовой пояс (IANA формат)
TIMEZONE="Europe/Moscow"

# Сообщение вне рабочих часов
OFF_HOURS_REPLY="Спасибо за сообщение! Ответим в рабочее время (9:00-18:00 МСК)."

# ============================================================================
# ИСКУССТВЕННЫЙ ИНТЕЛЛЕКТ (опционально)
# ============================================================================

# Groq API (бесплатно: https://console.groq.com)
GROQ_API_KEY=""
GROQ_MODELS="llama-3.3-70b-versatile,mixtral-8x7b-32768"

# Google Gemini (бесплатно: https://aistudio.google.com)
GEMINI_API_KEY=""
GEMINI_MODELS="gemini-1.5-flash-latest,gemini-1.5-pro-latest"

# ============================================================================
# REMNAWAVE VPN (опционально)
# ============================================================================

# URL панели Remnawave (например: https://panel.yourvpn.com)
REMNAWAVE_API_URL=""

# API токен из панели
REMNAWAVE_API_TOKEN=""

# ============================================================================
# СИСТЕМА
# ============================================================================

# Уровень логов: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL="INFO"

# Время ежедневного бэкапа (HH:MM, локальное время)
BACKUP_TIME="10:00"
```

### Получение токенов и ключей

#### Telegram Bot Token
1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Введите имя бота (например: "My Support Bot")
4. Введите username бота (например: `my_support_bot`)
5. Скопируйте токен (формат: `123456789:AABBccDDeeFFggHHiiJJkkLLmmNNoo`)

#### Ваш Telegram ID
1. Откройте [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте `/start`
3. Скопируйте ваш ID (число)

#### Groq API Key (бесплатно)
1. Зарегистрируйтесь на [console.groq.com](https://console.groq.com)
2. Перейдите в раздел "API Keys"
3. Нажмите "Create API Key"
4. Скопируйте ключ

#### Google Gemini API Key (бесплатно)
1. Откройте [aistudio.google.com](https://aistudio.google.com)
2. Войдите через Google-аккаунт
3. Нажмите "Get API key" → "Create API key"
4. Выберите проект или создайте новый
5. Скопируйте ключ

#### Webhook Secret Token
```bash
# Сгенерируйте случайный токен
openssl rand -hex 32
```

---

## 📖 Использование

### Команды бота

#### Для пользователей
| Команда | Описание |
|---------|----------|
| `/start` | Начать диалог, получить приветствие |
| `/help` | Показать справку |
| `/faq` | Список частых вопросов |

#### Для администратора
| Команда | Описание |
|---------|----------|
| `/admin` | Открыть админ-панель |
| `/stats` | Быстрая статистика |
| `/backup` | Создать резервную копию |

### Структура админ-панели

```
🎛️ Админ-панель
├── 📊 Дашборд — статистика, состояние бота
├── ✨ Приветствие — текст, изображение, предпросмотр
├── ⏰ Автоответчик — режим 24/7 или по часам
├── 🗂️ FAQ — добавление, редактирование, экспорт
├── 🧠 ИИ — включение, выбор модели, промпт, тест
├── 👥 Пользователи — список, поиск, блокировка
├── 📢 Рассылка — массовые сообщения
├── ⚡ Быстрые ответы — шаблоны
├── 🎯 Триггеры — автоответы по словам
├── 🗄️ Бэкапы — создание, восстановление
├── 🌐 Remnawave — названия серверов
├── 🌍 Языки — мультиязычность
├── 🔔 Уведомления — о новых пользователях
└── ⚙️ Режим работы — личка/группа
```

### Приоритет ответов бота

```
1. FAQ (если найдено совпадение выше порога)
2. Триггеры (по ключевым словам)
3. ИИ (если включен и FAQ не найден)
4. Автоответчик (вне рабочих часов)
5. Уведомление админу
```

### Health Check

```bash
# Локально
curl http://localhost:8081/health

# Продакшен
curl https://bot.yourdomain.com/bot/health
```

Ответ:
```json
{
  "status": "ok",
  "rate_limiter": {
    "total_requests": 1234,
    "rate_limited": 56,
    "banned_users": 2,
    "active_users": 100
  }
}
```

---

## 📚 Документация

| Документ | Описание |
|----------|----------|
| [ADMIN_PANEL_GUIDE.md](ADMIN_PANEL_GUIDE.md) | Подробное руководство по админ-панели |
| [SECURITY.md](SECURITY.md) | Настройка защиты, rate limiting, IP whitelist |
| [IMPROVEMENTS.md](IMPROVEMENTS.md) | История изменений и новые функции |
| [env.example](env.example) | Пример конфигурации со всеми параметрами |

---

## 📁 Структура проекта

```
aunt-polly-bot/
├── bot/
│   ├── handlers/           # Обработчики сообщений
│   │   ├── admin_panel.py  # Админ-панель (~1500 строк)
│   │   ├── admin_reply.py  # Ответы админа
│   │   ├── faq.py          # FAQ-система
│   │   ├── group_messages.py # Групповые чаты
│   │   ├── start.py        # /start команда
│   │   └── user_messages.py # Сообщения пользователей
│   ├── keyboards/          # Inline-клавиатуры
│   ├── fsm/                # Состояния FSM
│   ├── data/               # JSON-данные
│   │   ├── settings.json   # Настройки бота
│   │   └── faq.json        # База FAQ
│   ├── assets/             # Медиа-файлы
│   ├── ai_integration.py   # Интеграция Groq/Gemini
│   ├── ai_block_manager.py # Управление AI-блоками
│   ├── backup_manager.py   # Система бэкапов
│   ├── config.py           # Конфигурация
│   ├── faq_search.py       # Поиск по FAQ
│   ├── i18n.py             # Мультиязычность
│   ├── rate_limiter.py     # Rate limiting
│   ├── remnawave_integration.py # Remnawave API
│   ├── user_manager.py     # Управление пользователями
│   └── requirements.txt    # Python-зависимости
├── nginx/
│   └── nginx.conf          # Конфигурация Nginx
├── certbot/                # SSL-сертификаты
├── logs/                   # Логи
├── main.py                 # Точка входа
├── Dockerfile              # Docker-образ
├── docker-compose.yml      # Docker Compose
├── Caddyfile               # Конфигурация Caddy
├── env.example             # Пример .env
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🔧 Troubleshooting

### Бот не отвечает

```bash
# Проверьте, запущен ли контейнер
docker-compose ps

# Проверьте логи
docker-compose logs aunt-polly-bot

# Проверьте .env
cat .env | grep -E "BOT_TOKEN|ADMIN_ID"
```

**Частые причины:**
- ❌ Неверный `BOT_TOKEN`
- ❌ Неверный `ADMIN_ID`
- ❌ Бот заблокирован в Telegram
- ❌ Проблемы с сетью

### Webhook не работает

```bash
# Проверьте DNS
dig bot.yourdomain.com +short
ping bot.yourdomain.com

# Проверьте SSL
curl -I https://bot.yourdomain.com

# Проверьте endpoint
curl https://bot.yourdomain.com/bot/health

# Проверьте логи
docker-compose logs caddy  # или nginx
docker-compose logs aunt-polly-bot
```

**Частые причины:**
- ❌ DNS не настроен или не распространился
- ❌ Порты 80/443 закрыты в firewall
- ❌ Неверный `WEBHOOK_HOST` в .env
- ❌ Неверный домен в Caddyfile или nginx.conf
- ❌ SSL-сертификат не получен

### Ошибки AI

```bash
# Проверьте ключи в .env
grep -E "GROQ_API_KEY|GEMINI_API_KEY" .env

# Тест Groq API
curl -X POST https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer YOUR_GROQ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "mixtral-8x7b-32768", "messages": [{"role": "user", "content": "Hi"}]}'
```

**Частые причины:**
- ❌ Неверный или просроченный API-ключ
- ❌ Превышен лимит запросов
- ❌ Модель недоступна или переименована

### Rate Limiting срабатывает слишком часто

Отредактируйте `bot/data/settings.json`:
```json
{
  "rate_limit_user": 10,
  "rate_limit_burst": 20,
  "antiflood_rate": 0.3
}
```

```bash
docker-compose restart aunt-polly-bot
```

### Нет места на диске

```bash
# Проверьте использование
df -h

# Очистите Docker
docker system prune -a

# Очистите старые логи
sudo truncate -s 0 logs/**/*.log

# Удалите старые бэкапы
ls -la bot/backups/
rm bot/backups/backup_old_*.zip
```

### Контейнер постоянно перезапускается

```bash
# Посмотрите причину
docker-compose logs --tail=50 aunt-polly-bot

# Проверьте ресурсы
docker stats

# Проверьте .env на синтаксические ошибки
docker-compose config
```

### Бэкапы не создаются

```bash
# Проверьте права на папку
ls -la bot/backups/

# Проверьте ADMIN_ID в .env
grep ADMIN_ID .env

# Проверьте время бэкапа в настройках
cat bot/data/settings.json | grep backup_time
```

---

## 🔄 Обновление

### Docker

```bash
cd aunt-polly-bot
git pull

# Для polling
docker-compose down
docker-compose up -d --build

# Для webhook с Caddy
docker-compose --profile caddy down
docker-compose --profile caddy up -d --build

# Для webhook с Nginx
docker-compose --profile nginx down
docker-compose --profile nginx up -d --build
```

### Ручная установка

```bash
cd aunt-polly-bot
git pull

source venv/bin/activate
pip install -r bot/requirements.txt --upgrade

sudo systemctl restart aunt-polly-bot
```

---

## 🤝 Contributing

1. Fork репозитория
2. Создайте ветку: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Откройте Pull Request

---

## 📝 Лицензия

MIT License — см. [LICENSE](LICENSE)

---

## 🙏 Благодарности

- [aiogram](https://aiogram.dev) — асинхронный Telegram Bot Framework
- [Groq](https://groq.com) — быстрый AI inference
- [Google Gemini](https://ai.google.dev) — мощный AI API
- [Caddy](https://caddyserver.com) — автоматический HTTPS
- [Docker](https://docker.com) — контейнеризация

---

## 📞 Поддержка

- 🐛 **Баги**: [GitHub Issues](https://github.com/SkunkBG/aunt-polly-bot/issues)
- 💬 **Вопросы**: [GitHub Discussions](https://github.com/SkunkBG/aunt-polly-bot/discussions)

---

<p align="center">
  Made with ❤️ for support teams
</p>

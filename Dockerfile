# Используем официальный образ Python 3.11-slim
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /usr/src/app

# Копируем файл с зависимостями и устанавливаем их
# Это делается отдельным слоем для кэширования Docker
COPY bot/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всю папку 'bot' (включая handlers, assets, data, keyboards и т.д.)
# в одноименную папку внутри контейнера
COPY bot ./bot

# Копируем главный запускающий скрипт в корень рабочей директории
COPY main.py .

# Указываем команду, которая будет выполняться при запуске контейнера
CMD ["python", "main.py"]

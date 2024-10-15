# Используем базовый образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем requirements.txt для установки зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

# Копируем все файлы проекта в рабочую директорию контейнера
COPY . .

# Устанавливаем переменные окружения для чтения .env файла

# Команда для запуска бота
CMD ["python", "source.py"]

import logging
import os
import requests
import requests_cache
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
from mistralai import Mistral  # Импортируем клиентскую библиотеку Mistral
from pathlib import Path

# Очистка кэша запросов
requests_cache.clear()

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токенов из переменных окружения
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MISTRAL_API_KEY = os.getenv('MISTRAL_AI_API_KEY')

# Проверка наличия токенов
if not API_TOKEN or not MISTRAL_API_KEY:
    raise ValueError("Необходимо задать TELEGRAM_BOT_TOKEN и MISTRAL_AI_API_KEY в .env файле")

# Задаем директорию для логов
log_directory = Path("logs")

# Создаем директорию, если она не существует
log_directory.mkdir(parents=True, exist_ok=True)

# Настройка логирования
log_file = log_directory / "bot_log.log"
logging.basicConfig(filename=log_file, level=logging.INFO)

# Логирование начала работы
logging.info("Запуск бота")

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Инициализация клиента Mistral AI
client = Mistral(api_key=MISTRAL_API_KEY)
model_chat = "mistral-large-latest"

# Пример списка URL для парсинга
URL_LIST = [
    'https://ge74.ru'
]

async def parse_site(url):
    """
    Асинхронная функция для парсинга указанного веб-сайта и извлечения контента со всех возможных тегов.
    
    :param url: URL сайта для парсинга
    :return: Контент страницы
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Проверка на успешный статус код
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к {url}: {e}")
        return f"Не удалось получить данные с сайта {url}."
    
    # Парсим содержимое страницы с помощью BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Извлечение текста со страницы
    text_content = soup.get_text(separator=' ', strip=True)  # Извлекает текст из всех тегов
    
    if not text_content.strip():  # Проверка, есть ли какой-либо текст
        logging.warning(f"Текст не найден на странице {url}.")
        return f"Не удалось найти нужную информацию на сайте {url}."
    
    return text_content

async def gather_context():
    """
    Асинхронная функция для парсинга данных с нескольких сайтов.
    
    :return: Скомбинированный текст с нескольких сайтов
    """
    context = []
    for url in URL_LIST:
        site_content = await parse_site(url)
        if "Не удалось" not in site_content:  # Если парсинг успешен, добавляем контент
            context.append(site_content)
    
    # Объединение контента с нескольких сайтов
    return ' '.join(context)

async def generate_answer(question, context):
    """
    Асинхронная функция для генерации ответа с использованием Mistral AI.
    
    :param question: Вопрос пользователя
    :param context: Контекст, полученный из парсинга сайтов
    :return: Сгенерированный ответ или сообщение об ошибке
    """
    try:
        # Отправка запроса в Mistral AI для генерации ответа на русском языке
        chat_response = client.chat.complete(
            model=model_chat,
            messages=[
                {"role": "system", "content": "Пожалуйста, отвечай на вопросы на русском языке."},
                {"role": "user", "content": f"Вопрос: {question}. Контекст: {context}"}
            ],
            temperature=0
        )
        answer = chat_response.choices[0].message.content  # Извлечение ответа из ответа API
        logging.info(f"Сгенерированный ответ: {answer}")
        return answer
    except Exception as e:
        logging.error(f"Ошибка при работе с Mistral AI: {e}")
        return "Ошибка генерации ответа от Mistral AI."

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    Обработчик команды /start.
    
    :param message: Сообщение пользователя
    """
    welcome_text = (
        "Привет! Я бот, который поможет ответить на ваши вопросы.\n"
        "Просто отправьте мне свой вопрос, и я постараюсь найти ответ!\n"
        "\n"
        "( ge74_bot может допускать ошибки. Рекомендуем проверять важную информацию )"
    )
    logging.info(f"Отправлено приветствие пользователю {message.from_user.id}")
    await message.reply(welcome_text)

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    """
    Обработчик команды /help.
    
    :param message: Сообщение пользователя
    """
    help_text = (
        "Чтобы задать вопрос, просто отправьте его в чат.\n"
        "Я буду использовать данные с нескольких сайтов и нейросеть Mistral AI для формирования ответа."
    )
    logging.info(f"Отправлена помощь пользователю {message.from_user.id}")
    await message.reply(help_text)

@dp.message_handler()
async def handle_question(message: types.Message):
    """
    Обработчик текстовых сообщений (вопросов от пользователя).
    
    :param message: Сообщение пользователя
    """
    question = message.text
    logging.info(f"Получен вопрос от пользователя {message.from_user.id}: {question}")
    
    # Сбор контекста с нескольких сайтов
    context = await gather_context()
    
    if not context:
        await message.reply("Не удалось собрать данные с сайтов.")
        logging.warning(f"Контекст не собран для вопроса: {question}")
        return
    
    await message.reply("Ваш запрос обрабатывается")
    
    # Генерация ответа с использованием Mistral AI
    answer = await generate_answer(question, context)
    await message.reply(answer)

if __name__ == '__main__':
    logging.info("Запуск основного процесса бота")
    executor.start_polling(dp, skip_updates=True)

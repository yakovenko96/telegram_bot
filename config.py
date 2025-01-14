import os

from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

# Чтение токена из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")
WEATHER_TOKEN = os.getenv("WEATHER_TOKEN")
FOOD_ID = os.getenv("NUTRITIONIX_ID")
FOOD_TOKEN = os.getenv("NUTRITIONIX_TOKEN")

if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")
if not WEATHER_TOKEN:
    raise ValueError("Переменная окружения WEATHER_TOKEN не установлена!")
if not FOOD_ID:
    raise ValueError("Переменная окружения NUTRITIONIX_ID не установлена!")
if not FOOD_TOKEN:
    raise ValueError("Переменная окружения NUTRITIONIX_TOKEN не установлена!")

from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from states import Form
import aiohttp
from pydantic import BaseModel, Field, ValidationError
from translate import Translator
from config import WEATHER_TOKEN, FOOD_ID, FOOD_TOKEN

translator = Translator(to_lang="en", from_lang="ru")


async def translate(text: str):
    """Функция перевода с русского на английский язык"""
    return translator.translate(text)


async def get_temp(selected_city: str):
    """Функция получения температуры"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={selected_city}&appid={WEATHER_TOKEN}&units=metric"
    async with aiohttp.ClientSession() as client:
        response = await client.get(url)
        if response.status == 200:
            response = await response.json()
            return response['main']['temp']
        return await response.text


async def get_food(food: str):
    """Функция получения калорийности продукта"""
    url = "https://trackapi.nutritionix.com/v2/natural/nutrients"
    headers = {
        'x-app-id': FOOD_ID,
        'x-app-key': FOOD_TOKEN,
        'Content-Type': 'application/json'
    }
    data = {"query": food}

    async with aiohttp.ClientSession() as client:
        async with client.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                nutrients = await response.json()
                calories = nutrients['foods'][0]['nf_calories']
                serving_gramm = nutrients['foods'][0]['serving_weight_grams']
                calories_for_gramm = round(calories / serving_gramm, 2)
                return calories_for_gramm
            return await "К сожалению такого продукта в нашей базе еще нет."


async def get_train_cal(train: str, time: int):
    """Функция получения каллорийности с тренировки"""
    url = "https://trackapi.nutritionix.com/v2/natural/exercise"
    headers = {
        'x-app-id': FOOD_ID,
        'x-app-key': FOOD_TOKEN,
        'Content-Type': 'application/json'
    }
    data = {"query": f"{train} {time}"}

    async with aiohttp.ClientSession() as client:
        async with client.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                exercise = await response.json()
                calories = exercise['exercises'][0]['nf_calories']
                return calories
            return await "К сожалению такой тренировки в нашей базе нет."


class ProfileData(BaseModel):
    weight: Optional[float] = Field(None, ge=50.0, le=200.0)
    height: Optional[int] = Field(None, ge=50, le=220)
    age: Optional[int] = Field(None, ge=14, le=120)
    city: Optional[str] = Field(None, min_length=2, max_length=20)
    activity: Optional[int] = Field(None, ge=0, le=1440)
    calorie_goal: Optional[int] = Field(None, ge=500, le=5000)
    gramms: Optional[int] = Field(None, ge=0)
    water: Optional[int] = Field(None, ge=0, le=5000)
    train: Optional[str] = Field(None, min_length=2, max_length=20)
    time_train: Optional[int] = Field(None, ge=0, le=1440)


router = Router()
users = {}


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.reply("Добро пожаловать! Я бот помощник для отслеживания калорийности и воды "
                        "в вашем организме за сутки.\nВведите /help для списка команд.")


@router.message(Command("new_day"))
async def new_day(message: Message):
    """Обработчик команды /new_day"""
    user_id = message.from_user.id
    try:
        city = users[user_id]['city']
        age = users[user_id]["age"]
        activity = users[user_id]["activity"]
        users[user_id]["logged_water"] = [0]
        users[user_id]["logged_calories"] = [0]
        users[user_id]["burned_calories"] = 0
        city = await translate(city)
        temp = await get_temp(city)//25
        weather_water = temp*250
        users[user_id]["water_goal"] = age*30 + round(activity*500, 0) + weather_water
        await message.reply("Вот и новый день и я готов записывать ваши результаты!\n"
                            "Сегодня вам нужно:\n"
                            f"- выпить {users[user_id]["water_goal"]} мл воды.\n"
                            f"- съесть {users[user_id]["calorie_goal"]} ккал.")
    except KeyError:
        await message.reply("Нет информации, пожалуйста заполните профиль /set_profile и повторите попытку")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.reply(
        "Доступные команды:\n"
        "/new_day - Сброс учитываемых калорий и воды за день\n"
        "/set_profile - Создание профиля\n"
        "/check_progress - Информация из профиля\n"
        "/log_water - Запись выпитой воды\n"
        "/log_food - Запись съеденой еды\n"
        "/log_workout - Запись тренировок\n"
        "/plot_water - график учета воды\n"
        "/plot_calories - график учета калорий\n"
    )


@router.message(Command("plot_water"))
async def plot_water(message: Message):
    """Функция построения графика воды"""
    user_id = message.from_user.id
    try:
        water = users[user_id]['logged_water']
        water = np.cumsum(water)
        plt.title('Накопительный учет воды')
        plt.xlabel('Прием')
        plt.ylabel('Мл')
        plt.xticks(range(len(water)))
        plt.plot(water, marker='o')
        plt.savefig('water.png')
        plt.close()
        photo = FSInputFile("./water.png")
        await message.reply_photo(photo=photo)
    except KeyError:
        await message.reply("Нет информации, пожалуйста заполните профиль /set_profile и повторите попытку")


@router.message(Command("plot_calories"))
async def plot_calories(message: Message):
    """Функция построения графика калорий"""
    user_id = message.from_user.id
    try:
        calories = users[user_id]['logged_calories']
        calories = np.cumsum(calories)
        plt.title('Накопительный учет калорий')
        plt.xlabel('Прием')
        plt.ylabel('ккал')
        plt.xticks(range(len(calories)))
        plt.plot(calories, marker='o')
        plt.savefig('calories.png')
        plt.close()
        photo = FSInputFile("./calories.png")
        await message.reply_photo(photo=photo)
    except KeyError:
        await message.reply("Нет информации, пожалуйста заполните профиль /set_profile и повторите попытку")


@router.message(Command("log_workout"))
async def log_workout(message: Message, command: CommandObject):
    """Функция подсчета калорийности и воды за тренировку"""
    user_id = message.from_user.id
    try:
        args = command.args.split(" ")
        if len(args) != 2:
            raise AttributeError
        time = int(args[1])
        train_ = args[0]
        profile_data = ProfileData(time_train=time, train=train_)
        time = profile_data.time_train
        train_ = profile_data.train
        train = await translate(train_)
        calories = await get_train_cal(train, time)
        workout_water = time // 30 * 200
        users[user_id]["water_goal"] = users[user_id].get("water_goal", 0) + workout_water
        users[user_id]["burned_calories"] = users[user_id].get("burned_calories", 0) + calories
        await message.reply(f"{train_} {time} минут — {calories} ккал. Дополнительно: выпейте {workout_water} мл воды.")
    except AttributeError:
        await message.reply(text="Пожалуйста, укажите название тренировки "
                            "и проведенное время.\nНапример: <code>/log_workout </code>бег 30", parse_mode='html')
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, количество символов в названии тренировки должно быть больше 2, "
                            "время тренировки от 0 до 1440 минут")
    except KeyError:
        await message.reply("Нет информации, пожалуйста заполните профиль /set_profile и повторите попытку")


@router.message(Command("log_food"))
async def log_food(message: Message, command: CommandObject, state: FSMContext):
    """Функция подсчета калорийности"""
    food_item_ = command.args
    if not food_item_:
        await message.reply(text="Пожалуйста, укажите название продукта. Например: <code>/log_food </code>банан",
                            parse_mode='html')
        return None
    food_item = await translate(food_item_)

    calories_for_gramm = await get_food(food_item)

    if isinstance(calories_for_gramm, float):
        await state.update_data(calories_for_gramm=calories_for_gramm)
        await message.reply(f"{food_item_} — {calories_for_gramm*100} ккал на 100 г. Сколько грамм вы съели?")
        await state.set_state(Form.gramms)
    else:
        await message.reply(calories_for_gramm)


@router.message(Command("log_water"))
async def log_water(message: Message, command: CommandObject):
    """Функция подсчета выпитой воды"""
    user_id = message.from_user.id
    water = command.args
    if not water:
        await message.reply(text="Пожалуйста, пропишите количество воды в мл после команды." +
                            "Например: <code>/log_water </code>100", parse_mode='html')
        return None
    try:
        water = int(water)
        profile_data = ProfileData(water=water)
        water = profile_data.water
        users[user_id]["logged_water"].append(water)
        await message.reply(f"Записано: {water} мл, осталось выпить за сегодня "
                            f"{users[user_id]["water_goal"] - sum(users[user_id]["logged_water"])} мл.")
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, введите число мл воды от 0 до 5000")
    except KeyError:
        await message.reply("Нет информации, пожалуйста заполните профиль /set_profile и повторите попытку")


@router.message(Form.gramms)
async def process_log_food(message: Message, state: FSMContext):
    """Функция для записи съеденных грамов и пересчет калорий"""
    user_id = message.from_user.id
    try:
        gramms = int(message.text)
        profile_data = ProfileData(gramms=gramms)
        gramms = profile_data.gramms
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, введите число грамм от 0 и больше")

    data = await state.get_data()
    try:
        calories_for_gramm = data.get("calories_for_gramm")
        calories = round(calories_for_gramm*gramms, 2)
        users[user_id]["logged_calories"].append(calories)
        await message.reply(f"Записано: {calories} ккал.")
        await state.clear()
    except KeyError:
        await state.clear()
        await message.reply("Нет информации, пожалуйста заполните профиль /set_profile и повторите попытку")


@router.message(Command("set_profile"))
async def start_form(message: Message, state: FSMContext):
    """Запрос веса"""
    await message.reply("Введите ваш вес (в кг)")
    await state.set_state(Form.weight)


@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    """Запрос роста и получение веса"""
    try:
        weight = float(message.text)
        profile_data = ProfileData(weight=weight)
        await state.update_data(weight=profile_data.weight)
        await message.reply("Введите ваш рост (в см)")
        await state.set_state(Form.height)
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, вес должен быть от 50 до 200 кг")


@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    """Запрос возраста и получение роста"""
    try:
        height = int(message.text)
        profile_data = ProfileData(height=height)
        await state.update_data(height=profile_data.height)
        await message.reply("Введите ваш возраст")
        await state.set_state(Form.age)
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, рост должен быть от 50 до 220 см")


@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    """Запрос города и получение возраста"""
    try:
        age = int(message.text)
        profile_data = ProfileData(age=age)
        await state.update_data(age=profile_data.age)
        await message.reply("В каком городе вы находитесь?")
        await state.set_state(Form.city)
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, возраст должен быть от 14 до 120 лет")


@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    """Запрос пола и получение города"""
    try:
        city = message.text
        profile_data = ProfileData(city=city)
        await state.update_data(city=profile_data.city)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Мужской", callback_data="Men")],
                [InlineKeyboardButton(text="Женский", callback_data="Women")],
            ]
        )
        await message.reply("Какой у вас пол?", reply_markup=keyboard)
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, название города должно быть от 3 до 20 букв")


async def calculate_tde(callback_query, state: FSMContext):
    """Расчет нормы калорий"""
    data = await state.get_data()
    weight = data.get("weight")
    height = data.get("height")
    age = data.get("age")
    sex = data.get("sex")
    activity = data.get("activity")
    if sex:
        bmr = int(88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age))
    bmr = int(447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age))
    tdee = bmr * activity
    await callback_query.message.answer(f"Ваша норма калорий - {tdee} ккал.\n"
                                        "Для похудения: Обычно рекомендуется создать дефицит калорий, "
                                        "уменьшив потребление на 500-1000 калорий в день, "
                                        "чтобы терять около 0.5-1 кг в неделю.\n\n"
                                        "Для набора массы: Рекомендуется увеличить потребление калорий "
                                        "на 250-500 калорий в день.\n"
                                        "Какая целевая калорийность у вас?")
    await state.set_state(Form.calorie_goal)


@router.callback_query()
async def handle_callback(callback_query, state: FSMContext):
    """Функция вобработки нажатий кнопок"""
    if callback_query.data == "Men":
        await state.update_data(sex=True)
        await process_activity(callback_query)
    elif callback_query.data == "Women":
        await state.update_data(sex=False)
        await process_activity(callback_query)
    elif callback_query.data == "act1":
        await state.update_data(activity=1.2)
        await calculate_tde(callback_query, state)
        await state.set_state(Form.calorie_goal)
    elif callback_query.data == "act2":
        await state.update_data(activity=1.375)
        await calculate_tde(callback_query, state)
        await state.set_state(Form.calorie_goal)
    elif callback_query.data == "act3":
        await state.update_data(activity=1.55)
        await calculate_tde(callback_query, state)
        await state.set_state(Form.calorie_goal)
    elif callback_query.data == "act4":
        await state.update_data(activity=1.725)
        await calculate_tde(callback_query, state)
        await state.set_state(Form.calorie_goal)
    elif callback_query.data == "act5":
        await state.update_data(activity=1.9)
        await calculate_tde(callback_query, state)
        await state.set_state(Form.calorie_goal)
    await callback_query.message.delete_reply_markup()


async def process_activity(callback_query):
    """Фунция выбора активности"""
    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Сидячая работа, отсутствие упражнений",
                                      callback_data="act1")],
                [InlineKeyboardButton(text="Легкие упражнения 1-3 дня в неделю",
                                      callback_data="act2")],
                [InlineKeyboardButton(text="Умеренные упражнения 3-5 дней в неделю",
                                      callback_data="act3")],
                [InlineKeyboardButton(text="Интенсивные упражнения 6-7 дней в неделю",
                                      callback_data="act4")],
                [InlineKeyboardButton(text="Очень интенсивные упражнения, физическая работа",
                                      callback_data="act5")],
            ]
        )
    await callback_query.message.answer("Какой у вас уровень активности?", reply_markup=keyboard)


@router.message(Form.calorie_goal)
async def process_calorie_goal(message: Message, state: FSMContext):
    """Получение целевых калорий и вывод инфы"""
    user_id = message.from_user.id
    try:
        calorie_goal = int(message.text)
        profile_data = ProfileData(calorie_goal=calorie_goal)
        await state.update_data(calorie_goal=profile_data.calorie_goal)
    except (ValueError, ValidationError):
        await message.reply("Некорректное значение, количество калорий должен быть от 500 до 5000")

    data = await state.get_data()
    weight = data.get("weight")
    height = data.get("height")
    activity = data.get("activity")
    city = data.get("city")
    calorie_goal = data.get("calorie_goal")
    age = data.get("age")
    sex = data.get("sex")

    users[user_id] = {
        "weight": weight,
        "height": height,
        "age": age,
        "sex": sex,
        "activity": activity,
        "city": city,
        "water_goal": age*30 + round(activity*500, 0),
        "calorie_goal": calorie_goal,
        "logged_water": [0],
        "logged_calories": [0],
        "burned_calories": 0
    }

    await message.reply("Спасибо! Ваш профиль успешно создан.")
    await state.clear()


@router.message(Command("check_progress"))
async def check_progress(message: Message):
    """Вывод инфы"""
    user_id = message.from_user.id
    try:
        user_info = users[user_id]
        await message.reply(
            "Прогресс\n"
            "Вода:\n"
            f"- Выпито: {sum(user_info['logged_water'])} мл из {user_info['water_goal']} мл.\n"
            f"- Осталось: {user_info['water_goal'] - sum(user_info['logged_water'])} мл.\n\n"
            "Калории:\n"
            f"- Потреблено: {sum(user_info['logged_calories'])} ккал из {user_info['calorie_goal']} ккал.\n"
            f"- Сожжено: {user_info['burned_calories']} ккал.\n"
            f"- Баланс: {sum(user_info['logged_calories']) - user_info['burned_calories']} ккал.\n"
        )
    except KeyError:
        await message.reply("Нет информации, пожалуйста заполните профиль /set_profile")


def setup_handlers(dp):
    """Функция для подключения обработчиков"""
    dp.include_router(router)

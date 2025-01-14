from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    age = State()
    weight = State()
    height = State()
    city = State()
    activity = State()
    calorie_goal = State()
    water = State()
    calories_for_gramm = State()
    gramms = State()
    sex = State()

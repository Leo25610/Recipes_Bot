from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from random import choices
from googletrans import Translator

import aiohttp
import asyncio

router = Router()
translator=Translator()

class CategorySearchStates(StatesGroup):
    waiting_for_recipe_count = State()
    waiting_for_category_choice = State()

@router.message(F.text.startswith("/category_search_random"))
async def handle_category_random_command(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2 and parts[1].isdigit():
        count = int(parts[1])
        await state.set_data({"recipe_count": count})
        await ask_for_category(message, count)
        await state.set_state(CategorySearchStates.waiting_for_category_choice)
    else:
        await message.answer("Сколько рецептов вы хотите получить? Введите число:")
        await state.set_state(CategorySearchStates.waiting_for_recipe_count)

@router.message(CategorySearchStates.waiting_for_recipe_count, F.text.regexp(r"^\d+$"))
async def handle_recipe_count_input(message: Message, state: FSMContext):
    count = int(message.text)
    await state.update_data(recipe_count=count)
    await ask_for_category(message, count)
    await state.set_state(CategorySearchStates.waiting_for_category_choice)

# Если пользователь вводит не число
@router.message(CategorySearchStates.waiting_for_recipe_count)
async def handle_invalid_count(message: Message):
    await message.answer("❌ Пожалуйста, введите корректное число.")

async def ask_for_category(message: Message, count: int):
    url = "https://www.themealdb.com/api/json/v1/1/list.php?c=list"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            categories = [c["strCategory"] for c in data["meals"]]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")]
            for cat in categories
        ]
    )

    await message.answer(
        f"Вы выбрали {count} рецепт(а/ов).\nТеперь выберите категорию:",
        reply_markup=keyboard
    )
@router.callback_query(F.data.startswith("cat_"))
async def handle_category_choice(callback: CallbackQuery, state: FSMContext):
    category = callback.data.removeprefix("cat_")

    user_data = await state.get_data()
    count = user_data.get("recipe_count", 1)

    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?c={category}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            meals = data.get("meals", [])

    if not meals:
        await callback.message.answer("❌ Рецепты не найдены для этой категории.")
        return

    count = min(count, len(meals))
    selected_meals = choices(meals, k=count)

    ids = [meal["idMeal"] for meal in selected_meals]
    await state.update_data({"selected_meals_ids": ids})

    translated_names = []
    for meal in selected_meals:
        name_en = meal.get("strMeal")
        translation = translator.translate(name_en, src="en", dest="ru")
        name_ru = translation.text
        translated_names.append(f"• {name_ru}")

    result_text = "Как Вам такие варианты:\n" + "\n".join(translated_names)

    show_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Покажи рецепты", callback_data="show_selected_recipes")]
        ]
    )

    selected_ids = [meal["idMeal"] for meal in selected_meals]
    await state.update_data(meal_ids=selected_ids)
    await callback.message.answer(result_text, reply_markup=show_button)
    await callback.answer()

@router.callback_query(F.data == "show_selected_recipes")
async def handle_show_selected_recipes(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    ids = user_data.get("meal_ids", [])

    if not ids:
        await callback.message.answer("❌ Не удалось найти рецепты.")
        return

    async def fetch_meal(meal_id: str):
        url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data["meals"][0] if data["meals"] else None

    # Получаем все рецепты параллельно
    meals = await asyncio.gather(*[fetch_meal(meal_id) for meal_id in ids])

    for meal in meals:
        if meal is None:
            continue

        # Название
        name_en = meal.get("strMeal", "")
        name_ru = translator.translate(name_en, src="en", dest="ru").text

        # Рецепт
        instructions_en = meal.get("strInstructions", "")
        instructions_ru = translator.translate(instructions_en, src="en", dest="ru").text

        # Ингредиенты
        ingredients = []
        for i in range(1, 21):
            ingredient = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ingredient and ingredient.strip():
                full = f"{measure.strip()} {ingredient.strip()}" if measure else ingredient.strip()
                ingredients.append(full)

        # Переводим все ингредиенты списком
        ingredients_ru = [
            translator.translate(item, src="en", dest="ru").text for item in ingredients
        ]

        ingredients_text = ", ".join(ingredients_ru)

        # Финальное сообщение
        final_text = (
            f"🍽️ <b>{name_ru}</b>\n\n"
            f"<b>Рецепт:</b>\n{instructions_ru}\n\n"
            f"<b>Ингредиенты:</b> {ingredients_text}"
        )

        await callback.message.answer(final_text, parse_mode="HTML")

    await state.clear()
    await callback.answer()


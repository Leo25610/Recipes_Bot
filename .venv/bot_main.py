import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, BotCommand
from aiogram.utils.markdown import hbold
from aiogram.client.default import DefaultBotProperties
from recipes_handler import router
from token_data import TOKEN


token=TOKEN
dp=Dispatcher()
dp.include_router(router)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    text = (
        f"👋 Привет, {hbold(message.from_user.full_name)}!\n\n"
        "Я — бот 🍳 для поиска рецептов.\n\n"
        "Вот что я умею:\n"
        "🔎 Найти рецепты по категории (например, Завтрак, Обед, Десерт)\n"
        "🎲 Показать случайные рецепты \n"
        "📋 У каждого рецепта будут шаги приготовления и список ингредиентов\n\n"
        "Напиши команду или выбери её из меню ниже, чтобы начать 👇"
    )
    await message.answer(text)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="category_search_random", description="Выбрать категорию рецептов"),
        BotCommand(command="random", description="Получить случайные рецепты"),
        BotCommand(command="help", description="Описание возможностей бота"),
    ]
    await bot.set_my_commands(commands)



async def main() -> None:
   bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
   await set_bot_commands(bot)
   await dp.start_polling(bot)

if __name__ == "__main__":
   logging.basicConfig(level=logging.INFO, stream=sys.stdout)
   asyncio.run(main())





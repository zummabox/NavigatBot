from aiogram import types, Router
from aiogram.filters import Command
from filters.chat_types import ChatTypeFilter

user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


# @user_private_router.message(Command("start"))
# async def start_cmd(message: types.Message):
#     await message.answer("У вас нет прав пользования.")

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_get_categories,
    orm_add_detail,
    orm_update_detail,
    orm_delete_detail,
    orm_get_detail,
    orm_get_details,
    orm_get_detail_report,
    orm_get_detail_name,

)

from filters.chat_types import ChatTypeFilter, IsAdmin

from kbds.dict_inline_btns import report_buttons, add_buttons
from kbds.inline import get_callback_btns
from kbds.reply import get_keyboard

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


ADMIN_KB = get_keyboard(
    "Добавить данные",
    "Отчет",
    "Отчет по деталям",
    "Поиск",
    placeholder="Выберите действие",
    sizes=(2,),
)


@admin_router.message(Command("start"))
async def add_detail(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)


class SearchProduct(StatesGroup):
    name = State()
    detail_for_search = None


@admin_router.message(F.text == "Поиск")
async def search_at_product(message: types.Message, state: FSMContext):
    await message.answer('Введите название детали или последние 3 цифры децимального номера')
    await state.set_state(SearchProduct.name)


# Хендлер отмены и сброса состояния должен быть всегда именно здесь,
# после того, как только встали в состояние номер 1 (элементарная очередность фильтров)
@admin_router.message(StateFilter("*"), Command("отмена"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:

    current_state = await state.get_state()
    if current_state is None:
        return
    if SearchProduct.detail_for_search:
        SearchProduct.detail_for_search = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


@admin_router.message(SearchProduct.name, F.text)
async def search_name(message: types.Message, state: FSMContext, session: AsyncSession):

    detail_name = message.text

    details = await orm_get_detail_name(session, detail_name)

    if details:
        for detail in details:
            await message.answer(f"Деталь: {detail.name}\nНомер: {detail.number}\nСтатус: {detail.status}\n")
        await message.answer("Вот список найденных деталей ⬆️")
    else:
        await message.answer(f"К сожалению, детали с названием '{detail_name}' не найдены.")

    await state.clear()


@admin_router.message(StateFilter(None), F.text == "Отчет по деталям")
async def detail_report(message: types.Message, session: AsyncSession):
    categories = await orm_get_categories(session)
    btns = {category.name: f'categorys_{category.id}' for category in categories}
    await message.answer("Выберите изделие", reply_markup=get_callback_btns(btns=btns))


@admin_router.callback_query(F.data.startswith('categorys_'))
async def category_choice(callback: types.CallbackQuery, session: AsyncSession):
    categories = await orm_get_categories(session)
    category_id = int(callback.data.split('_')[-1])

    if category_id in [category.id for category in categories]:
        await callback.answer()

        if category_id in report_buttons:
            btns = report_buttons[category_id]
        await callback.message.answer('Выберите деталь.', reply_markup=get_callback_btns(btns=btns))


@admin_router.callback_query(F.data.startswith('report:'))
async def get_detail_report(callback: types.CallbackQuery, session: AsyncSession):
    detail_name = callback.data.split(":")[-1]
    detail_data = await orm_get_detail_report(session, detail_name)
    if detail_data:
        for detail in detail_data:
            await callback.message.answer(
                f"Деталь: {detail.name}\nНомер: {detail.number}\nСтатус: {detail.status}",
                reply_markup=get_callback_btns(
                    btns={
                        "Удалить": f"delete_{detail.id}",
                        "Изменить": f"change_{detail.id}",
                    },
                    sizes=(2,)
                ),
            )
    await callback.answer()
    await callback.message.answer("Вот список деталей ⬆️")


@admin_router.message(F.text == "Отчет")
async def all_report(message: types.Message, session: AsyncSession):
    categories = await orm_get_categories(session)
    btns = {category.name: f'category_{category.id}' for category in categories}
    await message.answer("Выберите изделие", reply_markup=get_callback_btns(btns=btns))


@admin_router.callback_query(F.data.startswith('category_'))
async def all_report(callback: types.CallbackQuery, session: AsyncSession):
    category_id = callback.data.split('_')[-1]
    for detail in await orm_get_details(session, int(category_id)):
        await callback.message.answer(
            f"Деталь: {detail.name}\nНомер: {detail.number}\nСтатус: {detail.status}",
            reply_markup=get_callback_btns(
                btns={
                    "Удалить": f"delete_{detail.id}",
                    "Изменить": f"change_{detail.id}",
                },
                sizes=(2,)
            ),
        )
    await callback.answer()
    await callback.message.answer("Вот список деталий ⬆️")


############################# Удаление детали #########################


@admin_router.callback_query(F.data.startswith("delete_"))
async def delete_product_callback(callback: types.CallbackQuery, session: AsyncSession):
    detail_id = callback.data.split("_")[-1]
    await orm_delete_detail(session, int(detail_id))

    await callback.answer("Деталь удалена")
    await callback.message.answer("Деталь удалена!")


####################### FSM для дабавления/изменения данных  ##############################

class AddDetail(StatesGroup):
    category = State()
    name = State()
    process_details = State()

    detail_for_change = None

    texts = {
        'AddDetail:category': 'Выберите категорию заново:',
        'AddDetail:name': 'Введите название заново:',
        'AddDetail:process_details': 'Введите заводской номер и статус в формате: Номер, Статус',
    }


@admin_router.callback_query(StateFilter(None), F.data.startswith("change_"))
async def change_detail_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    categories = await orm_get_categories(session)
    btns = {category.name: str(category.id) for category in categories}

    detail_id = callback.data.split("_")[-1]

    detail_for_change = await orm_get_detail(session, int(detail_id))

    AddDetail.detail_for_change = detail_for_change

    await callback.answer()
    await callback.message.answer("Выберите изделие", reply_markup=get_callback_btns(btns=btns))
    await state.set_state(AddDetail.category)


##############################################################################################
@admin_router.message(StateFilter(None), F.text == "Добавить данные")
async def add_category(message: types.Message, state: FSMContext, session: AsyncSession):
    categories = await orm_get_categories(session)
    btns = {category.name: str(category.id) for category in categories}
    await message.answer("Выберите изделие", reply_markup=get_callback_btns(btns=btns))

    current_state = await state.get_state()
    await state.update_data(previous_state=current_state)

    await state.set_state(AddDetail.category)


# Хендлер отмены и сброса состояния должен быть всегда именно здесь,
# после того, как только встали в состояние номер 1 (элементарная очередность фильтров)
@admin_router.message(StateFilter("*"), Command("отмена"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:

    current_state = await state.get_state()
    if current_state is None:
        return
    if AddDetail.detail_for_change:
        AddDetail.detail_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


# Вернутся на шаг назад (на прошлое состояние)
@admin_router.callback_query(F.data.startswith("back"))
async def process_back_button(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем текущее состояние
    current_state = await state.get_state()
    if current_state is None:
        # Если мы в начальном состоянии, то назад шагать некуда
        await callback_query.message.answer('Вы находитесь в начальном состоянии.')
        return

    # Получаем данные о предыдущем состоянии
    data = await state.get_data()
    previous_state = data.get('previous_state')

    if previous_state:
        # Устанавливаем предыдущее состояние
        await state.set_state(previous_state)
        # Получаем текст и кнопки для предыдущего состояния
        text_to_send = AddDetail.texts.get(f"AddDetail:{previous_state}")
        buttons = data.get(f"{previous_state}_buttons")
        # Редактируем сообщение с новым текстом и кнопками
        await callback_query.message.edit_text(text=text_to_send, reply_markup=buttons)
    else:
        # Если предыдущего состояния нет, сообщаем об этом пользователю
        await callback_query.message.answer('Предыдущего состояния нет.')


    # current_state = await state.get_state()
    #
    # if current_state == AddDetail.category:
    #     await callback.message.answer(
    #         'Предидущего шага нет, введите название детали или напишите "отмена"'
    #     )
    #     return
    #
    # previous = None
    # for step in AddDetail.__all_states__:
    #     if step.state == current_state:
    #         if previous is not None:
    #             await state.set_state(previous)
    #             text_to_send = AddDetail.texts.get(f"AddDetail:{previous}")
    #             if text_to_send is not None:
    #                 await callback.message.edit_text(text=text_to_send)
    #                 await callback.message.answer(
    #                     f"Вы вернулись к прошлому шагу \n {text_to_send}"
    #                 )
    #             else:
    #                 # Обработка случая, когда текст для предыдущего состояния отсутствует
    #                 await callback.message.answer("Текст для предыдущего шага не найден.")
    #             return
    #         else:
    #             # Обработка случая, когда предыдущего состояния нет
    #             await callback.message.answer("Предидущего шага нет.")
    #             return
    #     previous = step


#########################################################################################


@admin_router.callback_query(AddDetail.category)
async def category_choice(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    categories = await orm_get_categories(session)
    category_id = int(callback.data)
    if category_id in [category.id for category in categories]:

        await callback.answer()
        await state.update_data(category=callback.data)

        # Сохраняем текущее состояние
        current_state = await state.get_state()

        if category_id in add_buttons:
            btns = add_buttons[category_id]
        await callback.message.edit_text('Выберите деталь.', reply_markup=get_callback_btns(btns=btns))
        await state.set_state(AddDetail.name)

        # Обновляем предыдущее состояние
        await state.update_data(previous_state=current_state)
    else:
        await callback.message.answer('Выберите изделие из кнопок.')
        await callback.answer()


######## Ловим любые некорректные действия, кроме нажатия на кнопку выбора категории #########
@admin_router.message(AddDetail.category)
async def category_choice2(message: types.Message):
    await message.answer("'Выберите изделие из кнопок.'")


@admin_router.callback_query(AddDetail.name, F.data.startswith("add:"))
async def add_name(callback: types.CallbackQuery, state: FSMContext):
    name = callback.data.split(":")[-1]
    if name.strip().lower() == 'пропустить':
        await state.update_data(name=AddDetail.detail_for_change.name)
    else:
        # if 2 >= len(message.text) >= 150:
        #     await message.answer(
        #         "Название детали не должно превышать 150 символов\nили быть менее 2-ух символов. \n Введите заново"
        #     )
        #     return
        await callback.answer()
        await state.update_data(name=name)
    await callback.message.edit_text("Введите заводской номер и статус в формате: Номер, Статус",
                                     reply_markup=get_callback_btns(
                                                    btns={"Назад": "back",},
                                                    sizes=(2,)))
    await state.set_state(AddDetail.process_details)


# Хендлер для отлова некорректных вводов для состояния name
@admin_router.message(AddDetail.name)
async def add_name(message: types.Message):
    await message.answer("Выберите деталь из кнопок")


############################################################


@admin_router.message(AddDetail.process_details, F.text)
async def add_process_details(message: types.Message, state: FSMContext, session: AsyncSession):
    details_data = message.text.split("\n")

    for detail_data in details_data:
        data = detail_data.split(',')
        if len(data) == 2:
            number = data[0].strip()
            status = data[1].strip()

            if number == ".":
                number = AddDetail.detail_for_change.number

            if status == ".":
                status = AddDetail.detail_for_change.status

            state_data = await state.get_data()
            state_data['number'] = number
            state_data['status'] = status

            try:
                if AddDetail.detail_for_change:
                    await orm_update_detail(session, AddDetail.detail_for_change.id, state_data)
                    await message.answer("Данные детали обновлены")
                else:
                    await orm_add_detail(session, state_data)  # Вызов функции для добавления данных в БД
                    await message.answer("Детали успешно добавлены")
            except Exception as e:
                await message.answer(f"Произошла ошибка при обновлении/добавлении детали: {e}")
        else:
            await message.answer("Пожалуйста, введите данные в правильном формате: Номер, Статус")
            return

    await state.clear()
    AddDetail.detail_for_change = None


# @admin_router.message(AddDetail.number, F.text)
# async def add_number(message: types.Message, state: FSMContext, session: AsyncSession):
#     if message.text == ".":
#         await state.update_data(number=AddDetail.detail_for_change.number)
#     else:
#         if 4 >= len(message.text):
#             await message.answer(
#                 "Слишком короткое заводской номер. \n Введите заново"
#             )
#             return
#         await state.update_data(number=message.text)
#     await message.answer("Введите статус")
#     await state.set_state(AddDetail.status)
#
#
# ###### Хендлер для отлова некорректных вводов для состояния description #######
# @admin_router.message(AddDetail.number)
# async def add_number2(message: types.Message):
#     await message.answer("Вы ввели не допустимые данные, введите текст описания товара")
#
#
# ##############################################################################################
#
#
# @admin_router.message(AddDetail.status, F.text)
# async def add_status(message: types.Message, state: FSMContext, session: AsyncSession):
#     if message.text == "." and AddDetail.detail_for_change:
#         await state.update_data(status=AddDetail.detail_for_change.status)
#     else:
#         await state.update_data(status=message.text)
#
#     data = await state.get_data()
#     try:
#         if AddDetail.detail_for_change:
#             await orm_update_detail(session, AddDetail.detail_for_change.id, data)
#         else:
#             await orm_add_detail(session, data)
#         await message.answer("Данные добавлены/изменены", reply_markup=ADMIN_KB)
#         await state.clear()
#
#     except Exception as e:
#         await message.answer(
#             f"Ошибка: \n{str(e)}\nОбратитесь к программисту", reply_markup=ADMIN_KB)
#         await state.clear()
#
#     AddDetail.detail_for_change = None
#
#
# # Хендлер для отлова некорректных ввода для состояния price
# @admin_router.message(AddDetail.status)
# async def add_price2(message: types.Message):
#     await message.answer("Вы ввели не допустимые данные, введите статус детали")


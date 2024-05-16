from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Detail, Category


############################ Детали ######################################
async def orm_add_detail(session: AsyncSession, data: dict):
    obj = Detail(
        name=data["name"],
        number=(data["number"]),
        category_id=data["category"],
        status=data["status"],
    )
    session.add(obj)
    await session.commit()


async def orm_get_details(session: AsyncSession, category_id):
    query = select(Detail).where(Detail.category_id == int(category_id))
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_detail_report(session: AsyncSession, name: str):
    query = select(Detail).filter(Detail.name == name)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_detail(session: AsyncSession, detail_id: int):
    query = select(Detail).where(Detail.id == detail_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_get_detail_name(session: AsyncSession, detail_name: str):
    query = select(Detail).where(Detail.name.like("%" + detail_name + "%"))
    result = await session.execute(query)
    return result.scalars().all()


async def orm_update_detail(session: AsyncSession, detail_id: int, data):
    query = update(Detail).where(Detail.id == detail_id).values(
        name=data["name"],
        number=(data["number"]),
        category_id=data["category"],
        status=data["status"],)
    await session.execute(query)
    await session.commit()


async def orm_delete_detail(session: AsyncSession, detail_id: int):
    query = delete(Detail).where(Detail.id == detail_id)
    await session.execute(query)
    await session.commit()


############################ Категории изделий ######################################
async def orm_get_categories(session: AsyncSession):
    query = select(Category)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_create_categories(session: AsyncSession, categories: list):
    query = select(Category)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Category(name=name) for name in categories])
    await session.commit()


# ############################ Модули ######################################
#
# async def orm_add_modul(session: AsyncSession, data: dict):
#     obj = Modul(
#         name=data["name"],
#         number=(data["number"]),
#         category_id=data["category"],
#         status=data["status"],
#     )
#     session.add(obj)
#     await session.commit()
#
#
# async def orm_get_moduls(session: AsyncSession, category_id):
#     query = select(Modul).where(Modul.category_id == int(category_id))
#     result = await session.execute(query)
#     return result.scalars().all()
#
#
# async def orm_get_modul_report(session: AsyncSession, name: str):
#     query = select(Modul).filter(Modul.name == name)
#     result = await session.execute(query)
#     return result.scalars().all()
#
#
# async def orm_get_modul(session: AsyncSession, modul_id: int):
#     query = select(Modul).where(Modul.id == modul_id)
#     result = await session.execute(query)
#     return result.scalar()
#
#
# async def orm_update_modul(session: AsyncSession, modul_id: int, data):
#     query = update(Modul).where(Modul.id == modul_id).values(
#         name=data["name"],
#         number=(data["number"]),
#         category_id=data["category"],
#         status=data["status"],)
#     await session.execute(query)
#     await session.commit()
#
#
# async def orm_delete_modul(session: AsyncSession, modul_id: int):
#     query = delete(Modul).where(Modul.id == modul_id)
#     await session.execute(query)
#     await session.commit()

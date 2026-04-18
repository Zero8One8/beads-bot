"""
Админ-панель: управление товарами (категории, браслеты, витрина).
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from src.database.db import db
from src.database.models import UserModel, CategoryModel, BraceletModel, ShowcaseCollectionModel, ShowcaseItemModel
from src.utils.helpers import format_price

logger = logging.getLogger(__name__)
router = Router()


class AdminProductStates(StatesGroup):
    # Категории
    category_create_name = State()
    category_create_emoji = State()
    category_create_desc = State()
    category_edit = State()
    category_edit_select = State()
    category_edit_field = State()
    
    # Браслеты
    bracelet_create_name = State()
    bracelet_create_price = State()
    bracelet_create_category = State()
    bracelet_create_desc = State()
    bracelet_create_photo = State()
    bracelet_edit = State()
    bracelet_edit_field = State()
    
    # Коллекции витрины
    collection_create_name = State()
    collection_create_emoji = State()
    collection_create_desc = State()
    
    # Товары витрины
    showcase_create_name = State()
    showcase_create_price = State()
    showcase_create_stars = State()
    showcase_create_collection = State()
    showcase_create_desc = State()
    showcase_create_photo = State()


@router.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery):
    """Главное меню управления товарами."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    
    
    text = (
        "💎 *УПРАВЛЕНИЕ ТОВАРАМИ*\n\n"
        "Выберите раздел:"
    )
    
    buttons = [
        [InlineKeyboardButton(text="📋 КАТЕГОРИИ", callback_data="admin_categories")],
        [InlineKeyboardButton(text="💎 БРАСЛЕТЫ", callback_data="admin_bracelets")],
        [InlineKeyboardButton(text="🖼️ КОЛЛЕКЦИИ ВИТРИНЫ", callback_data="admin_collections")],
        [InlineKeyboardButton(text="📦 ТОВАРЫ ВИТРИНЫ", callback_data="admin_showcase")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_menu")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


# ======================================================
# КАТЕГОРИИ
# ======================================================

@router.callback_query(F.data == "admin_categories")
async def admin_categories(callback: CallbackQuery):
    """Список категорий."""
    try:
        if not UserModel.is_admin(callback.from_user.id):
            await callback.answer("❌ Нет прав")
            return
        
        categories = CategoryModel.get_all()
        
        text = f"📋 *КАТЕГОРИИ ТОВАРОВ*\n\nВсего: {len(categories)}\n\n"
        
        buttons = []
        for cat in categories[:10]:  # Лимит для избежания перегрузки
            text += f"{cat['emoji']} {cat['name']} (ID: {cat['id']})\n"
            buttons.append([InlineKeyboardButton(
                text=f"✏️ {cat['emoji']} {cat['name']}",
                callback_data=f"admin_cat_edit_{cat['id']}"
            )])
        
        if len(categories) > 10:
            text += f"\n... и ещё {len(categories) - 10} категорий"
        
        buttons.append([InlineKeyboardButton(text="➕ СОЗДАТЬ", callback_data="admin_cat_create")])
        buttons.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_products")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in admin_categories: {e}")
        await callback.answer("❌ Ошибка загрузки категорий", show_alert=True)


@router.callback_query(F.data == "admin_cat_create")
async def admin_cat_create(callback: CallbackQuery, state: FSMContext):
    """Создание категории."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    await state.set_state(AdminProductStates.category_create_name)
    await callback.message.edit_text(
        "➕ *СОЗДАНИЕ КАТЕГОРИИ*\n\nВведите название категории:",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminProductStates.category_create_name)
async def admin_cat_create_name(message: Message, state: FSMContext):
    await state.update_data(cat_name=message.text)
    await state.set_state(AdminProductStates.category_create_emoji)
    await message.answer("✏️ Введите эмодзи для категории (например, 📦):")


@router.message(AdminProductStates.category_create_emoji)
async def admin_cat_create_emoji(message: Message, state: FSMContext):
    await state.update_data(cat_emoji=message.text)
    await state.set_state(AdminProductStates.category_create_desc)
    await message.answer("📝 Введите описание категории (или /skip):")


@router.message(AdminProductStates.category_create_desc)
async def admin_cat_create_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    description = message.text if message.text != "/skip" else ""
    
    cat_id = CategoryModel.create(
        name=data['cat_name'],
        emoji=data['cat_emoji'],
        description=description
    )
    
    await state.clear()
    await message.answer(
        f"✅ *КАТЕГОРИЯ СОЗДАНА!*\n\nID: {cat_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К КАТЕГОРИЯМ", callback_data="admin_categories")]
        ])
    )


@router.callback_query(F.data.startswith("admin_cat_edit_"))
async def admin_cat_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование категории."""
    cat_id = int(callback.data.replace("admin_cat_edit_", ""))
    cat = CategoryModel.get_by_id(cat_id)
    
    if not cat:
        await callback.answer("❌ Категория не найдена")
        return
    
    
    await state.update_data(edit_cat_id=cat_id)
    
    text = (
        f"✏️ *РЕДАКТИРОВАНИЕ КАТЕГОРИИ*\n\n"
        f"{cat['emoji']} {cat['name']}\n"
        f"📝 {cat['description']}\n\n"
        f"Что хотите изменить?"
    )
    
    buttons = [
        [InlineKeyboardButton(text="📝 Название", callback_data="admin_cat_edit_name")],
        [InlineKeyboardButton(text="😊 Эмодзи", callback_data="admin_cat_edit_emoji")],
        [InlineKeyboardButton(text="📄 Описание", callback_data="admin_cat_edit_desc")],
        [InlineKeyboardButton(text="❌ Удалить", callback_data=f"admin_cat_delete_{cat_id}")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_categories")]
    ]
    
    await state.set_state(AdminProductStates.category_edit_select)
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(AdminProductStates.category_edit_select, F.data.startswith("admin_cat_edit_"))
async def admin_cat_edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("admin_cat_edit_", "")
    await state.update_data(edit_field=field)
    await state.set_state(AdminProductStates.category_edit_field)
    
    prompts = {
        "name": "Введите новое название:",
        "emoji": "Введите новый эмодзи:",
        "desc": "Введите новое описание:"
    }
    
    await callback.message.edit_text(prompts.get(field, "Введите новое значение:"))
    await callback.answer()


@router.message(AdminProductStates.category_edit_field)
async def admin_cat_edit_save(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data['edit_cat_id']
    field = data['edit_field']
    
    updates = {
        "name": "name",
        "emoji": "emoji",
        "desc": "description"
    }
    
    CategoryModel.update(cat_id, **{updates[field]: message.text})
    await state.clear()
    
    await message.answer(
        "✅ Категория обновлена!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К КАТЕГОРИЯМ", callback_data="admin_categories")]
        ])
    )


@router.callback_query(F.data.startswith("admin_cat_delete_"))
async def admin_cat_delete(callback: CallbackQuery):
    """Удаление категории."""
    cat_id = int(callback.data.replace("admin_cat_delete_", ""))
    
    # Проверяем, есть ли товары
    products = CategoryModel.get_products(cat_id)
    if products:
        await callback.message.edit_text(
            f"❌ *НЕЛЬЗЯ УДАЛИТЬ*\n\nВ этой категории есть товары ({len(products)} шт.)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 НАЗАД", callback_data=f"admin_cat_edit_{cat_id}")]
            ])
        )
        await callback.answer()
        return
    
    
    success = CategoryModel.delete(cat_id)
    if success:
        await callback.message.edit_text(
            "✅ Категория удалена",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К КАТЕГОРИЯМ", callback_data="admin_categories")]
            ])
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при удалении",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_categories")]
            ])
        )
    await callback.answer()


# ======================================================
# БРАСЛЕТЫ
# ======================================================

@router.callback_query(F.data == "admin_bracelets")
async def admin_bracelets(callback: CallbackQuery):
    """Список браслетов."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    bracelets = BraceletModel.get_all()
    
    text = f"💎 *БРАСЛЕТЫ*\n\nВсего: {len(bracelets)}\n\n"
    
    buttons = []
    for b in bracelets[:20]:
        text += f"• {b['name']} — {format_price(b['price'])}\n"
        buttons.append([InlineKeyboardButton(
            text=f"✏️ {b['name'][:20]}",
            callback_data=f"admin_bracelet_edit_{b['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="➕ СОЗДАТЬ", callback_data="admin_bracelet_create")])
    buttons.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_products")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "admin_bracelet_create")
async def admin_bracelet_create(callback: CallbackQuery, state: FSMContext):
    """Создание браслета."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    await state.set_state(AdminProductStates.bracelet_create_name)
    await callback.message.edit_text(
        "➕ *СОЗДАНИЕ БРАСЛЕТА*\n\nВведите название:",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminProductStates.bracelet_create_name)
async def admin_bracelet_create_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminProductStates.bracelet_create_price)
    await message.answer("💰 Введите цену в рублях:")


@router.message(AdminProductStates.bracelet_create_price)
async def admin_bracelet_create_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
    except (TypeError, ValueError):
        await message.answer("❌ Введите число")
        return
    
    
    # Получаем список категорий для выбора
    categories = CategoryModel.get_all()
    if not categories:
        await message.answer("❌ Сначала создайте категорию")
        await state.clear()
        return
    
    
    await state.update_data(categories=categories)
    await state.set_state(AdminProductStates.bracelet_create_category)
    
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(
            text=f"{cat['emoji']} {cat['name']}",
            callback_data=f"admin_bracelet_cat_{cat['id']}"
        )])
    
    await message.answer(
        "📋 Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(AdminProductStates.bracelet_create_category, F.data.startswith("admin_bracelet_cat_"))
async def admin_bracelet_create_category(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.replace("admin_bracelet_cat_", ""))
    await state.update_data(category_id=cat_id)
    await state.set_state(AdminProductStates.bracelet_create_desc)
    
    await callback.message.edit_text(
        "📝 Введите описание браслета (или /skip):"
    )
    await callback.answer()


@router.message(AdminProductStates.bracelet_create_desc)
async def admin_bracelet_create_desc(message: Message, state: FSMContext):
    description = message.text if message.text != "/skip" else ""
    await state.update_data(description=description)
    await state.set_state(AdminProductStates.bracelet_create_photo)
    
    await message.answer(
        "🖼️ Отправьте фото браслета (или /skip):"
    )


@router.message(AdminProductStates.bracelet_create_photo)
async def admin_bracelet_create_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    
    if message.photo:
        photo_id = message.photo[-1].file_id
    else:
        photo_id = ""
    
    bracelet_id = BraceletModel.create(
        name=data['name'],
        price=data['price'],
        category_id=data['category_id'],
        description=data['description'],
        image_url=photo_id
    )
    
    await state.clear()
    await message.answer(
        f"✅ *БРАСЛЕТ СОЗДАН!*\n\nID: {bracelet_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К БРАСЛЕТАМ", callback_data="admin_bracelets")]
        ])
    )


# ======================================================
# КОЛЛЕКЦИИ ВИТРИНЫ
# ======================================================

@router.callback_query(F.data == "admin_collections")
async def admin_collections(callback: CallbackQuery):
    """Список коллекций витрины."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    collections = ShowcaseCollectionModel.get_all()
    
    text = f"🖼️ *КОЛЛЕКЦИИ ВИТРИНЫ*\n\nВсего: {len(collections)}\n\n"
    
    buttons = []
    for col in collections:
        text += f"{col['emoji']} {col['name']}\n"
        buttons.append([InlineKeyboardButton(
            text=f"✏️ {col['emoji']} {col['name']}",
            callback_data=f"admin_collection_edit_{col['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="➕ СОЗДАТЬ", callback_data="admin_collection_create")])
    buttons.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_products")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "admin_collection_create")
async def admin_collection_create(callback: CallbackQuery, state: FSMContext):
    """Создание коллекции."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    await state.set_state(AdminProductStates.collection_create_name)
    await callback.message.edit_text(
        "➕ *СОЗДАНИЕ КОЛЛЕКЦИИ*\n\nВведите название:",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminProductStates.collection_create_name)
async def admin_collection_create_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminProductStates.collection_create_emoji)
    await message.answer("✏️ Введите эмодзи для коллекции:")


@router.message(AdminProductStates.collection_create_emoji)
async def admin_collection_create_emoji(message: Message, state: FSMContext):
    await state.update_data(emoji=message.text)
    await state.set_state(AdminProductStates.collection_create_desc)
    await message.answer("📝 Введите описание коллекции (или /skip):")


@router.message(AdminProductStates.collection_create_desc)
async def admin_collection_create_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    description = message.text if message.text != "/skip" else ""
    
    col_id = ShowcaseCollectionModel.create(
        name=data['name'],
        emoji=data['emoji'],
        description=description
    )
    
    await state.clear()
    await message.answer(
        f"✅ *КОЛЛЕКЦИЯ СОЗДАНА!*\n\nID: {col_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К КОЛЛЕКЦИЯМ", callback_data="admin_collections")]
        ])
    )


# ======================================================
# ТОВАРЫ ВИТРИНЫ
# ======================================================

@router.callback_query(F.data == "admin_showcase")
async def admin_showcase(callback: CallbackQuery):
    """Список товаров витрины."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    items = ShowcaseItemModel.get_all()
    
    text = f"📦 *ТОВАРЫ ВИТРИНЫ*\n\nВсего: {len(items)}\n\n"
    
    buttons = []
    for item in items[:20]:
        text += f"• {item['name']} — {format_price(item['price'])} ({item.get('stars_price', 0)}⭐)\n"
        buttons.append([InlineKeyboardButton(
            text=f"✏️ {item['name'][:20]}",
            callback_data=f"admin_showcase_edit_{item['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="➕ СОЗДАТЬ", callback_data="admin_showcase_create")])
    buttons.append([InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_products")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "admin_showcase_create")
async def admin_showcase_create(callback: CallbackQuery, state: FSMContext):
    """Создание товара витрины."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return
    await state.set_state(AdminProductStates.showcase_create_name)
    await callback.message.edit_text(
        "➕ *СОЗДАНИЕ ТОВАРА ВИТРИНЫ*\n\nВведите название:",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminProductStates.showcase_create_name)
async def admin_showcase_create_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminProductStates.showcase_create_price)
    await message.answer("💰 Введите цену в рублях (или 0):")


@router.message(AdminProductStates.showcase_create_price)
async def admin_showcase_create_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
    except ValueError:
        await message.answer("❌ Введите число. Например: 2500")
        return
    await state.update_data(price=price)
    await state.set_state(AdminProductStates.showcase_create_stars)
    await message.answer("⭐ Введите цену в Telegram Stars (или 0):")


@router.message(AdminProductStates.showcase_create_stars)
async def admin_showcase_create_stars(message: Message, state: FSMContext):
    try:
        stars = int(message.text)
    except ValueError:
        stars = 0
    await state.update_data(stars_price=stars)

    collections = ShowcaseCollectionModel.get_all()
    if not collections:
        await message.answer(
            "❌ Сначала создайте коллекцию витрины.\n",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ СОЗДАТЬ КОЛЛЕКЦИЮ", callback_data="admin_collection_create")]
            ])
        )
        await state.clear()
        return


    await state.set_state(AdminProductStates.showcase_create_collection)
    buttons = [[InlineKeyboardButton(
        text=f"{c['emoji']} {c['name']}",
        callback_data=f"admin_sc_col_{c['id']}"
    )] for c in collections]
    await message.answer("📦 Выберите коллекцию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(AdminProductStates.showcase_create_collection, F.data.startswith("admin_sc_col_"))
async def admin_showcase_create_collection(callback: CallbackQuery, state: FSMContext):
    col_id = int(callback.data.replace("admin_sc_col_", ""))
    await state.update_data(collection_id=col_id)
    await state.set_state(AdminProductStates.showcase_create_desc)
    await callback.message.edit_text("📝 Введите описание товара (или /skip):")
    await callback.answer()


@router.message(AdminProductStates.showcase_create_desc)
async def admin_showcase_create_desc(message: Message, state: FSMContext):
    description = "" if message.text == "/skip" else message.text
    await state.update_data(description=description)
    await state.set_state(AdminProductStates.showcase_create_photo)
    await message.answer(
        "🖼️ *ФОТО ТОВАРА*\n\n"
        "Отправьте фото браслета/четок.\n\n"
        "📌 *Рекомендации по фото:*\n"
        "• Хорошее освещение (дневной свет)\n"
        "• Белый или нейтральный фон\n"
        "• Браслет виден полностью\n"
        "• Разрешение от 800x800 пикселей\n\n"
        "Или /skip чтобы добавить фото позже.",
        parse_mode="Markdown"
    )


@router.message(AdminProductStates.showcase_create_photo)
async def admin_showcase_create_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    image_file_id = message.photo[-1].file_id if message.photo else None

    with db.cursor() as c:
        c.execute("""
            INSERT INTO showcase_items
                (name, price, stars_price, collection_id, description, image_file_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'], data['price'], data.get('stars_price', 0),
            data['collection_id'], data['description'], image_file_id, datetime.now()
        ))
        item_id = c.lastrowid

    await state.clear()
    await message.answer(
        f"✅ *ТОВАР СОЗДАН!* ID: {item_id}\n\n"
        f"Товар добавлен в витрину.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 К ТОВАРАМ ВИТРИНЫ", callback_data="admin_showcase")],
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_products")]
        ])
    )


@router.callback_query(F.data.startswith("admin_showcase_edit_"))
async def admin_showcase_edit(callback: CallbackQuery):
    item_id = int(callback.data.replace("admin_showcase_edit_", ""))
    with db.cursor() as c:
        c.execute("SELECT * FROM showcase_items WHERE id = ?", (item_id,))
        item = c.fetchone()
    if not item:
        await callback.answer("❌ Товар не найден")
        return
    text = (
        f"✏️ *ТОВАР: {item['name']}*\n\n"
        f"💰 Цена: {format_price(item['price'])}\n"
        f"⭐ Stars: {item.get('stars_price', 0)}\n"
        f"📝 Описание: {(item['description'] or '')[:100]}\n"
    )
    await callback.message.edit_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 УДАЛИТЬ", callback_data=f"admin_showcase_del_{item_id}")],
            [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_showcase")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_showcase_del_"))
async def admin_showcase_delete(callback: CallbackQuery):
    item_id = int(callback.data.replace("admin_showcase_del_", ""))
    with db.cursor() as c:
        c.execute("DELETE FROM showcase_items WHERE id = ?", (item_id,))
    await callback.message.edit_text(
        "✅ Товар удалён.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К ВИТРИНЕ", callback_data="admin_showcase")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_bracelet_edit_"))
async def admin_bracelet_edit(callback: CallbackQuery):
    """Карточка браслета для базового редактирования."""
    bracelet_id = int(callback.data.replace("admin_bracelet_edit_", ""))
    bracelet = BraceletModel.get_by_id(bracelet_id)
    if not bracelet:
        await callback.answer("❌ Браслет не найден")
        return

    text = (
        f"💎 *БРАСЛЕТ: {bracelet['name']}*\n\n"
        f"💰 Цена: {format_price(bracelet['price'])}\n"
        f"📝 Описание: {(bracelet['description'] or '—')[:300]}\n"
        f"🗂 Категория ID: {bracelet.get('category_id')}\n"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 УДАЛИТЬ", callback_data=f"admin_bracelet_del_{bracelet_id}")],
            [InlineKeyboardButton(text="🔙 К БРАСЛЕТАМ", callback_data="admin_bracelets")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_bracelet_del_"))
async def admin_bracelet_delete(callback: CallbackQuery):
    """Удаление браслета с мягкой логикой из модели."""
    bracelet_id = int(callback.data.replace("admin_bracelet_del_", ""))
    success = BraceletModel.delete(bracelet_id)
    text = "✅ Браслет удалён" if success else "❌ Не удалось удалить браслет"
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К БРАСЛЕТАМ", callback_data="admin_bracelets")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_collection_edit_"))
async def admin_collection_edit(callback: CallbackQuery):
    """Карточка коллекции витрины."""
    collection_id = int(callback.data.replace("admin_collection_edit_", ""))
    with db.cursor() as c:
        c.execute("SELECT * FROM showcase_collections WHERE id = ?", (collection_id,))
        collection = c.fetchone()
        c.execute("SELECT COUNT(*) as cnt FROM showcase_items WHERE collection_id = ?", (collection_id,))
        cnt = c.fetchone()['cnt']

    if not collection:
        await callback.answer("❌ Коллекция не найдена")
        return

    text = (
        f"🖼️ *КОЛЛЕКЦИЯ: {collection['name']}*\n\n"
        f"😊 Эмодзи: {collection.get('emoji') or '—'}\n"
        f"📝 Описание: {(collection.get('description') or '—')[:300]}\n"
        f"📦 Товаров в коллекции: {cnt}\n"
    )
    buttons = [[InlineKeyboardButton(text="🔙 К КОЛЛЕКЦИЯМ", callback_data="admin_collections")]]
    if cnt == 0:
        buttons.insert(0, [InlineKeyboardButton(text="🗑 УДАЛИТЬ КОЛЛЕКЦИЮ", callback_data=f"admin_collection_del_{collection_id}")])

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_collection_del_"))
async def admin_collection_delete(callback: CallbackQuery):
    """Удаление коллекции (только если в ней нет товаров)."""
    collection_id = int(callback.data.replace("admin_collection_del_", ""))
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM showcase_items WHERE collection_id = ?", (collection_id,))
        cnt = c.fetchone()['cnt']
        if cnt > 0:
            await callback.answer("❌ В коллекции есть товары", show_alert=True)
            return
        c.execute("DELETE FROM showcase_collections WHERE id = ?", (collection_id,))

    await callback.message.edit_text(
        "✅ Коллекция удалена",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К КОЛЛЕКЦИЯМ", callback_data="admin_collections")]
        ])
    )
    await callback.answer()

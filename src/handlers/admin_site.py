"""
Админ-панель: генератор статического сайта.
"""
import os
import shutil
import zipfile
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from src.database.db import db
from src.database.models import UserModel, CategoryModel, ShowcaseItemModel, KnowledgeModel, ServiceModel
from src.config import Config
from src.utils.helpers import format_price

logger = logging.getLogger(__name__)
router = Router()
_bot_username = "magic_stones_bot"


@router.callback_query(F.data == "admin_site")
async def admin_site(callback: CallbackQuery):
    """Главное меню генератора сайта."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return

    text = (
        "🌐 *ГЕНЕРАТОР САЙТА*\n\n"
        "Создаёт статический HTML-сайт на основе данных из бота:\n"
        "• Главная страница\n"
        "• Каталог товаров\n"
        "• База знаний (камни)\n"
        "• Услуги\n"
        "• Контакты\n\n"
        "После генерации вы получите ZIP-архив со всеми файлами.\n"
        "Его можно загрузить на любой бесплатный хостинг (GitHub Pages, Netlify)."
    )

    buttons = [
        [InlineKeyboardButton(text="🔄 СГЕНЕРИРОВАТЬ САЙТ", callback_data="site_generate")],
        [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_menu")]
    ]

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data == "site_generate")
async def site_generate(callback: CallbackQuery, bot: Bot):
    """Генерация сайта."""
    if not UserModel.is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав")
        return

    await callback.message.edit_text("🔄 Генерирую сайт... Это может занять до минуты.")

    try:
        # Получаем username бота
        bot_info = await bot.get_me()
        bot_username = bot_info.username or "The_magic_of_stones_bot"

        # Устанавливаем username для использования в генераторах
        global _bot_username
        _bot_username = bot_username

        # Создаём временную папку для сайта
        site_dir = Path(tempfile.gettempdir()) / "magic_site"
        if site_dir.exists():
            shutil.rmtree(site_dir)
        site_dir.mkdir(parents=True)

        # Создаём папки
        (site_dir / 'css').mkdir()
        (site_dir / 'images').mkdir()
        (site_dir / 'catalog').mkdir()
        (site_dir / 'knowledge').mkdir()
        (site_dir / 'services').mkdir()

        # Генерируем CSS
        css_content = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 60px 0; text-align: center; }
        header h1 { font-size: 48px; margin-bottom: 20px; }
        header p { font-size: 18px; max-width: 600px; margin: 0 auto; }
        nav { background: white; padding: 15px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        nav a { color: #4a148c; text-decoration: none; margin: 0 15px; font-weight: 500; }
        nav a:hover { color: #667eea; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 30px; padding: 40px 0; }
        .product-card { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .product-card:hover { transform: translateY(-5px); }
        .product-card img { width: 100%; height: 250px; object-fit: cover; }
        .product-card .info { padding: 20px; }
        .product-card h3 { margin-bottom: 10px; color: #4a148c; }
        .product-card .price { font-size: 20px; font-weight: bold; color: #667eea; margin: 10px 0; }
        .product-card .btn { display: inline-block; background: #4a148c; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 10px; }
        .btn { display: inline-block; background: #4a148c; color: white; text-decoration: none; padding: 12px 30px; border-radius: 30px; font-weight: 600; transition: transform 0.3s; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(74,20,140,0.3); }
        footer { background: #333; color: white; text-align: center; padding: 30px 0; margin-top: 60px; }
        @media (max-width: 768px) { header h1 { font-size: 36px; } }
        """
        (site_dir / 'css' / 'style.css').write_text(css_content, encoding='utf-8')

        # Главная страница
        index_html = generate_index_html()
        (site_dir / 'index.html').write_text(index_html, encoding='utf-8')

        # Каталог
        catalog_html = generate_catalog_html()
        (site_dir / 'catalog' / 'index.html').write_text(catalog_html, encoding='utf-8')

        # База знаний
        knowledge_html = generate_knowledge_html()
        (site_dir / 'knowledge' / 'index.html').write_text(knowledge_html, encoding='utf-8')

        # Услуги
        services_html = generate_services_html()
        (site_dir / 'services' / 'index.html').write_text(services_html, encoding='utf-8')

        # Контакты
        contacts_html = generate_contacts_html()
        (site_dir / 'contacts.html').write_text(contacts_html, encoding='utf-8')

        # Копируем изображения (если есть)
        if Config.PHOTOS_PATH.exists():
            for img in Config.PHOTOS_PATH.glob("*"):
                if img.is_file():
                    shutil.copy2(img, site_dir / 'images' / img.name)

        # Создаём ZIP-архив
        Config.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        zip_path = Config.STORAGE_PATH / f"site_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(site_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, site_dir)
                    zipf.write(file_path, arcname)

        # Отправляем архив
        await callback.message.answer_document(
            document=BufferedInputFile(zip_path.read_bytes(), filename=zip_path.name),
            caption="✅ *Сайт сгенерирован!*\n\nРаспакуйте архив и загрузите на любой хостинг.",
            parse_mode="Markdown"
        )

        # Очищаем
        shutil.rmtree(site_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)

        try:
            await callback.message.edit_text(
                "✅ *Сайт сгенерирован!*\n\n"
                "Архив отправлен выше. Распакуйте и загрузите на хостинг.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_menu")]
                ])
            )
        except Exception:
            pass

    except Exception as e:
        logger.exception("Ошибка генерации сайта")
        err_text = str(e)[:200]
        try:
            await callback.message.edit_text(
                f"❌ *Ошибка генерации сайта:*\n\n`{err_text}`\n\n"
                "Проверьте логи Railway для деталей.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 НАЗАД", callback_data="admin_menu")]
                ])
            )
        except Exception:
            pass


def generate_index_html() -> str:
    """Генерация главной страницы."""
    with db.cursor() as c:
        c.execute("""
            SELECT si.*, sc.name as collection_name
            FROM showcase_items si
            JOIN showcase_collections sc ON si.collection_id = sc.id
            WHERE si.price > 0
            ORDER BY si.created_at DESC
            LIMIT 6
        """)
        products = [dict(row) for row in c.fetchall()]

    products_html = ""
    for p in products:
        products_html += f"""
        <div class="product-card">
            <img src="/images/{p.get('image_file_id', 'default.jpg')}" alt="{p['name']}">
            <div class="info">
                <h3>{p['name']}</h3>
                <p class="price">{format_price(p['price'])}</p>
                <p>{p['description'][:100]}...</p>
                <a href="/catalog/product_{p['id']}.html" class="btn">Подробнее</a>
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Магия Камней - натуральные камни и браслеты</title>
    <meta name="description" content="Магазин натуральных камней. Браслеты, чётки, амулеты. Индивидуальный подбор под вашу энергетику.">
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <nav>
        <div class="container">
            <a href="/">Главная</a>
            <a href="/catalog/">Каталог</a>
            <a href="/knowledge/">База знаний</a>
            <a href="/services/">Услуги</a>
            <a href="/contacts.html">Контакты</a>
        </div>
    </nav>

    <header>
        <div class="container">
            <h1>✨ Магия Камней</h1>
            <p>Натуральные камни с душой. Браслеты, чётки и амулеты из натуральных камней. Индивидуальный подбор под вашу энергетику.</p>
            <a href="https://t.me/{_bot_username}" class="btn">Перейти в Telegram-бот</a>
        </div>
    </header>

    <main class="container">
        <h2 style="text-align: center; margin: 40px 0 20px;">Популярные товары</h2>
        <div class="products-grid">
            {products_html if products_html else '<p style="grid-column: 1/-1; text-align: center;">Скоро здесь появятся наши изделия</p>'}
        </div>

        <div style="text-align: center; margin: 60px 0;">
            <a href="/catalog/" class="btn">Смотреть весь каталог</a>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>© 2026 Магия Камней. Все права защищены.</p>
            <p><a href="https://t.me/{_bot_username}" style="color: white;">Перейти в Telegram-бот</a></p>
        </div>
    </footer>
</body>
</html>"""


def generate_catalog_html() -> str:
    """Генерация страницы каталога."""
    with db.cursor() as c:
        c.execute("""
            SELECT si.*, sc.name as collection_name
            FROM showcase_items si
            JOIN showcase_collections sc ON si.collection_id = sc.id
            WHERE si.price > 0
            ORDER BY si.created_at DESC
        """)
        products = [dict(row) for row in c.fetchall()]

    products_html = ""
    for p in products:
        products_html += f"""
        <div class="product-card">
            <img src="/images/{p.get('image_file_id', 'default.jpg')}" alt="{p['name']}">
            <div class="info">
                <h3>{p['name']}</h3>
                <p class="price">{format_price(p['price'])}</p>
                <p>{p['description'][:100]}...</p>
                <a href="https://t.me/{_bot_username}" class="btn">Купить в Telegram</a>
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Каталог - Магия Камней</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <nav>
        <div class="container">
            <a href="/">Главная</a>
            <a href="/catalog/">Каталог</a>
            <a href="/knowledge/">База знаний</a>
            <a href="/services/">Услуги</a>
            <a href="/contacts.html">Контакты</a>
        </div>
    </nav>

    <main class="container">
        <h1 style="text-align: center; margin: 40px 0;">Каталог товаров</h1>

        <div class="products-grid">
            {products_html if products_html else '<p style="grid-column: 1/-1; text-align: center;">Товаров пока нет</p>'}
        </div>

        <div style="text-align: center; margin: 40px 0;">
            <a href="https://t.me/{_bot_username}" class="btn">Перейти в Telegram-бот</a>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>© 2026 Магия Камней. Все права защищены.</p>
        </div>
    </footer>
</body>
</html>"""


def generate_knowledge_html() -> str:
    """Генерация страницы базы знаний из файлов камней."""
    from src.utils.text_loader import ContentLoader
    stones = ContentLoader.load_all_stones()

    stones_html = ""
    for stone_id, s in stones.items():
        emoji = s.get('EMOJI', '💎')
        name = s.get('TITLE', stone_id)
        short = s.get('SHORT_DESC', '')
        props = s.get('PROPERTIES', '')
        chakra = s.get('CHAKRA', '')

        props_html = ''
        if props:
            props_list = [p.strip() for p in props.split(',')[:4]]
            props_html = ' '.join(f'<span style="background:#f0e6ff;color:#4a148c;padding:3px 8px;border-radius:12px;font-size:12px;margin:2px;display:inline-block">{p}</span>' for p in props_list)

        stones_html += f"""
        <div class="product-card">
            <div class="info" style="padding:24px">
                <h3 style="font-size:20px;margin-bottom:8px">{emoji} {name}</h3>
                <p style="color:#666;margin-bottom:12px;font-size:14px">{short}</p>
                {f'<p style="font-size:12px;color:#888;margin-bottom:8px">Чакра: {chakra}</p>' if chakra else ''}
                <div style="margin-bottom:14px">{props_html}</div>
                <a href="https://t.me/{_bot_username}" class="btn" style="font-size:14px;padding:8px 18px">Подробнее в боте</a>
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>База знаний - Магия Камней</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <nav>
        <div class="container">
            <a href="/">Главная</a>
            <a href="/catalog/">Каталог</a>
            <a href="/knowledge/">База знаний</a>
            <a href="/services/">Услуги</a>
            <a href="/contacts.html">Контакты</a>
        </div>
    </nav>

    <main class="container">
        <h1 style="text-align: center; margin: 40px 0;">База знаний о камнях</h1>

        <div class="products-grid">
            {stones_html if stones_html else '<p style="grid-column: 1/-1; text-align: center;">База знаний пополняется</p>'}
        </div>

        <div style="text-align: center; margin: 40px 0;">
            <a href="https://t.me/{_bot_username}" class="btn">Перейти в Telegram-бот</a>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>© 2026 Магия Камней. Все права защищены.</p>
        </div>
    </footer>
</body>
</html>"""


def generate_services_html() -> str:
    """Генерация страницы услуг."""
    services = ServiceModel.get_all(active_only=True)

    services_html = ""
    for s in services:
        services_html += f"""
        <div class="product-card">
            <div class="info">
                <h3>✨ {s['name']}</h3>
                <p class="price">{format_price(s['price'])}</p>
                <p>{s['description'][:150]}...</p>
                <a href="https://t.me/{_bot_username}" class="btn">Записаться</a>
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Услуги - Магия Камней</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <nav>
        <div class="container">
            <a href="/">Главная</a>
            <a href="/catalog/">Каталог</a>
            <a href="/knowledge/">База знаний</a>
            <a href="/services/">Услуги</a>
            <a href="/contacts.html">Контакты</a>
        </div>
    </nav>

    <main class="container">
        <h1 style="text-align: center; margin: 40px 0;">Наши услуги</h1>

        <div class="products-grid">
            {services_html if services_html else '<p style="grid-column: 1/-1; text-align: center;">Услуги временно недоступны</p>'}
        </div>

        <div style="text-align: center; margin: 40px 0;">
            <a href="https://t.me/{_bot_username}" class="btn">Перейти в Telegram-бот</a>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>© 2026 Магия Камней. Все права защищены.</p>
        </div>
    </footer>
</body>
</html>"""


def generate_contacts_html() -> str:
    """Генерация страницы контактов из настроек бота."""
    with db.cursor() as c:
        c.execute("SELECT key, value FROM bot_settings WHERE key IN ('contact_phone','contact_email','contact_address','working_hours')")
        settings = {row['key']: row['value'] for row in c.fetchall()}

    phone = settings.get('contact_phone', '')
    email = settings.get('contact_email', '')
    address = settings.get('contact_address', '')
    hours = settings.get('working_hours', 'Ежедневно 10:00-22:00')

    contacts_extra = ''
    if phone:
        contacts_extra += f'<p>📱 <strong>Телефон:</strong> {phone}</p>'
    if email:
        contacts_extra += f'<p>📧 <strong>Email:</strong> {email}</p>'
    if address:
        contacts_extra += f'<p>📍 <strong>Адрес:</strong> {address}</p>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Контакты - Магия Камней</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <nav>
        <div class="container">
            <a href="/">Главная</a>
            <a href="/catalog/">Каталог</a>
            <a href="/knowledge/">База знаний</a>
            <a href="/services/">Услуги</a>
            <a href="/contacts.html">Контакты</a>
        </div>
    </nav>

    <main class="container">
        <h1 style="text-align: center; margin: 40px 0;">Контакты</h1>

        <div style="max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
            <h2>Свяжитесь с нами</h2>
            <p>💬 <strong>Telegram-бот:</strong> <a href="https://t.me/{_bot_username}">@{_bot_username}</a></p>
            <p>🕒 <strong>Режим работы:</strong> {hours}</p>
            {contacts_extra}
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/{_bot_username}" class="btn">Перейти в Telegram-бот</a>
            </div>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>© 2026 Магия Камней. Все права защищены.</p>
        </div>
    </footer>
</body>
</html>"""
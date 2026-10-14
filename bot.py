
import asyncio
import logging
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Optional external search: install the ddgs package to enable it.
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


# -------------------- Configuration --------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "infodz.db"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

PAGE_SIZE = 5

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("InfoDZ")


TEXT = {
    "ar": {
        "welcome": (
            "🎓 مرحبًا بك في InfoDZ Bot\n\n"
            "مساعدك للوصول إلى دروس الإعلام الآلي، "
            "الفيديوهات، أعمال TD، الحلول والامتحانات.\n\n"
            "اختر خدمة من القائمة:"
        ),
        "subjects": "📚 المواد",
        "library": "🔎 البحث في المكتبة",
        "online": "🌐 البحث عبر الإنترنت",
        "language": "🌍 تغيير اللغة / Langue",
        "help": "ℹ️ المساعدة",
        "choose_subject": "اختر المادة:",
        "choose_type": "اختر نوع المورد:",
        "all": "📂 جميع الموارد",
        "course": "📘 الدروس",
        "video": "🎥 الفيديوهات",
        "td": "📝 أعمال TD",
        "solution": "✅ الحلول",
        "exam": "📄 الامتحانات",
        "search_library_prompt": "اكتب كلمة أو عبارة للبحث في المكتبة:",
        "search_online_prompt": "اكتب موضوعًا للبحث عنه عبر الإنترنت:",
        "search_empty": "لم أجد نتائج مطابقة. جرّب كلمات أخرى.",
        "online_disabled": "البحث عبر الإنترنت غير مفعّل. ثبّت مكتبة ddgs.",
        "online_error": "تعذّر البحث عبر الإنترنت الآن. حاول لاحقًا.",
        "enter_query": "أرسل عبارة البحث في رسالة نصية.",
        "back": "⬅️ رجوع",
        "home": "🏠 القائمة الرئيسية",
        "next": "التالي ➡️",
        "previous": "⬅️ السابق",
        "page": "الصفحة",
        "no_subjects": "لا توجد مواد في قاعدة البيانات حتى الآن.",
        "no_resources": "لا توجد موارد لهذا الاختيار حتى الآن.",
        "resource_error": "تعذّر قراءة قاعدة البيانات. تحقق من ملفها.",
        "choose_language": "اختر اللغة / Choisissez la langue :",
        "language_changed": "تم تغيير اللغة.",
        "help_text": (
            "استخدم الأزرار للتنقل بين المواد والموارد.\n"
            "يمكنك البحث في المكتبة بالعربية أو الفرنسية.\n"
            "لإلغاء عملية البحث الحالية، أرسل /cancel."
        ),
        "cancelled": "تم إلغاء العملية.",
        "invalid_link": "رابط غير صالح",
    },
    "fr": {
        "welcome": (
            "🎓 Bienvenue sur InfoDZ Bot\n\n"
            "Votre assistant pour les cours, vidéos, TD, "
            "corrigés et examens d'informatique.\n\n"
            "Choisissez un service :"
        ),
        "subjects": "📚 Matières",
        "library": "🔎 Rechercher dans la bibliothèque",
        "online": "🌐 Recherche sur Internet",
        "language": "🌍 Changer de langue / اللغة",
        "help": "ℹ️ Aide",
        "choose_subject": "Choisissez une matière :",
        "choose_type": "Choisissez le type de ressource :",
        "all": "📂 Toutes les ressources",
        "course": "📘 Cours",
        "video": "🎥 Vidéos",
        "td": "📝 Travaux dirigés (TD)",
        "solution": "✅ Corrigés",
        "exam": "📄 Examens",
        "search_library_prompt": "Écrivez un mot ou une expression à rechercher :",
        "search_online_prompt": "Écrivez un sujet à rechercher sur Internet :",
        "search_empty": "Aucun résultat trouvé. Essayez d'autres mots.",
        "online_disabled": "Recherche Internet désactivée. Installez ddgs.",
        "online_error": "La recherche Internet a échoué. Réessayez plus tard.",
        "enter_query": "Envoyez votre recherche dans un message texte.",
        "back": "⬅️ Retour",
        "home": "🏠 Menu principal",
        "next": "Suivant ➡️",
        "previous": "⬅️ Précédent",
        "page": "Page",
        "no_subjects": "Aucune matière n'est enregistrée.",
        "no_resources": "Aucune ressource pour cette sélection.",
        "resource_error": "Impossible de lire la base de données.",
        "choose_language": "Choisissez la langue / اختر اللغة :",
        "language_changed": "Langue modifiée.",
        "help_text": (
            "Utilisez les boutons pour naviguer.\n"
            "La bibliothèque accepte les recherches en arabe et en français.\n"
            "Envoyez /cancel pour annuler la recherche."
        ),
        "cancelled": "Opération annulée.",
        "invalid_link": "Lien invalide",
    },
}

RESOURCE_TYPES = ("all", "course", "video", "td", "solution", "exam")


# -------------------- Database --------------------

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def get_subjects():
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name_ar, name_fr, code "
            "FROM subjects ORDER BY name_ar"
        ).fetchall()


def get_subject(subject_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name_ar, name_fr, code "
            "FROM subjects WHERE id = ?",
            (subject_id,),
        ).fetchone()


def get_resources(subject_id=None, resource_type="all"):
    sql = """
        SELECT r.id, r.title, r.resource_type, r.language,
               r.url, r.description,
               s.name_ar AS subject_ar,
               s.name_fr AS subject_fr
        FROM resources AS r
        LEFT JOIN subjects AS s ON s.id = r.subject_id
        WHERE 1 = 1
    """
    params = []

    if subject_id is not None:
        sql += " AND r.subject_id = ?"
        params.append(subject_id)

    if resource_type != "all":
        sql += " AND LOWER(r.resource_type) = ?"
        params.append(resource_type.lower())

    sql += " ORDER BY r.title COLLATE NOCASE"

    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


def search_resources(query):
    words = [word.strip() for word in query.split() if word.strip()]
    if not words:
        return []

    conditions = []
    params = []

    for word in words[:8]:
        pattern = f"%{word}%"
        conditions.append(
            "(r.title LIKE ? OR r.description LIKE ? "
            "OR s.name_ar LIKE ? OR s.name_fr LIKE ?)"
        )
        params.extend([pattern, pattern, pattern, pattern])

    sql = """
        SELECT r.id, r.title, r.resource_type, r.language,
               r.url, r.description,
               s.name_ar AS subject_ar,
               s.name_fr AS subject_fr
        FROM resources AS r
        LEFT JOIN subjects AS s ON s.id = r.subject_id
        WHERE
    """ + " AND ".join(conditions) + """
        ORDER BY r.title COLLATE NOCASE
        LIMIT 100
    """

    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


# -------------------- Language and keyboards --------------------

def get_lang(context):
    return context.user_data.get("lang", "ar")


def tr(context, key):
    return TEXT[get_lang(context)][key]


def main_keyboard(context):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(context, "subjects"), callback_data="subjects")],
        [InlineKeyboardButton(tr(context, "library"), callback_data="library")],
        [InlineKeyboardButton(tr(context, "online"), callback_data="online")],
        [InlineKeyboardButton(tr(context, "language"), callback_data="language")],
        [InlineKeyboardButton(tr(context, "help"), callback_data="help")],
    ])


def home_button(context):
    return InlineKeyboardButton(
        tr(context, "home"),
        callback_data="home",
    )


def back_home_keyboard(context, back_callback="home"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(context, "back"), callback_data=back_callback)],
        [home_button(context)],
    ])


def subjects_keyboard(subjects, context):
    lang = get_lang(context)
    rows = []

    for subject in subjects:
        name = subject["name_ar"] if lang == "ar" else subject["name_fr"]
        name = name or subject["name_fr"] or subject["name_ar"] or subject["code"]
        rows.append([
            InlineKeyboardButton(
                str(name)[:60],
                callback_data=f"subject:{subject['id']}",
            )
        ])

    rows.append([home_button(context)])
    return InlineKeyboardMarkup(rows)


def resource_type_keyboard(subject_id, context):
    keys = [
        ["all", "course"],
        ["video", "td"],
        ["solution", "exam"],
    ]
    rows = []

    for key_row in keys:
        rows.append([
            InlineKeyboardButton(
                tr(context, key),
                callback_data=f"type:{subject_id}:{key}",
            )
            for key in key_row
        ])

    rows.append([
        InlineKeyboardButton(tr(context, "back"), callback_data="subjects"),
        home_button(context),
    ])
    return InlineKeyboardMarkup(rows)


def pagination_keyboard(context, page, total, back_callback="home"):
    buttons = []
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                tr(context, "previous"),
                callback_data=f"page:{page - 1}",
            )
        )

    if page + 1 < total_pages:
        buttons.append(
            InlineKeyboardButton(
                tr(context, "next"),
                callback_data=f"page:{page + 1}",
            )
        )

    rows = [buttons] if buttons else []
    rows.append([
        InlineKeyboardButton(tr(context, "back"), callback_data=back_callback),
        home_button(context),
    ])
    return InlineKeyboardMarkup(rows)


# -------------------- Resource display --------------------

def valid_http_url(url):
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def resource_label(resource, lang):
    title = resource["title"] or "Untitled"
    subject = resource["subject_ar"] if lang == "ar" else resource["subject_fr"]
    subject = subject or resource["subject_fr"] or resource["subject_ar"] or ""
    kind = resource["resource_type"] or "resource"
    description = (resource["description"] or "").strip()
    language = (resource["language"] or "").strip()

    lines = [f"📌 {title}"]
    if subject:
        lines.append(f"📚 {subject}")
    lines.append(f"📂 {kind}")

    if language:
        lines.append(f"🌐 {language}")

    if description:
        lines.append(description[:500])

    return "\n".join(lines)


async def send_resource_page(update, context, items, page, back_callback="home"):
    lang = get_lang(context)
    total = len(items)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    shown = items[start:start + PAGE_SIZE]

    lines = [
        f"{tr(context, 'page')} {page + 1}/{total_pages}",
        "",
    ]
    buttons = []

    for item in shown:
        lines.append(resource_label(item, lang))
        url = item["url"]

        if valid_http_url(url):
            buttons.append([
                InlineKeyboardButton(
                    f"🔗 {str(item['title'] or 'Open')[:45]}",
                    url=url.strip(),
                )
            ])
        else:
            lines.append(f"⚠️ {tr(context, 'invalid_link')}")
        lines.append("")

    if not shown:
        lines.append(tr(context, "search_empty"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            tr(context, "previous"),
            callback_data=f"page:{page - 1}",
        ))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(
            tr(context, "next"),
            callback_data=f"page:{page + 1}",
        ))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(tr(context, "back"), callback_data=back_callback),
        home_button(context),
    ])

    markup = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "\n".join(lines)[:4000],
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    else:
        await update.effective_message.reply_text(
            "\n".join(lines)[:4000],
            reply_markup=markup,
            disable_web_page_preview=True,
        )


async def show_saved_results(update, context, items, back_callback="home"):
    context.user_data["results"] = [dict(row) for row in items]
    context.user_data["result_back"] = back_callback
    await send_resource_page(update, context, items, 0, back_callback)


# -------------------- Commands --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("search_mode", None)
    await update.effective_message.reply_text(
        tr(context, "welcome"),
        reply_markup=main_keyboard(context),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        tr(context, "help_text"),
        reply_markup=back_home_keyboard(context),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("search_mode", None)
    await update.effective_message.reply_text(tr(context, "cancelled"))
    await start(update, context)


# -------------------- External search --------------------

def external_search(query):
    if DDGS is None:
        return []

    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=5))


async def do_online_search(update, context, query):
    lang = get_lang(context)

    if DDGS is None:
        await update.effective_message.reply_text(
            tr(context, "online_disabled"),
            reply_markup=back_home_keyboard(context),
        )
        return

    status = await update.effective_message.reply_text("🔎 ...")

    try:
        results = await asyncio.to_thread(external_search, query)
        lines = []
        buttons = []

        for item in results:
            title = (item.get("title") or "Result").strip()
            url = (item.get("href") or item.get("url") or "").strip()
            body = (item.get("body") or "").strip()

            lines.append(f"🌐 {title}\n{body[:350]}\n")
            if valid_http_url(url):
                buttons.append([
                    InlineKeyboardButton(title[:50], url=url)
                ])

        if not results:
            lines = [tr(context, "search_empty")]

        buttons.append([home_button(context)])

        await status.edit_text(
            "\n".join(lines)[:4000],
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True,
        )
    except Exception:
        logger.exception("Online search failed")
        await status.edit_text(
            tr(context, "online_error"),
            reply_markup=back_home_keyboard(context),
        )


# -------------------- Button handler --------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    try:
        if data == "home":
            context.user_data.pop("search_mode", None)
            await query.edit_message_text(
                tr(context, "welcome"),
                reply_markup=main_keyboard(context),
            )
            return

        if data == "help":
            await query.edit_message_text(
                tr(context, "help_text"),
                reply_markup=back_home_keyboard(context),
            )
            return

        if data == "language":
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("العربية 🇩🇿", callback_data="lang:ar")],
                [InlineKeyboardButton("Français 🇫🇷", callback_data="lang:fr")],
                [home_button(context)],
            ])
            await query.edit_message_text(
                tr(context, "choose_language"),
                reply_markup=markup,
            )
            return

        if data.startswith("lang:"):
            lang = data.split(":", 1)[1]
            if lang in ("ar", "fr"):
                context.user_data["lang"] = lang
            await query.edit_message_text(
                tr(context, "welcome"),
                reply_markup=main_keyboard(context),
            )
            return

        if data == "subjects":
            subjects = get_subjects()
            if not subjects:
                await query.edit_message_text(
                    tr(context, "no_subjects"),
                    reply_markup=back_home_keyboard(context),
                )
                return

            await query.edit_message_text(
                tr(context, "choose_subject"),
                reply_markup=subjects_keyboard(subjects, context),
            )
            return

        if data.startswith("subject:"):
            subject_id = int(data.split(":")[1])
            subject = get_subject(subject_id)
            if subject is None:
                await query.edit_message_text(
                    tr(context, "no_subjects"),
                    reply_markup=back_home_keyboard(context, "subjects"),
                )
                return

            lang = get_lang(context)
            name = subject["name_ar"] if lang == "ar" else subject["name_fr"]
            name = name or subject["name_ar"] or subject["name_fr"]

            await query.edit_message_text(
                f"📚 {name}\n\n{tr(context, 'choose_type')}",
                reply_markup=resource_type_keyboard(subject_id, context),
            )
            return

        if data.startswith("type:"):
            _, subject_id, resource_type = data.split(":", 2)
            items = get_resources(int(subject_id), resource_type)
            if not items:
                await query.edit_message_text(
                    tr(context, "no_resources"),
                    reply_markup=back_home_keyboard(
                        context, f"subject:{subject_id}"
                    ),
                )
                return

            await show_saved_results(
                update, context, items, f"subject:{subject_id}"
            )
            return

        if data == "library":
            context.user_data["search_mode"] = "library"
            await query.edit_message_text(
                tr(context, "search_library_prompt"),
                reply_markup=back_home_keyboard(context),
            )
            return

        if data == "online":
            context.user_data["search_mode"] = "online"
            await query.edit_message_text(
                tr(context, "search_online_prompt"),
                reply_markup=back_home_keyboard(context),
            )
            return

        if data.startswith("page:"):
            page = int(data.split(":")[1])
            items = context.user_data.get("results", [])
            back = context.user_data.get("result_back", "home")
            await send_resource_page(update, context, items, page, back)
            return

        if data.startswith("back:"):
            await query.edit_message_text(
                tr(context, "welcome"),
                reply_markup=main_keyboard(context),
            )
            return

    except (sqlite3.Error, OSError, ValueError, IndexError):
        logger.exception("Button action failed: %s", data)
        await query.edit_message_text(
            tr(context, "resource_error"),
            reply_markup=back_home_keyboard(context),
        )


# -------------------- Text search handler --------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("search_mode")
    if mode not in ("library", "online"):
        await update.effective_message.reply_text(
            tr(context, "enter_query"),
            reply_markup=main_keyboard(context),
        )
        return

    query = (update.effective_message.text or "").strip()
    if not query:
        await update.effective_message.reply_text(tr(context, "enter_query"))
        return

    context.user_data.pop("search_mode", None)

    if mode == "library":
        try:
            items = search_resources(query)
            if not items:
                await update.effective_message.reply_text(
                    tr(context, "search_empty"),
                    reply_markup=back_home_keyboard(context),
                )
                return

            await show_saved_results(update, context, items)
        except (sqlite3.Error, OSError):
            logger.exception("Library search failed")
            await update.effective_message.reply_text(
                tr(context, "resource_error"),
                reply_markup=back_home_keyboard(context),
            )
    else:
        await do_online_search(update, context, query)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(
        "Unhandled bot error",
        exc_info=context.error,
    )


# -------------------- Start bot --------------------

def main():
    if not TOKEN:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN environment variable. "
            "Set it before starting the bot."
        )

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. "
            "Check that database/infodz.db exists."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )
    app.add_error_handler(error_handler)

    logger.info("InfoDZ Bot is starting...")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()

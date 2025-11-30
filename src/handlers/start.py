from __future__ import annotations

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

# --- Роли ---

ROLE_PATIENT = "🧑‍⚕️ Пациент"
ROLE_STUDENT = "📚 Студент"
ROLE_DOCTOR = "👨‍⚕️ Врач"
ROLE_HELP = "❓ Помощь"

# --- Стили для пациента ---

PATIENT_STYLE_SIMPLE = "⚡️ Краткий формат"
PATIENT_STYLE_DETAILED = "📋 Стандартный формат"
PATIENT_STYLE_SOFT = "💚 Понятный и упрощённый"
PATIENT_STYLE_MAX = "🔍 Расширенный разбор"

# --- Режимы для студента ---

STUDENT_MODE_EXPLAIN = "📘 Объяснить тему"
STUDENT_MODE_TRAIN = "🧠 Потренироваться"
STUDENT_MODE_HELP = "🤝 Помощь с вопросами"

# --- Специальности врача ---

DOC_SPEC_THERAPIST = "🩺 Терапевт"
DOC_SPEC_NEPHRO = "🧬 Нефролог"
DOC_SPEC_CARDIO = "❤️ Кардиолог"
DOC_SPEC_SURGEON = "🔪 Хирург"
DOC_SPEC_OTHER = "📎 Другая специальность"

# --- Главное меню режимов ответов ---

MENU_BRIEF = "🚀 Тезисно"
MENU_HISTORY_BRIEF = "🔮 История"
MENU_DEEP = "🔬 Глубокий анализ"
MENU_CLEAR_HISTORY = "🦠 Очистить историю"


# ---------- КЛАВИАТУРЫ ----------


def role_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [ROLE_PATIENT, ROLE_STUDENT],
        [ROLE_DOCTOR, ROLE_HELP],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def patient_style_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [PATIENT_STYLE_SIMPLE, PATIENT_STYLE_DETAILED],
        [PATIENT_STYLE_SOFT, PATIENT_STYLE_MAX],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def student_mode_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [STUDENT_MODE_EXPLAIN],
        [STUDENT_MODE_TRAIN],
        [STUDENT_MODE_HELP],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def doctor_specialty_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [DOC_SPEC_THERAPIST, DOC_SPEC_NEPHRO],
        [DOC_SPEC_CARDIO, DOC_SPEC_SURGEON],
        [DOC_SPEC_OTHER],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [MENU_BRIEF, MENU_DEEP],
        [MENU_HISTORY_BRIEF, MENU_CLEAR_HISTORY],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------- ХЭНДЛЕР /start ----------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # сбрасываем профиль и историю
    context.user_data.clear()
    context.user_data["docs_history"] = []
    context.user_data["response_mode"] = "balanced"

    text = (
        "Здравствуйте, я MedAll 🤖\n"
        "AI-ассистент для работы с медицинской информацией.\n\n"
        "Чтобы я мог лучше подстроиться под вас, "
        "пожалуйста, выберите, кто вы сейчас:"
    )

    await update.message.reply_text(
        text,
        reply_markup=role_keyboard(),
    )


# ---------- ВЫБОР РОЛИ ----------


async def handle_role_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    choice = update.message.text

    if choice == ROLE_PATIENT:
        context.user_data["profile_type"] = "patient"
        await update.message.reply_text(
            "Отлично! Я буду помогать как пациенту: "
            "объяснять анализы и заключения понятным языком.\n\n"
            "Как вам удобнее, чтобы я объяснял результаты?",
            reply_markup=patient_style_keyboard(),
        )
        return

    if choice == ROLE_STUDENT:
        context.user_data["profile_type"] = "student"
        await update.message.reply_text(
            "Здорово, что вы используете MedAll для учёбы 👨‍🎓\n\n"
            "Какой формат вам сейчас ближе?",
            reply_markup=student_mode_keyboard(),
        )
        return

    if choice == ROLE_DOCTOR:
        context.user_data["profile_type"] = "doctor"
        await update.message.reply_text(
            "Приятно познакомиться, доктор 👨‍⚕️\n"
            "Уточните, пожалуйста, вашу основную специальность — "
            "так мне будет проще подбирать формулировки и акценты:",
            reply_markup=doctor_specialty_keyboard(),
        )
        return

    if choice == ROLE_HELP:
        await show_help(update, context)
        return


# ---------- ПАЦИЕНТ: СТИЛЬ ОБЪЯСНЕНИЙ ----------


async def handle_patient_style(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    style = update.message.text

    if style == PATIENT_STYLE_SIMPLE:
        role_desc = "пациент, предпочитает простые " "и короткие объяснения"
        response_mode = "brief"
    elif style == PATIENT_STYLE_DETAILED:
        role_desc = "пациент, предпочитает подробные " "объяснения с деталями"
        response_mode = "deep"
    elif style == PATIENT_STYLE_SOFT:
        role_desc = "пациент, которому важен мягкий, " "поддерживающий тон"
        response_mode = "balanced"
    elif style == PATIENT_STYLE_MAX:
        role_desc = (
            "пациент, предпочитающий максимально "
            "подробный и структурированный разбор"
        )
        response_mode = "deep"
    else:
        return

    context.user_data["role"] = role_desc
    context.user_data["response_mode"] = response_mode

    await update.message.reply_text(
        "Спасибо! Я настроился под ваш стиль общения 👌\n\n"
        "Теперь можете отправить медицинский документ, текст "
        "заключения или просто описать ситуацию — "
        "я постараюсь объяснить всё максимально понятно.",
        reply_markup=main_menu_keyboard(),
    )


# ---------- СТУДЕНТ: РЕЖИМ ----------


async def handle_student_mode(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    mode = update.message.text

    if mode == STUDENT_MODE_EXPLAIN:
        context.user_data["role"] = "студент-медик (нужны объяснения материала)"
        context.user_data["response_mode"] = "balanced"
        msg = (
            "Ок, буду объяснять темы простым, но точным языком, "
            "с примерами и акцентом на понимание.\n"
            "Можно присылать выдержки из учебников, конспекты "
            "или клинические задачи."
        )
    elif mode == STUDENT_MODE_TRAIN:
        context.user_data["role"] = "студент-медик (режим тренировки и закрепления)"
        context.user_data["response_mode"] = "deep"
        msg = (
            "Отлично! Я могу разбирать материалы и задавать вам "
            "вопросы для закрепления — как мини-тренажёр."
        )
    elif mode == STUDENT_MODE_HELP:
        context.user_data["role"] = "студент-медик (нужна точечная помощь с вопросами)"
        context.user_data["response_mode"] = "brief"
        msg = (
            "Хорошо, задавайте любые вопросы: непонятные места "
            "из лекций, разбор задач, подготовка к зачётам и экзаменам."
        )
    else:
        return

    await update.message.reply_text(
        msg + "\n\nМожете отправить текст или вопрос — "
        "я подстроюсь под ваш уровень.",
        reply_markup=main_menu_keyboard(),
    )


# ---------- ВРАЧ: СПЕЦИАЛЬНОСТЬ ----------


async def handle_doctor_specialty(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    spec = update.message.text

    if spec == DOC_SPEC_OTHER:
        spec_desc = "врач (другая специализация)"
    elif spec in {
        DOC_SPEC_THERAPIST,
        DOC_SPEC_NEPHRO,
        DOC_SPEC_CARDIO,
        DOC_SPEC_SURGEON,
    }:
        spec_desc = f"врач, {spec.split(' ', 1)[1].lower()}"
    else:
        return

    context.user_data["role"] = spec_desc
    context.user_data["response_mode"] = "brief"

    compliment = (
        "Здорово, что вы используете MedAll как помощника в работе — "
        "врачи, которые объясняют пациентам результаты понятным "
        "языком, получают лучшее соблюдение назначений и больше доверия 💛"
    )

    await update.message.reply_text(
        compliment + "\n\nЯ буду давать вам сжатые, структурированные объяснения "
        "с акцентом на клинически важное и, при необходимости, "
        "готовые формулировки для общения с пациентом.",
        reply_markup=main_menu_keyboard(),
    )


# ---------- КНОПКИ МЕНЮ ----------


async def set_brief_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["response_mode"] = "brief"
    await update.message.reply_text(
        "🚀 Режим коротких ответов активирован. "
        "Буду объяснять максимально сжато и по делу."
    )


async def set_deep_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["response_mode"] = "deep"
    await update.message.reply_text(
        "🔬 Режим глубокого анализа активирован. "
        "Буду разбирать максимально подробно и структурированно."
    )


async def show_history_brief(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    history = context.user_data.get("docs_history", [])

    if not history:
        await update.message.reply_text(
            "🔮 История пуста — вы ещё ничего не разбирали."
        )
        return

    text_lines = ["🔮 Тезисная история последних документов:\n"]
    for i, item in enumerate(history[-7:], start=1):
        snippet = item.replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:120] + "…"
        text_lines.append(f"{i}. {snippet}")

    await update.message.reply_text("\n".join(text_lines))


async def clear_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["docs_history"] = []
    await update.message.reply_text("🦠 История очищена.")


# ---------- ПОМОЩЬ ----------


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = context.user_data.get("profile_type")

    if profile == "doctor":
        text = (
            "Я могу помочь вам:\n"
            "• кратко пересказать заключение для пациента понятным языком;\n"
            "• подсветить ключевые моменты, на которые важно сделать акцент;\n"
            "• подготовить варианты формулировок для беседы с пациентом.\n\n"
            "Просто пришлите текст заключения или выписки."
        )
    elif profile == "student":
        text = (
            "Я могу:\n"
            "• объяснить сложные фрагменты текста или статьи;\n"
            "• разобрать клиническую задачу по шагам;\n"
            "• помочь придумать вопросы для самопроверки.\n\n"
            "Пришлите фрагмент материала или вопрос, с которого начнём."
        )
    else:
        text = (
            "Я могу:\n"
            "• объяснить анализы и заключения простым языком;\n"
            "• подсветить, что выглядит спокойным, а что требует "
            "внимания врача;\n"
            "• помочь сформулировать вопросы к врачу.\n\n"
            "Отправьте текст медицинского документа или опишите ситуацию."
        )

    await update.message.reply_text(text, reply_markup=main_menu_keyboard())


# ---------- ЭКСПОРТ ХЭНДЛЕРОВ ----------

start_handler = CommandHandler("start", start)

role_handler = MessageHandler(
    filters.Regex(f"^{ROLE_PATIENT}$|^{ROLE_STUDENT}$|^{ROLE_DOCTOR}$|^{ROLE_HELP}$"),
    handle_role_choice,
)

patient_style_handler = MessageHandler(
    filters.Regex(
        f"^{PATIENT_STYLE_SIMPLE}$|^{PATIENT_STYLE_DETAILED}$|"
        f"^{PATIENT_STYLE_SOFT}$|^{PATIENT_STYLE_MAX}$"
    ),
    handle_patient_style,
)

student_mode_handler = MessageHandler(
    filters.Regex(
        f"^{STUDENT_MODE_EXPLAIN}$|^{STUDENT_MODE_TRAIN}$|" f"^{STUDENT_MODE_HELP}$"
    ),
    handle_student_mode,
)

doctor_spec_handler = MessageHandler(
    filters.Regex(
        f"^{DOC_SPEC_THERAPIST}$|^{DOC_SPEC_NEPHRO}$|"
        f"^{DOC_SPEC_CARDIO}$|^{DOC_SPEC_SURGEON}$|"
        f"^{DOC_SPEC_OTHER}$"
    ),
    handle_doctor_specialty,
)

menu_brief_handler = MessageHandler(
    filters.Regex(f"^{MENU_BRIEF}$"),
    set_brief_mode,
)
menu_deep_handler = MessageHandler(
    filters.Regex(f"^{MENU_DEEP}$"),
    set_deep_mode,
)
menu_history_brief_handler = MessageHandler(
    filters.Regex(f"^{MENU_HISTORY_BRIEF}$"),
    show_history_brief,
)
menu_clear_history_handler = MessageHandler(
    filters.Regex(f"^{MENU_CLEAR_HISTORY}$"),
    clear_history,
)

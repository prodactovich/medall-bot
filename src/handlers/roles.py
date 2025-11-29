from __future__ import annotations

from typing import Literal, Optional

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------- ПЛАНЫ ПОДПИСКИ ----------

PlanType = Literal["basic", "plus", "pro"]


PLAN_BASIC: PlanType = "basic"
PLAN_PLUS: PlanType = "plus"
PLAN_PRO: PlanType = "pro"

BTN_PLAN_BASIC = "🔹 MedAll BASIC"
BTN_PLAN_PLUS = "⭐️ MedAll PLUS"
BTN_PLAN_PRO = "💎 MedAll PRO"


def get_user_plan(context: ContextTypes.DEFAULT_TYPE) -> PlanType:
    plan = context.user_data.get("plan")
    if plan not in (PLAN_BASIC, PLAN_PLUS, PLAN_PRO):
        plan = PLAN_BASIC
        context.user_data["plan"] = plan
    return plan


def set_user_plan(context: ContextTypes.DEFAULT_TYPE, plan: PlanType) -> None:
    context.user_data["plan"] = plan


# ---------- РОЛИ ----------

ROLE_PATIENT = "🧑 Пациент"
ROLE_STUDENT = "📚 Студент"
ROLE_DOCTOR = "👨‍⚕️ Врач"
ROLE_HELP = "❓ Помощь"

BTN_BACK_TO_ROLE = "↩️ Выбрать роль"
BTN_SUBSCRIPTION = "💎 Подписка MedAll"

# ---------- ПАЦИЕНТ: КНОПКИ ----------

PAT_BTN_THESIS = "⚡️ Тезисно"
PAT_BTN_DEEP = "🔍 Глубокий анализ"
PAT_BTN_HISTORY = "📘 История"
PAT_BTN_ACTIONS = "🧭 Порядок действий"

# ---------- ВРАЧ: КНОПКИ ----------

DOC_BTN_GUIDELINES = "📘 Клинические рекомендации"
DOC_BTN_DRUGS = "💊 Справочник лекарств"
DOC_BTN_PATIENT_EXPL = "🗣 Объяснение пациенту"
DOC_BTN_FOREIGN = "🌍 Зарубежная литература"
DOC_BTN_SUPPORT = "💚 Психологическая поддержка врача"

# ---------- СТУДЕНТ: КНОПКИ ----------

ST_BTN_EXPLAIN = "📘 Объяснить тему"
ST_BTN_TRAIN = "🧪 Потренироваться"
ST_BTN_TESTS = "❓ Помощь с тестами"
ST_BTN_ESSAY = "📄 Помощь с рефератом/докладом"
ST_BTN_SUPPORT = "💚 Психологическая помощь"


# ---------- КЛАВИАТУРЫ ----------

def build_role_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [ROLE_PATIENT, ROLE_STUDENT],
        [ROLE_DOCTOR, ROLE_HELP],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def build_patient_menu(plan: PlanType) -> ReplyKeyboardMarkup:
    keyboard = [
        [PAT_BTN_THESIS, PAT_BTN_DEEP],
        [PAT_BTN_ACTIONS, PAT_BTN_HISTORY],
        [BTN_SUBSCRIPTION, BTN_BACK_TO_ROLE],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def build_doctor_menu(plan: PlanType) -> ReplyKeyboardMarkup:
    keyboard = [
        [DOC_BTN_GUIDELINES, DOC_BTN_DRUGS],
        [DOC_BTN_PATIENT_EXPL, DOC_BTN_FOREIGN],
        [DOC_BTN_SUPPORT],
        [BTN_SUBSCRIPTION, BTN_BACK_TO_ROLE],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def build_student_menu(plan: PlanType) -> ReplyKeyboardMarkup:
    keyboard = [
        [ST_BTN_EXPLAIN, ST_BTN_TRAIN],
        [ST_BTN_TESTS, ST_BTN_ESSAY],
        [ST_BTN_SUPPORT],
        [BTN_SUBSCRIPTION, BTN_BACK_TO_ROLE],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def build_doctor_specialties_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        ["🩺 Терапевт", "❤️ Кардиолог"],
        ["🧠 Невролог", "🔪 Хирург"],
        ["🧬 Нефролог", "🍏 Гастроэнтеролог"],
        ["🧒 Педиатр", "👂 ЛОР"],
        ["👁 Офтальмолог", "🧴 Дерматолог"],
        ["🧷 Гинеколог", "💊 Эндокринолог"],
        ["🧲 Онколог", "🦴 Травматолог"],
        ["📋 Другая специальность"],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def build_plan_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [BTN_PLAN_BASIC],
        [BTN_PLAN_PLUS],
        [BTN_PLAN_PRO],
        [BTN_BACK_TO_ROLE],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------- /start ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # лёгкий рефакторинг: всё, что касается ролей/планов, живёт в этом модуле
    context.user_data.setdefault("plan", PLAN_BASIC)
    context.user_data.pop("profile_type", None)
    context.user_data.pop("doctor_specialty", None)
    context.user_data.pop("mode", None)

    text = (
        "Здравствуйте, я MedAll 🤖\n"
        "AI-ассистент для работы с медицинской информацией.\n\n"
        "Кто вы сейчас и как мне лучше подстроиться под вас?"
    )

    await update.message.reply_text(
        text,
        reply_markup=build_role_keyboard(),
    )


start_handler = CommandHandler("start", start)


# ---------- ВЫБОР РОЛИ ----------

async def handle_role_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text
    plan = get_user_plan(context)

    if text == ROLE_PATIENT:
        context.user_data["profile_type"] = "patient"
        context.user_data["mode"] = "patient_thesis"  # по умолчанию — тезисный
        await update.message.reply_text(
            "Я настроюсь под роль пациента: буду объяснять анализы и "
            "заключения понятным языком.\n\n"
            "Вы можете отправить документ или текст, а также выбрать режим ниже.",
            reply_markup=build_patient_menu(plan),
        )
        return

    if text == ROLE_STUDENT:
        context.user_data["profile_type"] = "student"
        context.user_data["mode"] = "student_explain"
        await update.message.reply_text(
            "Роль: студент-медик 👨‍🎓\n\n"
            "Доступно:\n"
            "• 📘 Объяснить тему — разобрать непонятное место простым языком.\n"
            "• 🧪 Потренироваться — разобрать клинические мини-задачи.\n"
            "• ❓ Помощь с тестами — вместе пройтись по вопросам.\n"
            "• 📄 Реферат/доклад — помочь со структурой и текстом.\n"
            "• 💚 Психологическая помощь — поддержать, когда тяжело.\n\n"
            "Отправьте текст, фото или выберите режим ниже.",
            reply_markup=build_student_menu(plan),
        )
        return

    if text == ROLE_DOCTOR:
        context.user_data["profile_type"] = "doctor"
        await update.message.reply_text(
            "Роль: врач 👨‍⚕️\n\n"
            "Уточните, пожалуйста, вашу основную специальность — "
            "так я смогу точнее подбирать формулировки и подсказки.",
            reply_markup=build_doctor_specialties_keyboard(),
        )
        return

    if text == ROLE_HELP:
        await show_help(update, context)
        return


role_handler = MessageHandler(
    filters.Regex(
        f"^{ROLE_PATIENT}$|^{ROLE_STUDENT}$|^{ROLE_DOCTOR}$|^{ROLE_HELP}$"
    ),
    handle_role_choice,
)


# ---------- ВРАЧ: ВЫБОР СПЕЦИАЛЬНОСТИ ----------

async def handle_doctor_specialty(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    spec = update.message.text
    plan = get_user_plan(context)

    # просто сохраняем как есть (эмодзи + текст)
    context.user_data["doctor_specialty"] = spec
    context.user_data["profile_type"] = "doctor"
    context.user_data["mode"] = "doctor_default"

    await update.message.reply_text(
        "Спасибо. Я учту вашу специальность при подборе формулировок.\n\n"
        "Доступно:\n"
        "• 📘 Клинические рекомендации — сжатая информация по запросу.\n"
        "• 💊 Справочник лекарств — действующие вещества, аналоги и формы.\n"
        "• 🗣 Объяснение пациенту — коротко, понятно, в нескольких вариантах.\n"
        "• 🌍 Зарубежная литература — поиск и сжатие данных из зарубежных "
        "источников.\n"
        "• 💚 Психологическая поддержка — выговориться, снять напряжение.\n\n"
        "Выберите, с чего начнём.",
        reply_markup=build_doctor_menu(plan),
    )


doctor_specialty_handler = MessageHandler(
    filters.Regex("^(🩺 Терапевт|❤️ Кардиолог|🧠 Невролог|🔪 Хирург|"
                  "🧬 Нефролог|🍏 Гастроэнтеролог|🧒 Педиатр|👂 ЛОР|"
                  "👁 Офтальмолог|🧴 Дерматолог|🧷 Гинеколог|💊 Эндокринолог|"
                  "🧲 Онколог|🦴 Травматолог|📋 Другая специальность)$"),
    handle_doctor_specialty,
)


# ---------- ОБЩАЯ КНОПКА: ВЕРНУТЬСЯ К ВЫБОРУ РОЛИ ----------

async def handle_back_to_role(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    context.user_data.pop("profile_type", None)
    context.user_data.pop("mode", None)
    await update.message.reply_text(
        "Вы вернулись к выбору роли. "
        "Кто вы сейчас?",
        reply_markup=build_role_keyboard(),
    )


back_to_role_handler = MessageHandler(
    filters.Regex(f"^{BTN_BACK_TO_ROLE}$"),
    handle_back_to_role,
)


# ---------- МЕНЮ ПАЦИЕНТА: КНОПКИ ----------

async def handle_patient_menu_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text
    plan = get_user_plan(context)

    # безопасность: убедимся, что роль — пациент
    if context.user_data.get("profile_type") != "patient":
        return

    if text == PAT_BTN_THESIS:
        context.user_data["mode"] = "patient_thesis"
        await update.message.reply_text(
            "Режим: ⚡️ тезисно.\n"
            "Я буду выделять ключевые маркёры и выводы в сжатом формате.",
        )
        return

    if text == PAT_BTN_DEEP:
        # здесь можно проверять план и предлагать PRO/PLUS
        if plan == PLAN_BASIC:
            await update.message.reply_text(
                "Глубокий анализ доступен полностью в MedAll PRO.\n"
                "В вашем тарифе BASIC будет доступно только несколько "
                "глубоких разборов.\n\n"
                "Чтобы получить расширенный анализ без ограничений, "
                "можно открыть экран подписки.",
                reply_markup=build_plan_keyboard(),
            )
            return

        context.user_data["mode"] = "patient_deep"
        await update.message.reply_text(
            "Режим: 🔍 глубокий анализ.\n"
            "Я буду разбирать информацию подробнее, с логикой и аналогиями.",
        )
        return

    if text == PAT_BTN_HISTORY:
        # здесь пока заглушка — историю формируешь в text_handler
        history = context.user_data.get("docs_history", [])
        if not history:
            await update.message.reply_text(
                "История пока пуста. Вы ещё не отправляли документы."
            )
            return

        lines = ["📘 История последних запросов:"]
        for i, item in enumerate(history[-10:], start=1):
            one_line = item.replace("\n", " ")
            if len(one_line) > 80:
                one_line = one_line[:80] + "…"
            lines.append(f"{i}. {one_line}")
        await update.message.reply_text("\n".join(lines))
        return

    if text == PAT_BTN_ACTIONS:
        # Это кнопка "Порядок действий" — включаем специальный режим
        context.user_data["mode"] = "patient_actions"
        await update.message.reply_text(
            "Режим: 🧭 порядок действий.\n"
            "После вашего следующего сообщения я постараюсь:\n"
            "• обозначить возможные причины;\n"
            "• подсказать, к какому врачу логичнее обратиться;\n"
            "• предложить примерный список вопросов к врачу;\n"
            "• задать вам уточняющие вопросы для более точного маршрута.",
        )
        return


patient_menu_handler = MessageHandler(
    filters.Regex(
        f"^{PAT_BTN_THESIS}$|^{PAT_BTN_DEEP}$|"
        f"^{PAT_BTN_HISTORY}$|^{PAT_BTN_ACTIONS}$"
    ),
    handle_patient_menu_button,
)


# ---------- МЕНЮ ВРАЧА: КНОПКИ ----------

async def handle_doctor_menu_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text
    if context.user_data.get("profile_type") != "doctor":
        return

    # Здесь мы в основном задаём режим/настройку,
    # а сам "умный" ответ будет строиться в text_handler по mode.
    if text == DOC_BTN_GUIDELINES:
        context.user_data["mode"] = "doctor_guidelines"
        await update.message.reply_text(
            "Режим: 📘 клинические рекомендации.\n"
            "Отправьте текст запроса или выдержку — я сожму информацию "
            "по актуальным клин. рекомендациям (без назначения лечения), "
            "со ссылками на источники.",
        )
        return

    if text == DOC_BTN_DRUGS:
        context.user_data["mode"] = "doctor_drugs"
        await update.message.reply_text(
            "Режим: 💊 справочник лекарств.\n"
            "Напишите название препарата или действующее вещество — "
            "я помогу структурировать информацию: состав, форма, аналоги.",
        )
        return

    if text == DOC_BTN_PATIENT_EXPL:
        context.user_data["mode"] = "doctor_patient_expl"
        await update.message.reply_text(
            "Режим: 🗣 объяснение пациенту.\n"
            "Отправьте фрагмент заключения или анализа — "
            "я предложу несколько вариантов объяснения для пациента "
            "разного уровня детализации.",
        )
        return

    if text == DOC_BTN_FOREIGN:
        context.user_data["mode"] = "doctor_foreign"
        await update.message.reply_text(
            "Режим: 🌍 зарубежная литература.\n"
            "Опишите вопрос или приведите выдержку — я постараюсь "
            "ориентироваться на зарубежные источники и указать ключевые "
            "выводы и связи.",
        )
        return

    if text == DOC_BTN_SUPPORT:
        context.user_data["mode"] = "doctor_support"
        await update.message.reply_text(
            "Режим: 💚 психологическая поддержка врача.\n"
            "Можно просто написать, что вас тревожит в работе, "
            "что вы чувствуете — я постараюсь быть бережным "
            "и поддерживающим собеседником.",
        )
        return


doctor_menu_handler = MessageHandler(
    filters.Regex(
        f"^{DOC_BTN_GUIDELINES}$|^{DOC_BTN_DRUGS}$|"
        f"^{DOC_BTN_PATIENT_EXPL}$|^{DOC_BTN_FOREIGN}$|"
        f"^{DOC_BTN_SUPPORT}$"
    ),
    handle_doctor_menu_button,
)


# ---------- МЕНЮ СТУДЕНТА: КНОПКИ ----------

async def handle_student_menu_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text
    if context.user_data.get("profile_type") != "student":
        return

    if text == ST_BTN_EXPLAIN:
        context.user_data["mode"] = "student_explain"
        await update.message.reply_text(
            "Режим: 📘 объяснить тему.\n"
            "Пришлите фрагмент текста, тему из конспекта или учебника — "
            "я объясню проще и структурированно.",
        )
        return

    if text == ST_BTN_TRAIN:
        context.user_data["mode"] = "student_train"
        await update.message.reply_text(
            "Режим: 🧪 потренироваться.\n"
            "Напишите тему — я подготовлю пару клинических мини-задач "
            "и вопросы для самопроверки.",
        )
        return

    if text == ST_BTN_TESTS:
        context.user_data["mode"] = "student_tests"
        await update.message.reply_text(
            "Режим: ❓ помощь с тестами.\n"
            "Пришлите вопросы теста (фото или текстом) — "
            "я помогу разобраться в формулировках и логике.",
        )
        return

    if text == ST_BTN_ESSAY:
        context.user_data["mode"] = "student_essay"
        await update.message.reply_text(
            "Режим: 📄 реферат/доклад.\n"
            "Напишите тему, желаемый объём и, если есть, источники — "
            "я помогу со структурой и ключевыми тезисами.",
        )
        return

    if text == ST_BTN_SUPPORT:
        context.user_data["mode"] = "student_support"
        await update.message.reply_text(
            "Режим: 💚 психологическая поддержка.\n"
            "Можно просто выговориться: учёба в меде сложная, "
            "я постараюсь поддержать и мягко мотивировать.",
        )
        return


student_menu_handler = MessageHandler(
    filters.Regex(
        f"^{ST_BTN_EXPLAIN}$|^{ST_BTN_TRAIN}$|"
        f"^{ST_BTN_TESTS}$|^{ST_BTN_ESSAY}$|"
        f"^{ST_BTN_SUPPORT}$"
    ),
    handle_student_menu_button,
)


# ---------- ПОДПИСКА ----------

async def show_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    plan = get_user_plan(context)

    current = {
        PLAN_BASIC: "BASIC",
        PLAN_PLUS: "PLUS",
        PLAN_PRO: "PRO",
    }[plan]

    text = (
        "💎 MedAll — уровни подписки для пациентов\n\n"
        "Текущий уровень: "
        f"{current}\n\n"
        "🔹 MEDALL BASIC • бесплатно\n"
        "• Простые разъяснения\n"
        "• Стандартный формат\n"
        "• 2 глубоких разбора/мес\n"
        "• OCR: до 3 фото\n"
        "• История: до 10 записей\n\n"
        "⭐️ MEDALL PLUS • условная цена\n"
        "• Более понятные разъяснения\n"
        "• Расширенный анализ\n"
        "• OCR: до 10 фото\n"
        "• История: до 50 записей\n\n"
        "💎 MEDALL PRO • условная цена\n"
        "• Глубокий анализ\n"
        "• Поддерживающий режим\n"
        "• OCR без ограничений\n"
        "• История без лимита\n"
        "• Экспорт PDF и доп. инструменты\n\n"
        "Сейчас можно выбрать уровень (пока без реальной оплаты, "
        "для тестирования логики подписок)."
    )

    await update.message.reply_text(
        text,
        reply_markup=build_plan_keyboard(),
    )


subscription_handler = MessageHandler(
    filters.Regex(f"^{BTN_SUBSCRIPTION}$"),
    show_subscription,
)


async def handle_plan_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text

    if text == BTN_PLAN_BASIC:
        set_user_plan(context, PLAN_BASIC)
        msg = "Вы выбрали 🔹 MedAll BASIC."
    elif text == BTN_PLAN_PLUS:
        set_user_plan(context, PLAN_PLUS)
        msg = "Вы выбрали ⭐️ MedAll PLUS."
    elif text == BTN_PLAN_PRO:
        set_user_plan(context, PLAN_PRO)
        msg = "Вы выбрали 💎 MedAll PRO."
    else:
        return

    profile_type: Optional[str] = context.user_data.get("profile_type")
    plan = get_user_plan(context)

    # после выбора плана возвращаем в меню текущей роли
    if profile_type == "patient":
        kb = build_patient_menu(plan)
    elif profile_type == "doctor":
        kb = build_doctor_menu(plan)
    elif profile_type == "student":
        kb = build_student_menu(plan)
    else:
        kb = build_role_keyboard()

    await update.message.reply_text(
        msg + "\nНастройки учтены.",
        reply_markup=kb,
    )


plan_choice_handler = MessageHandler(
    filters.Regex(
        f"^{BTN_PLAN_BASIC}$|^{BTN_PLAN_PLUS}$|^{BTN_PLAN_PRO}$"
    ),
    handle_plan_choice,
)


# ---------- HELP / ПОДСКАЗКИ ----------

async def show_help(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    profile = context.user_data.get("profile_type")

    if profile == "doctor":
        text = (
            "Режим врача 👨‍⚕️.\n\n"
            "• Клинические рекомендации — сжатая информация по запросу.\n"
            "• Справочник лекарств — действующее вещество, аналоги.\n"
            "• Объяснение пациенту — понятные формулировки.\n"
            "• Зарубежная литература — ориентир по зарубежным данным.\n"
            "• Психологическая поддержка — выговориться и снизить напряжение."
        )
    elif profile == "student":
        text = (
            "Режим студента 📚.\n\n"
            "• Объяснить тему — разобрать непонятный фрагмент.\n"
            "• Потренироваться — клинические мини-кейсы.\n"
            "• Помощь с тестами — разбор вопросов.\n"
            "• Реферат/доклад — структура и опоры.\n"
            "• Психологическая помощь — поддержка и мотивация."
        )
    elif profile == "patient":
        text = (
            "Режим пациента 🧑.\n\n"
            "• Тезисно — короткие выводы и ключевые маркёры.\n"
            "• Глубокий анализ — подробное объяснение (в PRO ещё глубже).\n"
            "• Порядок действий — как подготовиться к приёму и что спросить.\n"
            "• История — краткие записи по прошлым запросам."
        )
    else:
        text = (
            "Я могу работать в трёх режимах:\n"
            "• пациент — разбор анализов и заключений простым языком;\n"
            "• студент — объяснение тем, задачи, тесты;\n"
            "• врач — клинические подсказки и формулировки для пациентов.\n\n"
            "Выберите роль, чтобы продолжить."
        )

    await update.message.reply_text(text)


help_handler = MessageHandler(
    filters.Regex(f"^{ROLE_HELP}$"),
    show_help,
)
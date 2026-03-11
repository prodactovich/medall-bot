from __future__ import annotations

from typing import Literal

from telegram import ReplyKeyboardMarkup

PlanType = Literal["basic", "pro"]

# ---------- Общие кнопки ----------

ROLE_PATIENT = "👨‍⚕️ Пациент"
ROLE_STUDENT = "👩‍🎓 Студент"
ROLE_DOCTOR = "👨‍⚕️ Врач"
ROLE_HELP = "🆘 Помощь"

BTN_BACK_TO_ROLE = "↩️ Выбрать роль"
BTN_PATIENT_CHANGE_ROLE = "🔁 Сменить роль"
BTN_SUBSCRIPTION = "💳 Подписка MedAll"

# ---------- Тарифы ----------

PLAN_BASIC: PlanType = "basic"
PLAN_PRO: PlanType = "pro"
PLAN_PREMIUM: PlanType = PLAN_PRO

BTN_PLAN_BASIC = "🪙 MedAll BASIC"
BTN_PLAN_PREMIUM = "💎 MedAll PREMIUM"

# ---------- Пациент ----------

PAT_BTN_EXPLAIN_DOC = "📎 Расшифровать документ"
PAT_BTN_URGENCY = "🚨 Срочно или нет"
PAT_BTN_24H_PLAN = "🧭 План на 24 часа"
PAT_BTN_QUESTIONS = "🗣️ Вопросы к врачу"
PAT_BTN_HISTORY = "📜 История"

# ---------- Врач ----------

DOC_BTN_GUIDELINES = "📑 Клинические рекомендации"
DOC_BTN_DRUGS = "💊 Справочник лекарств"
DOC_BTN_PATIENT_EXPL = "💬 Объяснение пациенту"
DOC_BTN_FOREIGN = "🌍 Зарубежная литература"
DOC_BTN_SUPPORT = "🤗 Возможность выговориться"

DOCTOR_SPECIALTIES = [
    "👩‍⚕️ Терапевт",
    "❤️ Кардиолог",
    "🧠 Невролог",
    "🔪 Хирург",
    "🩸 Нефролог",
    "🩺 Гастроэнтеролог",
    "🧒 Педиатр",
    "👂 ЛОР",
    "👁️ Офтальмолог",
    "🌿 Дерматолог",
    "⚖️ Гинеколог",
    "🧬 Эндокринолог",
    "🎗️ Онколог",
    "🦴 Травматолог",
    "➕ Другая специальность",
]

# ---------- Студент ----------

ST_BTN_EXPLAIN = "📖 Объяснить тему"
ST_BTN_TRAIN = "📝 Потренироваться"
ST_BTN_TESTS = "❔ Помощь с тестами"
ST_BTN_ESSAY = "🧾 Помощь с рефератом/докладом"
ST_BTN_SUPPORT = "🤝 Психологическая помощь"


# ---------- Клавиатуры ----------


def build_role_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [ROLE_PATIENT, ROLE_STUDENT],
        [ROLE_DOCTOR, ROLE_HELP],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def build_patient_menu(
    plan: PlanType,
) -> ReplyKeyboardMarkup:  # plan на будущее
    keyboard = [
        [PAT_BTN_EXPLAIN_DOC, PAT_BTN_URGENCY],
        [PAT_BTN_24H_PLAN, PAT_BTN_QUESTIONS],
        [PAT_BTN_HISTORY],
        [BTN_SUBSCRIPTION, BTN_PATIENT_CHANGE_ROLE],
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
    rows = [
        DOCTOR_SPECIALTIES[i : i + 2]
        for i in range(0, len(DOCTOR_SPECIALTIES), 2)
    ]
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def build_plan_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [BTN_PLAN_BASIC],
        [BTN_PLAN_PREMIUM],
        [BTN_BACK_TO_ROLE],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

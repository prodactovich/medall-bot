from __future__ import annotations

import os
import re
from typing import Optional

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from domain.enums import PlanCode
from src.config import INTRO_VIDEO_CAPTION, INTRO_VIDEO_PATH
from src.ui import messages
from src.ui.buttons import (
    BTN_BACK_TO_ROLE,
    BTN_PLAN_BASIC,
    BTN_PLAN_PREMIUM,
    BTN_SUBSCRIPTION,
    DOC_BTN_DRUGS,
    DOC_BTN_FOREIGN,
    DOC_BTN_GUIDELINES,
    DOC_BTN_PATIENT_EXPL,
    DOC_BTN_SUPPORT,
    DOCTOR_SPECIALTIES,
    PAT_BTN_ACTIONS,
    PAT_BTN_DEEP,
    PAT_BTN_HISTORY,
    PAT_BTN_THESIS,
    PLAN_BASIC,
    PLAN_PREMIUM,
    PLAN_PRO,
    ROLE_DOCTOR,
    ROLE_HELP,
    ROLE_PATIENT,
    ROLE_STUDENT,
    ST_BTN_ESSAY,
    ST_BTN_EXPLAIN,
    ST_BTN_SUPPORT,
    ST_BTN_TESTS,
    ST_BTN_TRAIN,
    PlanType,
    build_doctor_menu,
    build_doctor_specialties_keyboard,
    build_patient_menu,
    build_plan_keyboard,
    build_role_keyboard,
    build_student_menu,
)


def get_user_plan(context: ContextTypes.DEFAULT_TYPE) -> PlanCode:
    plan = context.user_data.get("plan")

    if plan not in (PlanCode.BASIC, PlanCode.PRO):
        plan = PlanCode.BASIC
        context.user_data["plan"] = plan

    return plan


def set_user_plan(context: ContextTypes.DEFAULT_TYPE, plan: PlanType) -> None:
    """Сохраняем выбранный план в user_data с валидацией."""
    if plan not in (PLAN_BASIC, PLAN_PRO):
        plan = PLAN_BASIC
    context.user_data["plan"] = PlanCode(plan)


def _buttons_regex(*buttons: str) -> str:
    """Безопасный regex для кнопок с эмодзи/символами."""
    escaped = [re.escape(btn) for btn in buttons]
    return f"^({'|'.join(escaped)})$"


async def _delete_intro_if_any(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Удаляет приветственное видео, если ещё лежит в чате."""
    msg_id = context.user_data.pop("intro_video_id", None)
    if not msg_id:
        return
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=msg_id,
        )
    except Exception:
        # Если видео уже удалено или устарело - тихо игнорируем
        pass


# ---------- /start ----------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.setdefault("plan", PLAN_BASIC)
    context.user_data.pop("profile_type", None)
    context.user_data.pop("doctor_specialty", None)
    context.user_data.pop("mode", None)
    context.user_data.pop("intro_video_id", None)

    text = messages.start_greeting()

    # Отправляем приветственное видео, если путь задан и файл есть
    if INTRO_VIDEO_PATH and os.path.exists(INTRO_VIDEO_PATH):
        try:
            video_msg = await update.message.reply_video(
                video=INTRO_VIDEO_PATH,
                caption=INTRO_VIDEO_CAPTION,
                supports_streaming=True,
            )
            context.user_data["intro_video_id"] = video_msg.message_id
        except Exception:
            # Не блокируем старт, если видео не отправилось
            pass

    await update.message.reply_text(
        text,
        reply_markup=build_role_keyboard(),
    )


start_handler = CommandHandler(
    "start", start, filters=filters.ChatType.PRIVATE
)


# ---------- ВЫБОР РОЛИ ----------


async def handle_role_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text
    plan = get_user_plan(context)
    await _delete_intro_if_any(update, context)

    if text == ROLE_PATIENT:
        context.user_data["profile_type"] = "patient"
        context.user_data["mode"] = "patient_thesis"
        await update.message.reply_text(
            messages.patient_intro(),
            reply_markup=build_patient_menu(plan),
        )
        return

    if text == ROLE_STUDENT:
        context.user_data["profile_type"] = "student"
        context.user_data["mode"] = "student_explain"
        await update.message.reply_text(
            "Роль: студент-медик 🎓\n\n"
            "Доступно:\n"
            "• 📖 Объяснить тему - разобрать непонятное место простым языком.\n"
            "• 📝 Потренироваться - разобрать клинические мини-задачи.\n"
            "• ❔ Помощь с тестами - вместе пройтись по вопросам.\n"
            "• 🧾 Реферат/доклад - помочь со структурой и текстом.\n"
            "• 🤝 Психологическая помощь - поддержать, когда тяжело.\n\n"
            "Отправьте текст, фото или выберите режим ниже.",
            reply_markup=build_student_menu(plan),
        )
        return

    if text == ROLE_DOCTOR:
        context.user_data["profile_type"] = "doctor"
        await update.message.reply_text(
            "Роль: врач 🩺\n\n"
            "Уточните, пожалуйста, вашу основную специальность - "
            "так я смогу точнее подбирать формулировки и подсказки.",
            reply_markup=build_doctor_specialties_keyboard(),
        )
        return

    if text == ROLE_HELP:
        await show_help(update, context)
        return


role_handler = MessageHandler(
    filters.ChatType.PRIVATE
    & filters.Regex(
        _buttons_regex(ROLE_PATIENT, ROLE_STUDENT, ROLE_DOCTOR, ROLE_HELP)
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

    context.user_data["doctor_specialty"] = spec
    context.user_data["profile_type"] = "doctor"
    context.user_data["mode"] = "doctor_default"

    await update.message.reply_text(
        "Спасибо. Я учту вашу специальность при подборе формулировок.\n\n"
        "Доступно:\n"
        "• 📑 Клинические рекомендации - сжатая информация по запросу.\n"
        "• 💊 Справочник лекарств - действующие вещества, аналоги и формы.\n"
        "• 💬 Объяснение пациенту - коротко, понятно, в нескольких вариантах.\n"
        "• 🌍 Зарубежная литература - обзор зарубежных источников.\n"
        "• 🤗 Психологическая поддержка - выговориться, снять напряжение.\n\n"
        "Выберите, с чего начнём.",
        reply_markup=build_doctor_menu(plan),
    )


doctor_specialty_handler = MessageHandler(
    filters.ChatType.PRIVATE
    & filters.Regex(
        f"^({'|'.join(re.escape(item) for item in DOCTOR_SPECIALTIES)})$"
    ),
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
        "Вы вернулись к выбору роли. Кто вы сейчас?",
        reply_markup=build_role_keyboard(),
    )


back_to_role_handler = MessageHandler(
    filters.ChatType.PRIVATE & filters.Regex(_buttons_regex(BTN_BACK_TO_ROLE)),
    handle_back_to_role,
)


# ---------- МЕНЮ ПАЦИЕНТА: КНОПКИ ----------


async def handle_patient_menu_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text
    plan = get_user_plan(context)

    if context.user_data.get("profile_type") != "patient":
        return

    if text == PAT_BTN_THESIS:
        context.user_data["mode"] = "patient_thesis"
        await update.message.reply_text(
            "Режим: 📌 тезисно.\n"
            "Я буду выделять ключевые маркёры и выводы в сжатом формате.",
        )
        return

    if text == PAT_BTN_DEEP:
        if plan == PLAN_BASIC:
            await update.message.reply_text(
                "Глубокий анализ полностью доступен в MedAll PREMIUM.\n"
                "В BASIC есть ограниченное число глубоких разборов.\n\n"
                "Чтобы снять ограничения, откройте экран подписки.",
                reply_markup=build_plan_keyboard(),
            )
            return

        context.user_data["mode"] = "patient_deep"
        await update.message.reply_text(
            "Режим: 🧠 глубокий анализ.\n"
            "Я буду разбирать информацию подробнее, с логикой и аналогиями.",
        )
        return

    if text == PAT_BTN_HISTORY:
        history = context.user_data.get("docs_history", [])
        if not history:
            await update.message.reply_text(
                "История пока пуста. Вы ещё не отправляли документы."
            )
            return

        lines = ["📜 История последних запросов:"]
        for i, item in enumerate(history[-10:], start=1):
            one_line = item.replace("\n", " ")
            if len(one_line) > 80:
                one_line = one_line[:80] + "…"
            lines.append(f"{i}. {one_line}")
        await update.message.reply_text("\n".join(lines))
        return

    if text == PAT_BTN_ACTIONS:
        context.user_data["mode"] = "patient_actions"
        await update.message.reply_text(
            "Режим: 🧭 порядок действий.\n"
            "После вашего следующего сообщения я постараюсь:\n"
            "• обозначить возможные причины;\n"
            "• подсказать, к какому врачу логичнее обратиться;\n"
            "• предложить примерный список вопросов к врачу;\n"
            "• задать уточняющие вопросы для более точного маршрута.",
        )
        return


patient_menu_handler = MessageHandler(
    filters.ChatType.PRIVATE
    & filters.Regex(
        _buttons_regex(
            PAT_BTN_THESIS,
            PAT_BTN_DEEP,
            PAT_BTN_HISTORY,
            PAT_BTN_ACTIONS,
        )
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

    if text == DOC_BTN_GUIDELINES:
        context.user_data["mode"] = "doctor_guidelines"
        await update.message.reply_text(
            "Режим: 📑 клинические рекомендации.\n"
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
            "Режим: 💬 объяснение пациенту.\n"
            "Отправьте фрагмент заключения или анализа — "
            "я предложу несколько вариантов объяснения для пациента "
            "разного уровня детализации.",
        )
        return

    if text == DOC_BTN_FOREIGN:
        context.user_data["mode"] = "doctor_foreign"
        await update.message.reply_text(
            "Режим: 🌍 зарубежная литература.\n"
            "Опишите вопрос или приведите выдержку — постараюсь опереться "
            "на зарубежные источники и выделить ключевые выводы.",
        )
        return

    if text == DOC_BTN_SUPPORT:
        context.user_data["mode"] = "doctor_support"
        await update.message.reply_text(
            "Режим: 🤗 психологическая поддержка врача.\n"
            "Можно просто написать, что вас тревожит в работе, "
            "что вы чувствуете — постараюсь быть бережным "
            "и поддерживающим собеседником.",
        )
        return


doctor_menu_handler = MessageHandler(
    filters.ChatType.PRIVATE
    & filters.Regex(
        _buttons_regex(
            DOC_BTN_GUIDELINES,
            DOC_BTN_DRUGS,
            DOC_BTN_PATIENT_EXPL,
            DOC_BTN_FOREIGN,
            DOC_BTN_SUPPORT,
        )
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
            "Режим: 📖 объяснить тему.\n"
            "Пришлите фрагмент текста, тему из конспекта или учебника — "
            "объясню проще и структурированно.",
        )
        return

    if text == ST_BTN_TRAIN:
        context.user_data["mode"] = "student_train"
        await update.message.reply_text(
            "Режим: 📝 потренироваться.\n"
            "Напишите тему — подготовлю пару клинических мини-задач "
            "и вопросы для самопроверки.",
        )
        return

    if text == ST_BTN_TESTS:
        context.user_data["mode"] = "student_tests"
        await update.message.reply_text(
            "Режим: ❔ помощь с тестами.\n"
            "Пришлите вопросы теста (фото или текстом) — "
            "помогу разобраться в формулировках и логике.",
        )
        return

    if text == ST_BTN_ESSAY:
        context.user_data["mode"] = "student_essay"
        await update.message.reply_text(
            "Режим: 🧾 реферат/доклад.\n"
            "Напишите тему, желаемый объём и, если есть, источники — "
            "помогу со структурой и ключевыми тезисами.",
        )
        return

    if text == ST_BTN_SUPPORT:
        context.user_data["mode"] = "student_support"
        await update.message.reply_text(
            "Режим: 🤝 психологическая поддержка.\n"
            "Можно просто выговориться: учёба в меде сложная, "
            "я постараюсь поддержать и мягко мотивировать.",
        )
        return


student_menu_handler = MessageHandler(
    filters.ChatType.PRIVATE
    & filters.Regex(
        _buttons_regex(
            ST_BTN_EXPLAIN,
            ST_BTN_TRAIN,
            ST_BTN_TESTS,
            ST_BTN_ESSAY,
            ST_BTN_SUPPORT,
        )
    ),
    handle_student_menu_button,
)


# ---------- ПОДПИСКА ----------


async def show_subscription(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    plan = get_user_plan(context)
    text = messages.subscription_text(str(plan))

    await update.message.reply_text(
        text,
        reply_markup=build_plan_keyboard(),
    )


subscription_handler = MessageHandler(
    filters.ChatType.PRIVATE & filters.Regex(_buttons_regex(BTN_SUBSCRIPTION)),
    show_subscription,
)


async def handle_plan_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text

    if text == BTN_PLAN_BASIC:
        set_user_plan(context, PLAN_BASIC)
        msg = "Вы выбрали 🟢 MedAll BASIC."
    elif text == BTN_PLAN_PREMIUM:
        set_user_plan(context, PLAN_PREMIUM)
        msg = "Вы выбрали 💎 MedAll PREMIUM."
    else:
        return

    profile_type: Optional[str] = context.user_data.get("profile_type")
    plan = get_user_plan(context)

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
    filters.ChatType.PRIVATE
    & filters.Regex(_buttons_regex(BTN_PLAN_BASIC, BTN_PLAN_PREMIUM)),
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
            "Режим врача 🩺.\n\n"
            "• Клинические рекомендации — сжатая информация по запросу.\n"
            "• Справочник лекарств — действующее вещество, аналоги.\n"
            "• Объяснение пациенту — понятные формулировки.\n"
            "• Зарубежная литература — ориентир по зарубежным данным.\n"
            "• Психологическая поддержка — выговориться и снизить напряжение."
        )
    elif profile == "student":
        text = (
            "Режим студента 🎓.\n\n"
            "• Объяснить тему — разобрать непонятный фрагмент.\n"
            "• Потренироваться — клинические мини-кейсы.\n"
            "• Помощь с тестами — разбор вопросов.\n"
            "• Реферат/доклад — структура и опоры.\n"
            "• Психологическая помощь — поддержка и мотивация."
        )
    elif profile == "patient":
        text = (
            "Режим пациента 🤒.\n\n"
            "• Тезисно — короткие выводы и ключевые маркёры.\n"
            "• Глубокий анализ — подробное объяснение (в PREMIUM ещё глубже).\n"
            "• Порядок действий — подготовка к приёму и вопросы врачу.\n"
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
    filters.ChatType.PRIVATE & filters.Regex(_buttons_regex(ROLE_HELP)),
    show_help,
)

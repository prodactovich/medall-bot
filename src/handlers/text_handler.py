from __future__ import annotations

from typing import Any, Dict

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from src.ai_client import ask_deepseek
from src.handlers.roles import (
    PLAN_BASIC,
    PLAN_PLUS,
    PLAN_PRO,
    get_user_plan,
)
from src.nlp_utils import (
    build_ai_input,
    detect_doc_type,
    detect_red_flags,
    detect_user_emotion,
)

# Простые лимиты по планам (за сессию пользователя)
PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    PLAN_BASIC: {
        "docs": 10,  # сколько запросов к ИИ за сессию
        "deep": 2,  # сколько глубоких разборов (patient_deep) за сессию
    },
    PLAN_PLUS: {
        "docs": 50,
        "deep": 9999,
    },
    PLAN_PRO: {
        "docs": None,  # None = без ограничений
        "deep": None,
    },
}


def _is_deep_mode(profile: str | None, mode: str | None) -> bool:
    """
    Какие режимы считаем «глубокими» для лимитов.
    Пока жёстко: глубокий анализ пациента, при желании можно добавить ещё.
    """
    if profile == "patient" and mode == "patient_deep":
        return True
    # сюда можно добавить doctor_guidelines, doctor_foreign и т.п.
    return False


def _build_role_description(
    profile: str | None,
    mode: str | None,
    plan: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> str:
    """
    Строим человекочитаемое описание роли+режима+плана
    для передачи в ИИ (в system prompt).
    """
    plan_label = {
        PLAN_BASIC: "MedAll BASIC",
        PLAN_PLUS: "MedAll PLUS",
        PLAN_PRO: "MedAll PRO",
    }.get(plan, "MedAll BASIC")

    if profile == "patient":
        if mode == "patient_thesis":
            return (
                f"Пациент, тариф {plan_label}, режим: тезисное краткое "
                "объяснение результатов и документов."
            )
        if mode == "patient_deep":
            return (
                f"Пациент, тариф {plan_label}, режим: глубокий анализ с "
                "деталями, аналогиями и аккуратными выводами."
            )
        if mode == "patient_actions":
            return (
                f"Пациент, тариф {plan_label}, режим: помощь с порядком действий "
                "и подготовкой к визиту к врачу (без постановки диагноза)."
            )
        return f"Пациент, тариф {plan_label}, без уточнённого режима."

    if profile == "doctor":
        spec = (
            context.user_data.get("doctor_specialty")
            or "врач без указания специальности"
        )
        if mode == "doctor_guidelines":
            return (
                f"{spec}, тариф {plan_label}, режим: сжатое изложение актуальных "
                "клинических рекомендаций по запросу."
            )
        if mode == "doctor_drugs":
            return (
                f"{spec}, тариф {plan_label}, режим: справочник лекарств "
                "(действующее вещество, аналоги, формы, но без назначения лечения)."
            )
        if mode == "doctor_patient_expl":
            return (
                f"{spec}, тариф {plan_label}, режим: формулировки для объяснения "
                "пациенту, в нескольких вариантах."
            )
        if mode == "doctor_foreign":
            return (
                f"{spec}, тариф {plan_label}, режим: обзор зарубежных источников "
                "и выводов по теме."
            )
        if mode == "doctor_support":
            return (
                f"{spec}, тариф {plan_label}, режим: психологическая поддержка "
                "и профилактика выгорания."
            )
        return f"{spec}, тариф {plan_label}, без уточнённого режима."

    if profile == "student":
        if mode == "student_explain":
            return (
                f"Студент-медик, тариф {plan_label}, режим: объяснение темы "
                "простым, но точным языком."
            )
        if mode == "student_train":
            return (
                f"Студент-медик, тариф {plan_label}, режим: тренировка на "
                "клинических мини-кейсах и вопросах."
            )
        if mode == "student_tests":
            return (
                f"Студент-медик, тариф {plan_label}, режим: помощь с тестами "
                "и разбором формулировок."
            )
        if mode == "student_essay":
            return (
                f"Студент-медик, тариф {plan_label}, режим: помощь с "
                "рефератом/докладом (структура, ключевые тезисы)."
            )
        if mode == "student_support":
            return (
                f"Студент-медик, тариф {plan_label}, режим: психологическая "
                "поддержка и мягкая мотивация."
            )
        return f"Студент-медик, тариф {plan_label}, без уточнённого режима."

    # если по какой-то причине профиль ещё не выбран
    return f"Пользователь без заданной роли, тариф {plan_label}."


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Главный обработчик текстовых сообщений.
    Здесь:
    - проверяем, что роль выбрана;
    - учитываем текущий план (BASIC / PLUS / PRO);
    - применяем простые лимиты;
    - определяем doc_type / эмоции / red_flags;
    - вызываем DeepSeek с учётом роли/режима;
    - обновляем историю и счётчики.
    """
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    profile = context.user_data.get("profile_type")
    mode = context.user_data.get("mode")
    plan = get_user_plan(context)

    # Если роль ещё не выбрана — отправляем к /start
    if profile is None:
        await update.message.reply_text(
            "Чтобы я мог правильно подстроиться под вас, "
            "сначала выберите роль через /start."
        )
        return

    # --- Лимиты по планам ---

    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[PLAN_BASIC])
    usage = context.user_data.setdefault(
        "usage",
        {"docs_used": 0, "deep_used": 0},
    )

    # общий лимит документов
    docs_cap = limits.get("docs")
    if docs_cap is not None and usage["docs_used"] >= docs_cap:
        await update.message.reply_text(
            "Вы использовали доступный лимит разборов для вашего уровня "
            "подписки.\n\n"
            "Можно продолжать пользоваться базовыми функциями или "
            "открыть MedAll PLUS / PRO в разделе подписки 💎."
        )
        return

    # лимит «глубокого анализа» для некоторых режимов
    if _is_deep_mode(profile, mode):
        deep_cap = limits.get("deep")
        if deep_cap is not None and usage["deep_used"] >= deep_cap:
            await update.message.reply_text(
                "Лимит глубоких разборов в текущем уровне подписки исчерпан.\n\n"
                "Вы можете переключиться в режим тезисного объяснения или "
                "рассмотреть подключение MedAll PRO для расширенного анализа 💎."
            )
            return

    # --- Эвристики по тексту ---
    doc_type = detect_doc_type(user_text)
    emotion = detect_user_emotion(user_text)
    red_flags = detect_red_flags(user_text)

    # Описание роли+режима для ИИ
    role_desc = _build_role_description(profile, mode, plan, context)

    # Формируем вход для ИИ
    # ВАЖНО: здесь больше никаких именованных аргументов,
    # чтобы не конфликтовать с реальной сигнатурой build_ai_input.
    ai_input = build_ai_input(user_text)

    usage_info: dict = {}

    answer = await ask_deepseek(
        ai_input,
        role=role_desc,
        mode=mode or "",
        doc_type=doc_type,
        emotion=emotion,
        red_flags=red_flags,
        usage_tracker=usage_info,
        plan=plan,
    )

    usage_info: dict = {}

    answer = await ask_deepseek(
        ai_input,
        role=role_desc,
        mode=mode or "",
        doc_type=doc_type,
        emotion=emotion,
        red_flags=red_flags,
        usage_tracker=usage_info,
        plan=plan,
    )

    # Обновляем историю пользователя
    history = context.user_data.setdefault("docs_history", [])
    history.append(user_text[:500])

    # Обновляем usage по плану
    usage["docs_used"] += 1
    if _is_deep_mode(profile, mode):
        usage["deep_used"] += 1

    # Грубый учёт «символов» на уровне приложения (можно потом заменить на tokens)
    app_usage = context.application.bot_data.setdefault(
        "usage",
        {"prompt_chars": 0, "completion_chars": 0},
    )
    app_usage["prompt_chars"] += len(ai_input)
    app_usage["completion_chars"] += len(answer)

    # Для отладки — выводим в консоль
    print(
        f"[USAGE] plan={plan}, profile={profile}, mode={mode}, "
        f"docs_used={usage['docs_used']}, deep_used={usage['deep_used']}, "
        f"prompt_chars={app_usage['prompt_chars']}, "
        f"completion_chars={app_usage['completion_chars']}"
    )

    await update.message.reply_text(answer)


text_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    handle_message,
)

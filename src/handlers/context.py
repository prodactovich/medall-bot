"""
Docstring for src.handlers.context.
Фабрика текстовых описаний. Функция берёт технические параметры
пользователя (профиль, режим, тариф) и преобразует их в понятное
для ИИ и человека описание, которое задаёт контекст для генерации ответов.
"""

from __future__ import annotations

from telegram.ext import ContextTypes

from .roles import PLAN_BASIC, PLAN_PRO


def build_role_description(
    profile: str | None,
    mode: str | None,
    plan: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> str:
    """
    Строит человекочитаемое описание роли+режима+плана
    для передачи в ИИ (в system prompt).
    """
    plan_label = {
        PLAN_BASIC: "MedAll BASIC",
        PLAN_PRO: "MedAll PREMIUM",
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

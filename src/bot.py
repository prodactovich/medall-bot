from __future__ import annotations

from telegram.ext import ApplicationBuilder

from src.config import TELEGRAM_TOKEN
from src.handlers.roles import (
    start_handler,
    role_handler,
    doctor_specialty_handler,
    back_to_role_handler,
    patient_menu_handler,
    doctor_menu_handler,
    student_menu_handler,
    subscription_handler,
    plan_choice_handler,
    help_handler,
)
from src.handlers.text_handler import text_handler
from src.handlers.photo_handler import photo_handler


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # /start
    app.add_handler(start_handler)

    # роли и выбор спец-сти
    app.add_handler(role_handler)
    app.add_handler(doctor_specialty_handler)

    # кнопка "вернуться к выбору роли"
    app.add_handler(back_to_role_handler)

    # меню по ролям
    app.add_handler(patient_menu_handler)
    app.add_handler(doctor_menu_handler)
    app.add_handler(student_menu_handler)

    # подписка
    app.add_handler(subscription_handler)
    app.add_handler(plan_choice_handler)

    # help
    app.add_handler(help_handler)

    # контент
    app.add_handler(photo_handler)
    app.add_handler(text_handler)

    print("MedAll бот запущен…")
    app.run_polling()


if __name__ == "__main__":
    main()
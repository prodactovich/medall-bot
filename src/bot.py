from __future__ import annotations

from telegram.error import Conflict, Forbidden
from telegram.ext import ApplicationBuilder

from src.config import TELEGRAM_TOKEN, validate_runtime_config
from src.handlers.photo_handler import photo_handler
from src.handlers.roles import (
    about_handler,
    back_from_subscription_handler,
    back_to_role_handler,
    doctor_menu_handler,
    doctor_specialty_handler,
    patient_menu_handler,
    plan_choice_handler,
    role_handler,
    start_handler,
    student_menu_handler,
    subscription_handler,
)
from src.handlers.text_handler import text_handler
from src.security import cleanup_rate_limit_buckets


def main() -> None:
    validate_runtime_config()

    # Explicitly set longer timeouts to avoid connect/read timeouts on slow networks.
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # /start
    app.add_handler(start_handler)

    # роли и выбор спец-сти
    app.add_handler(role_handler)
    app.add_handler(doctor_specialty_handler)

    # кнопка "вернуться к выбору роли"
    app.add_handler(back_to_role_handler)
    app.add_handler(back_from_subscription_handler)

    # меню по ролям
    app.add_handler(patient_menu_handler)
    app.add_handler(doctor_menu_handler)
    app.add_handler(student_menu_handler)

    # подписка
    app.add_handler(subscription_handler)
    app.add_handler(plan_choice_handler)

    # about
    app.add_handler(about_handler)

    # контент
    app.add_handler(photo_handler)
    app.add_handler(text_handler)

    async def handle_errors(update, context):
        # Игнорируем ситуации, когда пользователь заблокировал бота
        # или чат больше недоступен, чтобы не падать на отправке сообщений.
        if isinstance(context.error, (Forbidden, Conflict)):
            return
        raise context.error

    app.add_error_handler(handle_errors)

    async def cleanup_rate_limits_job(context):
        try:
            deleted = cleanup_rate_limit_buckets()
            if deleted:
                print(f"[RATE_LIMIT] cleaned {deleted} expired buckets")
        except Exception as e:
            print(f"[RATE_LIMIT] cleanup job failed: {e}")

    if app.job_queue:
        app.job_queue.run_repeating(
            cleanup_rate_limits_job,
            interval=300,
            first=300,
            name="cleanup_rate_limit_buckets",
        )

    print("MedAll бот запущен…")
    app.run_polling()


if __name__ == "__main__":
    main()

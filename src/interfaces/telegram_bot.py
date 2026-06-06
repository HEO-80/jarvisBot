"""
Interfaz de Telegram para Jarvis.
Recibe mensajes, los enruta al Cerebro y devuelve respuestas.
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_ID
from agentes.cerebro_openclaw import Cerebro

logger = logging.getLogger("jarvis.telegram")

CEREBRO: Cerebro | None = None


def _is_authorized(update: Update) -> bool:
    return update.effective_user.id == TELEGRAM_ALLOWED_USER_ID


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Acceso denegado.")
        return
    await update.message.reply_text(
        "Jarvis activo. ¿En qué puedo ayudarte?\n\n"
        "Comandos:\n"
        "/reset — borrar contexto\n"
        "/status — estado del sistema"
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    CEREBRO.reset_context()
    await update.message.reply_text("Contexto borrado. Empezamos de cero.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    msgs = len(CEREBRO.history)
    await update.message.reply_text(
        f"Sistema activo.\n"
        f"Modelo: {CEREBRO.model.model_name}\n"
        f"Mensajes en contexto: {msgs}"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        logger.warning(f"Acceso denegado para user_id={update.effective_user.id}")
        await update.message.reply_text("No estás autorizado para usar este bot.")
        return

    user_text = update.message.text
    if not user_text:
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    response = CEREBRO.chat(user_text)

    # Telegram tiene límite de 4096 chars por mensaje
    if len(response) > 4096:
        for i in range(0, len(response), 4096):
            await update.message.reply_text(response[i:i+4096])
    else:
        await update.message.reply_text(response)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error en update: {context.error}", exc_info=context.error)


def create_app(cerebro: Cerebro) -> Application:
    global CEREBRO
    CEREBRO = cerebro

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Aplicación Telegram configurada")
    return app

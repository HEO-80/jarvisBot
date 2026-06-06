"""
Interfaz de Telegram para Jarvis.
Maneja mensajes de texto y voz, enruta al Cerebro y responde con audio.
"""
import logging
import os
import tempfile

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatAction

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_ID, VOICE_ENABLED, VOICE_MODEL
from agentes.cerebro_openclaw import Cerebro
from utils.voice import clean_for_tts, text_to_speech, transcribe, ogg_to_wav

logger = logging.getLogger("jarvis.telegram")

CEREBRO: Cerebro | None = None


def _is_authorized(update: Update) -> bool:
    return update.effective_user.id == TELEGRAM_ALLOWED_USER_ID


async def _send_reply(update: Update, text: str, force_text: bool = False):
    if VOICE_ENABLED and not force_text:
        spoken = clean_for_tts(text)
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = os.path.join(tmp, "response.wav")
            if text_to_speech(spoken, wav_path, VOICE_MODEL):
                with open(wav_path, "rb") as audio:
                    caption = spoken[:1024] if len(spoken) <= 1024 else spoken[:1021] + "..."
                    await update.message.reply_voice(audio, caption=caption)
                return
        logger.warning("TTS falló, enviando texto")

    # Fallback o modo texto: partir si supera límite Telegram
    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            await update.message.reply_text(text[i:i+4096])
    else:
        await update.message.reply_text(text)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("Acceso denegado.")
        return
    msg = (
        "Jarvis en línea. A su servicio.\n\n"
        "Puede enviarme mensajes de texto o de voz.\n"
        "/reset — borrar contexto\n"
        "/status — estado del sistema\n"
        "/texto — respuesta solo en texto"
    )
    await update.message.reply_text(msg)


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    CEREBRO.reset_context()
    await update.message.reply_text("Contexto borrado. Listo para una nueva sesión.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    msgs = len(CEREBRO.history)
    voice_status = f"activa ({os.path.basename(VOICE_MODEL)})" if VOICE_ENABLED else "desactivada"
    await update.message.reply_text(
        f"Sistema activo.\n"
        f"Modelo: {CEREBRO._get_model().model_name}\n"
        f"Mensajes en contexto: {msgs}\n"
        f"Voz: {voice_status}"
    )


async def cmd_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return
    context.user_data["force_text"] = not context.user_data.get("force_text", False)
    estado = "desactivada" if context.user_data["force_text"] else "activada"
    await update.message.reply_text(f"Respuesta por voz {estado}.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        logger.warning(f"Acceso denegado user_id={update.effective_user.id}")
        await update.message.reply_text("No estás autorizado para usar este bot.")
        return

    user_text = update.message.text
    if not user_text:
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    response = CEREBRO.chat(user_text)

    force_text = context.user_data.get("force_text", False)
    await _send_reply(update, response, force_text=force_text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        await update.message.reply_text("No estás autorizado para usar este bot.")
        return

    await update.message.chat.send_action(ChatAction.RECORD_VOICE)

    with tempfile.TemporaryDirectory() as tmp:
        ogg_path = os.path.join(tmp, "voice.ogg")
        wav_path = os.path.join(tmp, "voice.wav")

        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(ogg_path)

        if not ogg_to_wav(ogg_path, wav_path):
            await update.message.reply_text("Error al procesar el audio.")
            return

        user_text = transcribe(wav_path)

    if not user_text:
        await update.message.reply_text("No pude entender el audio. ¿Puedes repetirlo?")
        return

    logger.info(f"Voz transcrita: {user_text}")
    await update.message.reply_text(f"_{user_text}_", parse_mode="Markdown")

    await update.message.chat.send_action(ChatAction.TYPING)
    response = CEREBRO.chat(user_text)

    force_text = context.user_data.get("force_text", False)
    await _send_reply(update, response, force_text=force_text)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error en update: {context.error}", exc_info=context.error)


def create_app(cerebro: Cerebro) -> Application:
    global CEREBRO
    CEREBRO = cerebro

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("texto", cmd_texto))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("Aplicación Telegram configurada")
    return app

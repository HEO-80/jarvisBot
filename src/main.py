import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import setup_logger, validate_config, INTERPRETER_AUTO_RUN
from agentes.cerebro_openclaw import Cerebro
from interfaces.telegram_bot import create_app

logger = setup_logger("jarvis")


def main():
    logger.info("=== Iniciando Jarvis Bot ===")

    errors = validate_config()
    if errors:
        for err in errors:
            logger.error(f"Config error: {err}")
        sys.exit(1)

    cerebro = Cerebro(auto_run=INTERPRETER_AUTO_RUN)
    app = create_app(cerebro)

    logger.info("Jarvis listo. Escuchando mensajes de Telegram...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        app.run_polling(drop_pending_updates=True)
    finally:
        loop.close()


if __name__ == "__main__":
    main()

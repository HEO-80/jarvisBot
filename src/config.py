import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

INTERPRETER_AUTO_RUN = os.getenv("INTERPRETER_AUTO_RUN", "false").lower() == "true"
INTERPRETER_SAFE_MODE = os.getenv("INTERPRETER_SAFE_MODE", "ask")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "")

SYSTEM_PROMPT = """Eres Jarvis, el asistente personal de Héctor Oviedo. Eres preciso, directo y eficiente.
Tienes acceso a herramientas para ejecutar código en el sistema Linux (Omarchy/Arch),
gestionar proyectos en Notion y revisar el correo de Gmail.

Cuando el usuario te pida ejecutar algo en el sistema, usa la herramienta execute_code.
Cuando pida guardar información en Notion, usa la herramienta notion_create_page.
Cuando pida revisar correos, usa la herramienta gmail_search.

Responde siempre en el mismo idioma que el usuario. Sé conciso pero completo.
Tu usuario es desarrollador y profesor, experto en Java/Spring Boot, React/Next.js, Solidity y Web3."""


def setup_logger(name: str = "jarvis") -> logging.Logger:
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    file_handler = logging.FileHandler(log_dir / "jarvis.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger


def validate_config() -> list[str]:
    errors = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN no configurado")
    if not TELEGRAM_ALLOWED_USER_ID:
        errors.append("TELEGRAM_ALLOWED_USER_ID no configurado")
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY no configurado")
    return errors

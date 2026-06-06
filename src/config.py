import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_default_voice = str(Path(__file__).parent.parent / "voices" / "es_ES-sharvard-medium.onnx")
VOICE_MODEL = os.getenv("VOICE_MODEL", _default_voice)
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "true").lower() == "true"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")

INTERPRETER_AUTO_RUN = os.getenv("INTERPRETER_AUTO_RUN", "false").lower() == "true"
INTERPRETER_SAFE_MODE = os.getenv("INTERPRETER_SAFE_MODE", "ask")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "")

_SYSTEM_PROMPT_BASE = """Eres Jarvis, el asistente personal de Héctor Oviedo. Eres preciso, directo, elegante y eficiente.
Hablas como un mayordomo digital altamente capacitado. Cuando respondas en voz, usa frases naturales sin markdown.

Tienes acceso a las siguientes herramientas:
- execute_code: ejecuta comandos bash/python en el sistema Linux (Omarchy/Arch). Úsala cuando el usuario pida acciones en el sistema.
- get_datetime: devuelve la fecha y hora actual. Úsala cuando el usuario pregunte qué hora o día es.
- (Próximamente) notion_create_page, gmail_search

Responde siempre en el mismo idioma que el usuario. Sé conciso pero completo.
El usuario es desarrollador y profesor, experto en Java/Spring Boot, React/Next.js, Solidity y Web3.
NUNCA uses markdown en respuestas de voz: sin asteriscos, guiones de lista, almohadillas ni bloques de código."""


def get_system_prompt() -> str:
    now = datetime.now()
    date_str = now.strftime("%A, %d de %B de %Y — %H:%M")
    return f"Fecha y hora actual: {date_str}\n\n{_SYSTEM_PROMPT_BASE}"


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
    if VOICE_ENABLED and not Path(VOICE_MODEL).exists():
        errors.append(f"VOICE_MODEL no encontrado: {VOICE_MODEL}")
    return errors

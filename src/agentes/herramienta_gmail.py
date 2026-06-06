"""
Tool de Gmail para Jarvis.
Lee, busca y redacta correos via Gmail API con OAuth2.
"""
import base64
import logging
import os
import pickle
from email.mime.text import MIMEText
from pathlib import Path

from config import GMAIL_CREDENTIALS_FILE

logger = logging.getLogger("jarvis.gmail")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]
TOKEN_FILE = str(Path(__file__).parent.parent.parent / "credentials" / "gmail_token.pickle")

_service = None


def _get_service():
    global _service
    if _service is not None:
        return _service

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"No se encontró {GMAIL_CREDENTIALS_FILE}. "
                    "Descarga las credenciales OAuth desde Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    _service = build("gmail", "v1", credentials=creds)
    logger.info("Gmail service autenticado")
    return _service


def search_emails(query: str, max_results: int = 5) -> str:
    """Busca emails con la query al estilo Gmail (ej: 'from:cliente@mail.com is:unread')."""
    try:
        service = _get_service()
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return f"No encontré emails para: '{query}'"

        summaries = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            snippet = detail.get("snippet", "")[:150]
            summaries.append(
                f"De: {headers.get('From', '?')}\n"
                f"Asunto: {headers.get('Subject', '?')}\n"
                f"Fecha: {headers.get('Date', '?')}\n"
                f"Resumen: {snippet}"
            )

        return f"Encontré {len(messages)} email(s):\n\n" + "\n\n---\n\n".join(summaries)

    except Exception as e:
        logger.error(f"Error Gmail search: {e}")
        return f"Error buscando emails: {str(e)}"


def get_unread_summary(max_results: int = 5) -> str:
    """Obtiene un resumen de los emails no leídos recientes."""
    return search_emails("is:unread in:inbox", max_results)


def create_draft(to: str, subject: str, body: str) -> str:
    """Crea un borrador de email."""
    try:
        service = _get_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()

        draft_id = draft.get("id", "")
        logger.info(f"Borrador creado: {draft_id}")
        return (
            f"Borrador creado correctamente.\n"
            f"Para: {to}\n"
            f"Asunto: {subject}\n"
            f"Puedes revisarlo y enviarlo desde Gmail."
        )

    except Exception as e:
        logger.error(f"Error Gmail draft: {e}")
        return f"Error creando borrador: {str(e)}"


# Definiciones de tools para Gemini
GMAIL_TOOL_DECLARATIONS = [
    {
        "name": "gmail_search",
        "description": (
            "Busca y lee emails en Gmail. Acepta queries tipo Gmail: "
            "'is:unread', 'from:alguien@email.com', 'subject:tema', etc. "
            "Úsala para leer correos, resumir bandeja de entrada, buscar conversaciones."
        ),
        "schema": {
            "query": ("str", "Query de búsqueda estilo Gmail"),
            "max_results": ("int", "Número máximo de resultados (default 5)"),
        }
    },
    {
        "name": "gmail_unread",
        "description": "Obtiene un resumen de los emails no leídos en la bandeja de entrada.",
        "schema": {
            "max_results": ("int", "Número máximo de emails (default 5)"),
        }
    },
    {
        "name": "gmail_draft",
        "description": "Crea un borrador de email en Gmail. NO envía el email, solo crea el borrador para que el usuario lo revise.",
        "schema": {
            "to": ("str", "Dirección de email del destinatario"),
            "subject": ("str", "Asunto del email"),
            "body": ("str", "Cuerpo del email en texto plano"),
        }
    },
]

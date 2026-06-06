"""
Tool de Notion para Jarvis.
Permite crear páginas, buscar en bases de datos y listar tareas.
"""
import logging
from datetime import datetime

from notion_client import Client

from config import NOTION_API_KEY

logger = logging.getLogger("jarvis.notion")

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(auth=NOTION_API_KEY)
        logger.info("Notion client inicializado")
    return _client


def search_pages(query: str, limit: int = 5) -> str:
    try:
        client = _get_client()
        results = client.search(query=query, page_size=limit)
        if not results["results"]:
            return f"No encontré páginas en Notion relacionadas con '{query}'."

        lines = [f"Páginas encontradas para '{query}':"]
        for item in results["results"]:
            obj_type = item["object"]
            if obj_type == "page":
                title = _get_title(item)
                url = item.get("url", "")
                lines.append(f"- {title}: {url}")
            elif obj_type == "database":
                title = _get_db_title(item)
                lines.append(f"- [BD] {title}")
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error Notion search: {e}")
        return f"Error buscando en Notion: {str(e)}"


def create_page(parent_title: str, page_title: str, content: str) -> str:
    """Crea una página en Notion. Busca el parent por título o usa el workspace root."""
    try:
        client = _get_client()

        parent_id = None
        if parent_title:
            results = client.search(query=parent_title, page_size=5)
            for item in results["results"]:
                if item["object"] in ("page", "database"):
                    parent_id = item["id"]
                    break

        if parent_id:
            parent = {"page_id": parent_id}
        else:
            # Si no encuentra parent, crea en el workspace (requiere que el bot tenga acceso)
            return (
                f"No encontré la página o base de datos '{parent_title}' en Notion. "
                "Asegúrate de que la integración Jarvis tiene acceso a esa página."
            )

        blocks = _markdown_to_blocks(content)

        new_page = client.pages.create(
            parent=parent,
            properties={
                "title": {"title": [{"text": {"content": page_title}}]}
            },
            children=blocks,
        )

        url = new_page.get("url", "")
        logger.info(f"Página creada: {page_title} — {url}")
        return f"Página '{page_title}' creada correctamente en Notion.\nURL: {url}"

    except Exception as e:
        logger.error(f"Error Notion create_page: {e}")
        return f"Error creando página en Notion: {str(e)}"


def query_database(database_title: str, filter_text: str = "") -> str:
    """Consulta una base de datos de Notion por título."""
    try:
        client = _get_client()

        results = client.search(query=database_title, filter={"property": "object", "value": "database"})
        if not results["results"]:
            return f"No encontré la base de datos '{database_title}' en Notion."

        db_id = results["results"][0]["id"]
        db_name = _get_db_title(results["results"][0])

        query_result = client.databases.query(database_id=db_id, page_size=10)
        pages = query_result.get("results", [])

        if not pages:
            return f"La base de datos '{db_name}' está vacía."

        lines = [f"Entradas en '{db_name}':"]
        for page in pages:
            title = _get_title(page)
            url = page.get("url", "")
            lines.append(f"- {title}: {url}")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error Notion query_database: {e}")
        return f"Error consultando base de datos: {str(e)}"


def _get_title(page: dict) -> str:
    props = page.get("properties", {})
    for key in ("Name", "Nombre", "title", "Title"):
        if key in props:
            prop = props[key]
            if prop.get("type") == "title":
                parts = prop.get("title", [])
                return "".join(p.get("plain_text", "") for p in parts) or "(sin título)"
    return "(sin título)"


def _get_db_title(db: dict) -> str:
    title_parts = db.get("title", [])
    return "".join(p.get("plain_text", "") for p in title_parts) or "(sin nombre)"


def _markdown_to_blocks(text: str) -> list:
    """Convierte texto plano/markdown básico a bloques Notion."""
    blocks = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
        elif line.startswith("- ") or line.startswith("• "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}})
    return blocks or [{"object": "block", "type": "paragraph",
                       "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}]


# Definiciones de tools para Gemini
NOTION_TOOL_DECLARATIONS = [
    {
        "name": "notion_search",
        "description": "Busca páginas o bases de datos en Notion por texto. Úsala para encontrar información o verificar si existe algo.",
        "schema": {
            "query": ("str", "Texto a buscar en Notion"),
        }
    },
    {
        "name": "notion_create_page",
        "description": "Crea una nueva página en Notion dentro de una página o base de datos existente.",
        "schema": {
            "parent_title": ("str", "Título de la página o base de datos donde crear la nueva página"),
            "page_title": ("str", "Título de la nueva página"),
            "content": ("str", "Contenido de la página (texto plano o markdown básico)"),
        }
    },
    {
        "name": "notion_query_database",
        "description": "Lista las entradas de una base de datos de Notion. Útil para ver tareas, proyectos, etc.",
        "schema": {
            "database_title": ("str", "Nombre de la base de datos a consultar"),
        }
    },
]

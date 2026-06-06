"""
Cerebro de Jarvis: orquestador basado en Gemini con function calling.
Gestiona el contexto de conversación, razona sobre las peticiones
y decide qué herramientas invocar.
"""
import logging
from datetime import datetime

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, NOTION_API_KEY, GMAIL_CREDENTIALS_FILE, get_system_prompt
from agentes.herramienta_interpreter import InterpreterTool

logger = logging.getLogger("jarvis.cerebro")

MAX_HISTORY = 20


def _schema(properties: dict[str, tuple], required: list[str] | None = None) -> genai.protos.Schema:
    props = {}
    for name, (typ, desc) in properties.items():
        proto_type = genai.protos.Type.STRING if typ == "str" else genai.protos.Type.INTEGER
        props[name] = genai.protos.Schema(type=proto_type, description=desc)
    return genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties=props,
        required=required or list(properties.keys()),
    )


def _decl(name: str, description: str, properties: dict = None, required: list = None) -> genai.protos.FunctionDeclaration:
    params = _schema(properties, required) if properties else genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={})
    return genai.protos.FunctionDeclaration(name=name, description=description, parameters=params)


def _build_tools() -> list:
    declarations = [
        _decl("execute_code",
              "Ejecuta comandos bash o código Python en el sistema Linux. Úsala para acciones en el sistema, repos, archivos.",
              {"instruction": ("str", "Instrucción clara en lenguaje natural")}),
        _decl("get_datetime",
              "Devuelve la fecha y hora actual. Úsala cuando el usuario pregunte qué día o qué hora es."),
    ]

    if NOTION_API_KEY:
        declarations += [
            _decl("notion_search",
                  "Busca páginas o bases de datos en Notion por texto.",
                  {"query": ("str", "Texto a buscar")}),
            _decl("notion_create_page",
                  "Crea una nueva página en Notion dentro de una página o base de datos existente.",
                  {"parent_title": ("str", "Nombre de la página/BD padre"),
                   "page_title": ("str", "Título de la nueva página"),
                   "content": ("str", "Contenido en texto o markdown básico")}),
            _decl("notion_query_database",
                  "Lista las entradas de una base de datos de Notion (tareas, proyectos, etc).",
                  {"database_title": ("str", "Nombre de la base de datos")}),
        ]

    if GMAIL_CREDENTIALS_FILE and GMAIL_CREDENTIALS_FILE != "credentials/gmail_credentials.json":
        from pathlib import Path
        if Path(GMAIL_CREDENTIALS_FILE).exists():
            declarations += [
                _decl("gmail_search",
                      "Busca y lee emails en Gmail. Usa queries tipo Gmail: 'is:unread', 'from:x@y.com', 'subject:Z'.",
                      {"query": ("str", "Query de búsqueda"), "max_results": ("int", "Máximo resultados")},
                      required=["query"]),
                _decl("gmail_unread",
                      "Resumen de emails no leídos en la bandeja de entrada.",
                      {"max_results": ("int", "Máximo resultados")},
                      required=[]),
                _decl("gmail_draft",
                      "Crea un BORRADOR de email en Gmail (no lo envía, el usuario lo revisa y envía).",
                      {"to": ("str", "Email del destinatario"),
                       "subject": ("str", "Asunto"),
                       "body": ("str", "Cuerpo del email")}),
            ]

    return [genai.protos.Tool(function_declarations=declarations)]


class Cerebro:
    def __init__(self, auto_run: bool = False):
        genai.configure(api_key=GEMINI_API_KEY)

        self.tools = _build_tools()
        self.interpreter = InterpreterTool(auto_run=auto_run)
        self.history: list[dict] = []

        enabled = [d.name for d in self.tools[0].function_declarations]
        logger.info(f"Cerebro iniciado. Modelo={GEMINI_MODEL}. Tools: {enabled}")

    def _get_model(self) -> genai.GenerativeModel:
        return genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=get_system_prompt(),
            tools=self.tools,
        )

    def _trim_history(self):
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    def chat(self, user_message: str) -> str:
        logger.info(f"Usuario: {user_message[:100]}")
        self._trim_history()
        self.history.append({"role": "user", "parts": [user_message]})

        try:
            model = self._get_model()
            chat_session = model.start_chat(history=self.history[:-1])
            response = chat_session.send_message(user_message)

            while response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]

                if hasattr(part, "function_call") and part.function_call.name:
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)
                    logger.info(f"Tool call: {fn_name}({list(fn_args.keys())})")

                    tool_result = self._dispatch_tool(fn_name, fn_args)
                    self.history.append({"role": "model", "parts": [part]})

                    response = chat_session.send_message(
                        genai.protos.Content(
                            role="function",
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fn_name,
                                    response={"result": tool_result},
                                )
                            )]
                        )
                    )
                else:
                    break

            final_text = response.text
            self.history.append({"role": "model", "parts": [final_text]})
            logger.info(f"Respuesta: {final_text[:100]}")
            return final_text

        except Exception as e:
            logger.error(f"Error en Cerebro.chat: {e}", exc_info=True)
            return f"Error interno: {str(e)}"

    def _dispatch_tool(self, name: str, args: dict) -> str:
        if name == "execute_code":
            return self.interpreter.execute(args.get("instruction", ""))

        if name == "get_datetime":
            return datetime.now().strftime("%A, %d de %B de %Y, %H:%M:%S")

        if name.startswith("notion_"):
            from agentes.herramienta_notion import search_pages, create_page, query_database
            if name == "notion_search":
                return search_pages(args.get("query", ""))
            if name == "notion_create_page":
                return create_page(args.get("parent_title", ""), args.get("page_title", ""), args.get("content", ""))
            if name == "notion_query_database":
                return query_database(args.get("database_title", ""))

        if name.startswith("gmail_"):
            from agentes.herramienta_gmail import search_emails, get_unread_summary, create_draft
            if name == "gmail_search":
                return search_emails(args.get("query", ""), int(args.get("max_results", 5)))
            if name == "gmail_unread":
                return get_unread_summary(int(args.get("max_results", 5)))
            if name == "gmail_draft":
                return create_draft(args.get("to", ""), args.get("subject", ""), args.get("body", ""))

        logger.warning(f"Tool desconocida: {name}")
        return f"Tool '{name}' no disponible."

    def reset_context(self):
        self.history.clear()
        self.interpreter.reset()
        logger.info("Contexto reseteado")

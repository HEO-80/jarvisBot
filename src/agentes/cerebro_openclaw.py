"""
Cerebro de Jarvis: orquestador basado en Gemini con function calling.
Gestiona el contexto de conversación, razona sobre las peticiones
y decide qué herramientas invocar.
"""
import logging
from datetime import datetime

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, get_system_prompt
from agentes.herramienta_interpreter import InterpreterTool

logger = logging.getLogger("jarvis.cerebro")

MAX_HISTORY = 20


def _build_tools() -> list:
    execute_code = genai.protos.FunctionDeclaration(
        name="execute_code",
        description=(
            "Ejecuta comandos o código en el sistema Linux del usuario. "
            "Puede crear/modificar archivos, ejecutar scripts Python/Bash, "
            "instalar paquetes, clonar repos, analizar código, etc."
        ),
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={
                "instruction": genai.protos.Schema(
                    type=genai.protos.Type.STRING,
                    description="Instrucción clara en lenguaje natural de lo que ejecutar",
                )
            },
            required=["instruction"],
        ),
    )
    get_datetime = genai.protos.FunctionDeclaration(
        name="get_datetime",
        description="Devuelve la fecha y hora actual del sistema. Úsala cuando el usuario pregunte qué hora es, qué día es hoy, etc.",
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties={},
        ),
    )
    return [genai.protos.Tool(function_declarations=[execute_code, get_datetime])]


class Cerebro:
    def __init__(self, auto_run: bool = False):
        genai.configure(api_key=GEMINI_API_KEY)

        self.tools = _build_tools()
        self._auto_run = auto_run
        self.interpreter = InterpreterTool(auto_run=auto_run)
        self.history: list[dict] = []
        logger.info(f"Cerebro iniciado con modelo {GEMINI_MODEL}")

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

            # Loop de function calling
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
            now = datetime.now()
            return now.strftime("%A, %d de %B de %Y, %H:%M:%S")
        logger.warning(f"Tool desconocida: {name}")
        return f"Tool '{name}' no disponible."

    def reset_context(self):
        self.history.clear()
        self.interpreter.reset()
        logger.info("Contexto reseteado")

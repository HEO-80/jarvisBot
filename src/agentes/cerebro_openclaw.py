"""
Cerebro de Jarvis: orquestador basado en Gemini con function calling.
Gestiona el contexto de conversación, razona sobre las peticiones
y decide qué herramientas invocar.
"""
import json
import logging
from typing import Any

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT
from agentes.herramienta_interpreter import InterpreterTool, INTERPRETER_TOOL_DEFINITION

logger = logging.getLogger("jarvis.cerebro")

MAX_HISTORY = 20  # mensajes en contexto antes de resumir


class Cerebro:
    def __init__(self, auto_run: bool = False):
        genai.configure(api_key=GEMINI_API_KEY)

        self.tools = [
            genai.protos.Tool(
                function_declarations=[
                    genai.protos.FunctionDeclaration(**INTERPRETER_TOOL_DEFINITION)
                ]
            )
        ]

        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            tools=self.tools,
        )

        self.interpreter = InterpreterTool(auto_run=auto_run)
        self.history: list[dict] = []
        logger.info(f"Cerebro iniciado con modelo {GEMINI_MODEL}")

    def _trim_history(self):
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    def chat(self, user_message: str) -> str:
        """
        Procesa un mensaje del usuario y devuelve la respuesta de Jarvis.
        Gestiona el loop de function calling automáticamente.
        """
        logger.info(f"Usuario: {user_message[:100]}")
        self._trim_history()

        self.history.append({"role": "user", "parts": [user_message]})

        try:
            chat_session = self.model.start_chat(history=self.history[:-1])
            response = chat_session.send_message(user_message)

            # Loop de function calling
            while response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]

                # Si hay una llamada a función
                if hasattr(part, "function_call") and part.function_call.name:
                    fn_name = part.function_call.name
                    fn_args = dict(part.function_call.args)
                    logger.info(f"Tool call: {fn_name}({list(fn_args.keys())})")

                    tool_result = self._dispatch_tool(fn_name, fn_args)

                    # Añadir al historial la respuesta del modelo con la tool call
                    self.history.append({
                        "role": "model",
                        "parts": [part]
                    })

                    # Enviar resultado de vuelta al modelo
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
        # Más tools se añaden aquí en Fase 4 (Notion, Gmail)
        logger.warning(f"Tool desconocida: {name}")
        return f"Tool '{name}' no disponible."

    def reset_context(self):
        self.history.clear()
        self.interpreter.reset()
        logger.info("Contexto reseteado")

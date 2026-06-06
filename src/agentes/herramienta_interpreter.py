"""
Open Interpreter como herramienta ejecutora.
Recibe instrucciones en lenguaje natural y ejecuta código/comandos en el sistema.
"""
import logging
from typing import Any

logger = logging.getLogger("jarvis.interpreter")


class InterpreterTool:
    """Wrapper de Open Interpreter para uso como tool de Gemini."""

    def __init__(self, auto_run: bool = False, safe_mode: str = "ask"):
        self.auto_run = auto_run
        self.safe_mode = safe_mode
        self._interpreter = None

    def _get_interpreter(self):
        if self._interpreter is None:
            try:
                from interpreter import interpreter
                interpreter.auto_run = self.auto_run
                interpreter.llm.model = "gemini/gemini-2.5-flash"
                interpreter.llm.supports_functions = True
                self._interpreter = interpreter
                logger.info("Open Interpreter inicializado")
            except ImportError:
                logger.error("open-interpreter no instalado. Ejecuta: pip install open-interpreter")
                raise
        return self._interpreter

    def execute(self, instruction: str) -> str:
        """
        Ejecuta una instrucción en lenguaje natural.
        Devuelve el output completo como string.
        """
        logger.info(f"Ejecutando: {instruction[:100]}...")
        interp = self._get_interpreter()

        output_parts = []
        try:
            for chunk in interp.chat(instruction, display=False, stream=True):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "message" and chunk.get("content"):
                        output_parts.append(str(chunk["content"]))
                    elif chunk.get("type") == "code" and chunk.get("content"):
                        output_parts.append(f"```\n{chunk['content']}\n```")
                    elif chunk.get("type") == "console" and chunk.get("content"):
                        output_parts.append(f"[output] {chunk['content']}")

            result = "\n".join(output_parts).strip()
            logger.debug(f"Resultado: {result[:200]}")
            return result or "Ejecución completada sin output."

        except Exception as e:
            logger.error(f"Error en InterpreterTool: {e}")
            return f"Error al ejecutar: {str(e)}"

    def reset(self):
        if self._interpreter:
            self._interpreter.messages = []
            logger.debug("Contexto de interpreter reseteado")


# Definición de la tool para Gemini function calling
INTERPRETER_TOOL_DEFINITION = {
    "name": "execute_code",
    "description": (
        "Ejecuta comandos o código en el sistema Linux del usuario. "
        "Puede crear/modificar archivos, ejecutar scripts Python/Bash, "
        "instalar paquetes, clonar repos, analizar código, etc. "
        "Usa esto cuando el usuario pida realizar acciones en su sistema."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": "Instrucción clara en lenguaje natural de lo que ejecutar",
            }
        },
        "required": ["instruction"],
    },
}

"""
Ejecutor de código y comandos del sistema.
Implementa la tool execute_code de Jarvis sin depender de open-interpreter.
Soporta bash y Python con timeout y límite de output.
"""
import logging
import subprocess
import tempfile
import os
import re
from pathlib import Path

logger = logging.getLogger("jarvis.interpreter")

TIMEOUT = 30
MAX_OUTPUT = 4000
WORK_DIR = str(Path.home())


class InterpreterTool:
    def __init__(self, auto_run: bool = False, safe_mode: str = "ask"):
        self.auto_run = auto_run
        self.safe_mode = safe_mode

    def execute(self, instruction: str) -> str:
        logger.info(f"Ejecutando instrucción: {instruction[:120]}")

        # Detectar si la instrucción contiene código explícito o es lenguaje natural
        lang, code = self._extract_code(instruction)

        if lang and code:
            return self._run_code(lang, code)
        else:
            # Ejecutar directamente como bash si suena a comando
            return self._run_bash(instruction)

    def _extract_code(self, text: str) -> tuple[str, str]:
        # Busca bloques ```bash, ```python, ```sh
        match = re.search(r"```(bash|sh|python|py)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
        if match:
            lang = (match.group(1) or "bash").lower()
            lang = "python" if lang == "py" else lang
            lang = "bash" if lang == "sh" else lang
            return lang, match.group(2).strip()
        return "", ""

    def _run_bash(self, command: str) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                cwd=WORK_DIR,
                env={**os.environ, "TERM": "dumb"},
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            output = output.strip()
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + f"\n...[truncado a {MAX_OUTPUT} chars]"
            return output or "(sin output)"

        except subprocess.TimeoutExpired:
            return f"Timeout: el comando superó {TIMEOUT}s."
        except Exception as e:
            logger.error(f"Error ejecutando bash: {e}")
            return f"Error: {str(e)}"

    def _run_code(self, lang: str, code: str) -> str:
        if lang == "python":
            return self._run_python(code)
        return self._run_bash(code)

    def _run_python(self, code: str) -> str:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name

            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                cwd=WORK_DIR,
            )
            os.unlink(tmp_path)

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"

            output = output.strip()
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + f"\n...[truncado]"
            return output or "(sin output)"

        except subprocess.TimeoutExpired:
            return f"Timeout: el script superó {TIMEOUT}s."
        except Exception as e:
            logger.error(f"Error ejecutando Python: {e}")
            return f"Error: {str(e)}"

    def reset(self):
        pass  # stateless, nada que resetear

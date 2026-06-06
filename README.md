# jarvisBot

Asistente personal tipo "Jarvis" que corre de forma nativa en Omarchy (Arch Linux).
Controlado por Telegram, con razonamiento via Gemini y capacidad de ejecutar acciones reales en el sistema.

## Arquitectura

| Capa | Componente | Rol |
|------|------------|-----|
| Cerebro | Gemini 2.5 Flash + function calling | Razonamiento, planificación, contexto |
| Manos | Open Interpreter | Ejecuta código/comandos en el sistema |
| Voz entrada | faster-whisper | Transcribe mensajes de voz |
| Voz salida | piper-tts | Respuestas en audio (voz masculina elegante) |
| Interfaz | Telegram (python-telegram-bot) | Canal de comunicación |
| Integraciones | Notion, Gmail | Gestión de proyectos y correo |

## Estructura

```
jarvisBot/
├── src/
│   ├── main.py                          # Entry point
│   ├── config.py                        # Config + logger
│   ├── agentes/
│   │   ├── cerebro_openclaw.py          # Gemini orquestador + tools
│   │   └── herramienta_interpreter.py  # Open Interpreter tool
│   ├── interfaces/
│   │   └── telegram_bot.py             # Bot Telegram (texto + voz)
│   └── utils/
│       └── voice.py                    # TTS (piper) + STT (whisper)
├── voices/                             # Modelos de voz piper
├── .env                                # Credenciales (no en git)
└── requirements.txt
```

## Comandos Telegram

| Comando | Acción |
|---------|--------|
| `/start` | Activa Jarvis |
| `/reset` | Borra el contexto de conversación |
| `/status` | Estado del sistema y modelo activo |
| Texto | Responde con texto y voz |
| Audio | Transcribe con whisper, responde con voz |

---

## Fases de desarrollo

### ✅ Fase 1 — Configuración Base
- Estructura de proyecto modular (`src/`, `agentes/`, `interfaces/`, `utils/`)
- Logger centralizado con rotación a archivo
- Config via `.env` con validación al arranque
- Conexión a Gemini 2.5 Flash verificada
- Servicio systemd `jarvis-bot.service` (autostart en boot)
- Bot Telegram básico con autorización por user_id

### ✅ Fase 2 — Cerebro, Manos y Voz
- Gemini con function calling como orquestador
- Tool `execute_code` via Open Interpreter (ejecuta bash/python en el sistema)
- Tool `get_datetime` — Jarvis sabe la fecha y hora actual
- Respuestas en voz con piper-tts (voz masculina elegante `es_ES-sharvard-medium`)
- Mensajes de voz entrantes transcritos con faster-whisper
- Sistema de tool dispatch extensible para nuevas integraciones
- Prompt del sistema dinámico con fecha/hora inyectada

### 🔜 Fase 3 — Telegram avanzado
- Soporte de imágenes y documentos
- Respuesta a mensajes de grupos (si se decide)
- Modo solo-texto configurable

### 🔜 Fase 4 — Integraciones Externas
- **Notion**: crear páginas, leer bases de datos, anotar tareas
- **Gmail**: leer y resumir correos, redactar borradores
- Tool `notion_create_page`, `notion_search`, `gmail_search`, `gmail_draft`

### 🔜 Fase 5 — Despliegue Avanzado
- Configuración para replicar en Beelink u otro equipo
- Variables de entorno por máquina
- Script de instalación automatizado (`install.sh`)
- Documentación de clonado del bot para otros proyectos

---

## Setup rápido (nuevo equipo)

```bash
git clone https://github.com/HEO-80/jarvisBot.git
cd jarvisBot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Descarga voz: es_ES-sharvard-medium.onnx → voices/
# Copia y rellena .env
cp .env.example .env
systemctl --user enable --now jarvis-bot.service
```

## Dependencias sistema (Arch/Omarchy)

```bash
yay -S piper-tts ffmpeg
```

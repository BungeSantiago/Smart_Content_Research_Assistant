
# Smart Research Assistant

Sistema multi-agente basado en consola para investigación de temas con
validación humana y optimización de costos de IA.

## Stack

- **Python 3.12+**
- **LangGraph** — orquestación de agentes con estado
- **Pydantic** — validación de datos
- **Google Gemini API** — modelos de lenguaje
- **Rich** — UI de consola

## Setup

1. Cloná el repo y entrá a la carpeta:
```bash
   git clone <repo-url>
   cd smart-research-assistant
```

2. Creá un virtual environment con Python 3.12:
```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
```

3. Instalá las dependencias:
```bash
   pip install -r requirements.txt
```

4. Configurá tus API keys:
```bash
   cp .env.example .env
```
   Conseguí una API key gratis en https://aistudio.google.com/apikey
   y pegala en `.env`.

5. Ejecutá:
```bash
   python main.py
```

## Arquitectura

(En construcción)

## Licencia

MIT
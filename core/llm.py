"""
Factory de modelos LLM.

Centraliza la creación de modelos para que los agentes solo declaren
qué nivel de modelo necesitan, sin preocuparse por la configuración.

Esto también prepara el terreno para el routing por costo:
distintos agentes usan distintos tiers de modelos.
"""
import os
from enum import Enum
from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel


class ModelTier(str, Enum):
    """Tiers de modelos según complejidad de la tarea."""
    SIMPLE = "simple"    # Tareas rápidas, baratas (ej. clasificar, listar)
    COMPLEX = "complex"  # Tareas analíticas profundas (ej. síntesis, redacción)


def get_llm(tier: ModelTier, temperature: float = 0.3) -> BaseChatModel:
    """
    Devuelve una instancia de LLM según el tier requerido.

    El tier se resuelve a un modelo concreto vía variables de entorno:
      - SIMPLE  → MODEL_SIMPLE  (default: llama-3.1-8b-instant)
      - COMPLEX → MODEL_COMPLEX (default: llama-3.3-70b-versatile)

    Args:
        tier: nivel de complejidad requerido.
        temperature: aleatoriedad del output (0.0 = determinista, 1.0 = creativo).
    """
    if tier == ModelTier.SIMPLE:
        model_name = os.getenv("MODEL_SIMPLE", "llama-3.1-8b-instant")
    elif tier == ModelTier.COMPLEX:
        model_name = os.getenv("MODEL_COMPLEX", "llama-3.3-70b-versatile")
    else:
        raise ValueError(f"Tier desconocido: {tier}")

    return ChatGroq(
        model=model_name,
        temperature=temperature,
    )


def load_prompt(name: str) -> str:
    """
    Carga un prompt desde la carpeta prompts/.

    Args:
        name: nombre del archivo sin extensión (ej. "investigator_system").
    """
    prompts_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
    path = os.path.join(prompts_dir, f"{name}.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
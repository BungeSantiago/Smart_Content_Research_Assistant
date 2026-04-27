"""
Tracking de uso y costos de llamadas a LLMs.

Provee un helper que envuelve invocaciones a modelos y captura métricas
de uso (tokens, costo) automáticamente.

Como workaround, estimamos los tokens por longitud del texto 
(4 caracteres por token es la regla del pulgar estándar). 
Es una aproximación, no exacta, pero suficiente para reportar.
"""
from typing import Any
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from core.state import UsageEntry
from core.pricing import estimate_cost


def invoke_with_tracking(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    agent_name: str,
) -> tuple[Any, UsageEntry]:
    """
    Invoca un LLM y devuelve la respuesta + un registro de uso.

    Args:
        llm: el modelo (cualquier BaseChatModel de LangChain).
        messages: la lista de mensajes a enviar.
        agent_name: nombre del agente que hace la llamada (para el log).

    Returns:
        (response, usage_entry): la respuesta del modelo y el registro de uso.
    """
    response = llm.invoke(messages)

    # Extraer metadata del modelo (cómo se llama internamente)
    model_name = _extract_model_name(llm)

    # Extraer tokens. LangChain los pone en response.usage_metadata
    # (estándar nuevo) o en response.response_metadata (legacy).
    input_tokens, output_tokens = _extract_token_usage(response)

    cost = estimate_cost(model_name, input_tokens, output_tokens)

    usage = UsageEntry(
        agent=agent_name,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
    )

    return response, usage


def invoke_structured_with_tracking(
    structured_llm: Any,
    base_llm: BaseChatModel,
    messages: list[BaseMessage],
    agent_name: str,
) -> tuple[Any, UsageEntry]:
    """
    Variante para LLMs con structured output.

    Estos no exponen usage_metadata directamente porque el wrapper de
    structured output devuelve el modelo Pydantic, no el AIMessage.
    Para capturar tokens, se invoca el LLM base en paralelo o se usa
    el callback de LangChain. Acá usamos una aproximación: invocar
    structured_llm normalmente y estimar tokens del prompt + output.
    """
    response = structured_llm.invoke(messages)

    model_name = _extract_model_name(base_llm)

    # Para structured output, una aproximación razonable:
    # - input_tokens: estimado por longitud del prompt
    # - output_tokens: estimado por longitud del JSON serializado
    input_tokens = _estimate_tokens_from_messages(messages)
    output_tokens = _estimate_tokens_from_text(str(response))

    cost = estimate_cost(model_name, input_tokens, output_tokens)

    usage = UsageEntry(
        agent=agent_name,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=cost,
    )

    return response, usage


def _extract_model_name(llm: BaseChatModel) -> str:
    """Extrae el nombre del modelo de una instancia de LLM."""
    # ChatGroq lo guarda en .model_name o .model
    for attr in ("model_name", "model"):
        if hasattr(llm, attr):
            return str(getattr(llm, attr))
    return "unknown"


def _extract_token_usage(response: Any) -> tuple[int, int]:
    """
    Extrae (input_tokens, output_tokens) de la respuesta del LLM.

    LangChain expone esto en distintos lugares según el provider y la versión.
    """
    # Forma estándar nueva: response.usage_metadata
    usage = getattr(response, "usage_metadata", None)
    if usage:
        return (
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )

    # Fallback: response.response_metadata.token_usage (Groq, OpenAI)
    metadata = getattr(response, "response_metadata", {}) or {}
    token_usage = metadata.get("token_usage", {}) or {}
    return (
        token_usage.get("prompt_tokens", 0),
        token_usage.get("completion_tokens", 0),
    )


def _estimate_tokens_from_messages(messages: list[BaseMessage]) -> int:
    """Estimación grosera: ~4 caracteres por token."""
    total_chars = sum(len(str(m.content)) for m in messages)
    return total_chars // 4


def _estimate_tokens_from_text(text: str) -> int:
    """Estimación grosera: ~4 caracteres por token."""
    return len(text) // 4
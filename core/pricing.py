from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """Precio de un modelo, en USD por millón de tokens."""
    input_per_million: float
    output_per_million: float


# Catálogo de modelos conocidos. Si usás un modelo no listado, el costo
# se reportará como 0 (con un warning), pero el sistema sigue funcionando.
MODEL_PRICING: dict[str, ModelPricing] = {
    # Groq - Llama
    "llama-3.1-8b-instant": ModelPricing(
        input_per_million=0.05,
        output_per_million=0.08,
    ),
    "llama-3.3-70b-versatile": ModelPricing(
        input_per_million=0.59,
        output_per_million=0.79,
    ),
    # Agregá acá otros modelos si los usás.
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calcula el costo estimado de una llamada en USD.

    Args:
        model: nombre exacto del modelo (debe coincidir con MODEL_PRICING).
        input_tokens: tokens enviados al modelo.
        output_tokens: tokens generados por el modelo.

    Returns:
        Costo en USD. 0.0 si el modelo no está en el catálogo.
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0

    cost_input = (input_tokens / 1_000_000) * pricing.input_per_million
    cost_output = (output_tokens / 1_000_000) * pricing.output_per_million
    return cost_input + cost_output
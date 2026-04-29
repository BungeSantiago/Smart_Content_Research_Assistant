"""
Classifier de complejidad para routing dinámico de modelos.

Cada agente tiene un tier baseline, pero puede ajustarse dinámicamente
según la complejidad real del trabajo. Implementa la idea del cost
optimization del challenge: usar el modelo caro solo cuando se justifica.

Las heurísticas son simples a propósito: basadas en señales objetivas
del input. Una alternativa más sofisticada sería usar un modelo chico
para clasificar, pero esa metaclasificación tiene su propio costo y
latencia, lo que rompería el objetivo de optimización.
"""
from dataclasses import dataclass

from core.llm import ModelTier


@dataclass(frozen=True)
class RoutingDecision:
    """Resultado de la clasificación: tier elegido y motivo."""
    tier: ModelTier
    reason: str


def classify_investigator(topic: str) -> RoutingDecision:
    """Decide el tier para el Investigator según la complejidad del topic."""
    word_count = len(topic.split())

    if word_count <= 6:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=f"Topic corto ({word_count} palabras): SIMPLE alcanza.",
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=f"Topic extenso ({word_count} palabras): COMPLEX para mejor comprensión.",
    )

def classify_curator(
    num_approved_subtopics: int,
    avg_rationale_length: int,
    total_sources: int = 0,
    avg_snippet_length: int = 0,
) -> RoutingDecision:
    """
    Decide el tier para el Curator según la carga de trabajo.

    Considera tanto los subtemas aprobados como las fuentes web asociadas,
    porque ambos contribuyen al volumen de material a sintetizar.
    """
    if num_approved_subtopics == 0:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason="Sin subtemas aprobados: tier mínimo.",
        )

    total_material_chars = (
        num_approved_subtopics * avg_rationale_length
        + total_sources * avg_snippet_length
    )

    # Caso claramente liviano: 1 subtema, pocas fuentes, material acotado
    if (
        num_approved_subtopics == 1
        and total_sources <= 3
        and total_material_chars < 1500
    ):
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=(
                f"Carga liviana (1 subtema, {total_sources} fuentes, "
                f"~{total_material_chars} chars de material): SIMPLE alcanza."
            ),
        )

    # Caso moderado: hasta 2 subtemas con material acotado
    if num_approved_subtopics <= 2 and total_material_chars < 1200:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=(
                f"Carga moderada ({num_approved_subtopics} subtemas, "
                f"{total_sources} fuentes, ~{total_material_chars} chars): SIMPLE alcanza."
            ),
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=(
            f"Carga significativa ({num_approved_subtopics} subtemas, "
            f"{total_sources} fuentes, ~{total_material_chars} chars de material): "
            f"COMPLEX para síntesis profunda."
        ),
    )

def classify_reporter(curated_content_length: int) -> RoutingDecision:
    """Decide el tier para el Reporter según el contenido a transformar."""
    if curated_content_length < 500:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=(
                f"Contenido curado muy corto ({curated_content_length} chars): "
                f"SIMPLE alcanza para formatear."
            ),
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=(
            f"Contenido curado extenso ({curated_content_length} chars): "
            f"COMPLEX para generar reporte coherente."
        ),
    )
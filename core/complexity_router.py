
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
            reason=f"Short topic ({word_count} words): SIMPLE is sufficient.",
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=f"Long topic ({word_count} words): COMPLEX is needed for better understanding.",
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
            reason="No approved subtopics: minimum tier.",
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
                f"Light workload (1 subtopic, {total_sources} sources, "
                f"~{total_material_chars} chars of content): SIMPLE is sufficient."
            ),
        )

    # Caso moderado: hasta 2 subtemas con material acotado
    if num_approved_subtopics <= 2 and total_material_chars < 1200:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=(
                f"Moderate workload ({num_approved_subtopics} subtopics, "
                f"{total_sources} sources, ~{total_material_chars} chars): SIMPLE is sufficient."
            ),
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=(
            f"Significant workload ({num_approved_subtopics} subtopics, "
            f"{total_sources} sources, ~{total_material_chars} chars of content): "
            f"COMPLEX for deep synthesis."
        ),
    )

def classify_reporter(curated_content_length: int) -> RoutingDecision:
    """Decide el tier para el Reporter según el contenido a transformar."""
    if curated_content_length < 500:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=(
                f"Curated content very short ({curated_content_length} chars): "
                f"SIMPLE is sufficient for formatting."
            ),
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=(
            f"Curated content long ({curated_content_length} chars): "
            f"COMPLEX for generating a coherent report."
        ),
    )
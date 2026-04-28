"""
Classifier de complejidad para routing dinámico de modelos.

Cada agente tiene una baseline (tier por defecto que usaría siempre), pero
puede ser ajustado dinámicamente según la complejidad real del trabajo.

Esto implementa la idea del cost optimization del challenge: usar el modelo
caro solo cuando la tarea lo justifica.

Las heurísticas son simples a propósito: basadas en señales objetivas del input
(cantidad de subtemas, longitud de texto, etc.). Una alternativa más sofisticada
sería usar un modelo chico para clasificar, pero esa metaclasificación tiene
su propio costo y latencia, lo que rompe el objetivo de optimización.
"""
from dataclasses import dataclass

from core.llm import ModelTier


@dataclass(frozen=True)
class RoutingDecision:
    """
    Resultado de la clasificación.

    Incluye el tier elegido y el motivo, para que sea trazable y se pueda
    loguear o mostrar al usuario.
    """
    tier: ModelTier
    reason: str


# ---------------------------------------------------------------------------
# Investigator
# ---------------------------------------------------------------------------

def classify_investigator(topic: str) -> RoutingDecision:
    """
    Decide el tier para el Investigator.

    Señales:
      - Topics muy cortos o genéricos → SIMPLE alcanza.
      - Topics largos o con múltiples conceptos → puede beneficiarse de COMPLEX.
    """
    word_count = len(topic.split())

    if word_count <= 10:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=f"Topic corto ({word_count} palabras): SIMPLE alcanza.",
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=f"Topic extenso ({word_count} palabras): COMPLEX para mejor comprensión.",
    )


# ---------------------------------------------------------------------------
# Curator
# ---------------------------------------------------------------------------

def classify_curator(
    num_approved_subtopics: int,
    avg_rationale_length: int,
) -> RoutingDecision:
    """
    Decide el tier para el Curator.

    Señales:
      - Pocos subtemas con rationales cortos → análisis simple, SIMPLE alcanza.
      - Muchos subtemas o rationales profundos → COMPLEX para síntesis seria.
    """
    if num_approved_subtopics == 0:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason="Sin subtemas aprobados: tier mínimo.",
        )

    if num_approved_subtopics <= 2 and avg_rationale_length < 100:
        return RoutingDecision(
            tier=ModelTier.SIMPLE,
            reason=(
                f"Carga liviana ({num_approved_subtopics} subtemas, "
                f"rationales de {avg_rationale_length} chars promedio): SIMPLE alcanza."
            ),
        )

    return RoutingDecision(
        tier=ModelTier.COMPLEX,
        reason=(
            f"Carga significativa ({num_approved_subtopics} subtemas, "
            f"rationales de {avg_rationale_length} chars promedio): COMPLEX para análisis profundo."
        ),
    )


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

def classify_reporter(curated_content_length: int) -> RoutingDecision:
    """
    Decide el tier para el Reporter.

    Señales:
      - Contenido curado muy chico → SIMPLE alcanza para formatearlo.
      - Contenido extenso → COMPLEX para producir un reporte coherente.

    El Reporter es más conservador: tiende a COMPLEX porque es el output
    visible al usuario y la calidad de la prosa importa.
    """
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
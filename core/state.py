from datetime import datetime
from enum import Enum
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict
from operator import add


class SubtopicStatus(str, Enum):
    """Estado de un subtema durante el ciclo de validación humana."""
    PROPOSED = "proposed"      # Sugerido por el Investigator
    APPROVED = "approved"      # Aprobado por el humano
    REJECTED = "rejected"      # Rechazado por el humano
    MODIFIED = "modified"      # Aprobado pero con título editado


class Subtopic(BaseModel):
    """Un subtema de investigación propuesto por el Investigator."""
    model_config = ConfigDict(use_enum_values=True)

    id: int = Field(..., description="Unique ID, starting at 1")
    title: str = Field(..., min_length=3, description="Title of the subtopic")
    rationale: str = Field(..., description="Why this subtopic is relevant")
    status: SubtopicStatus = SubtopicStatus.PROPOSED


class Source(BaseModel):
    """Fuente de información encontrada por el Investigator."""
    title: str
    url: str
    snippet: str = Field(..., description="Brief summary of the content")
    subtopic_id: int = Field(..., description="Which subtopic it belongs to")


class UsageEntry(BaseModel):
    """Registro de uso de un modelo para tracking de costos."""
    timestamp: datetime = Field(default_factory=datetime.now)
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    routing_reason: str | None = None

class ResearchState(BaseModel):
    """
    Estado global del sistema, viaja entre los nodos del grafo.

    Cada nodo recibe el estado, lo modifica, y lo devuelve.
    LangGraph se encarga de mergear los cambios.
    """
    model_config = ConfigDict(use_enum_values=True)

    # Input del usuario
    topic: str = Field(..., description="Research topic")

    # Salida del Investigator
    subtopics: list[Subtopic] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)

    # Salida del human-in-the-loop
    human_feedback_raw: str | None = None  # Lo que el humano tipeó

    # Salida del Curator
    curated_content: str | None = None

    # Salida del Reporter
    final_report: str | None = None

    # Tracking de costos (se va acumulando, por eso el Annotated)
    usage_log: Annotated[list[UsageEntry], add] = Field(default_factory=list)

    # Metadatos
    started_at: datetime = Field(default_factory=datetime.now)

    language: str | None = None  # detectado por el Investigator
"""
Supervisor Agent.

Es el orquestador del sistema multi-agente. Sus tres responsabilidades,
siguiendo la consigna del challenge, son:

  1. Orquestar el workflow completo (decidir qué agente corre y cuándo).
  2. Gestionar el pasaje de datos entre agentes.
  3. Manejar el estado durante las interacciones humanas.

A diferencia de los otros agentes (Investigator, Curator, Reporter), el
Supervisor NO usa un LLM. Sus decisiones son determinísticas: cuándo
ejecutar cada nodo, cuándo pausar para input humano, cuándo reanudar.
Usar un LLM acá sería innecesario y costoso, porque no hay razonamiento
semántico involucrado.

Implementación: encapsula la complejidad de LangGraph (creación del grafo,
manejo del ciclo interrupt/resume, inspección del estado) detrás de una
fachada simple. La capa de presentación (main.py) solo necesita conocer
esta fachada, no los detalles internos de LangGraph.
"""
import uuid
from dataclasses import dataclass
from typing import Callable

from langgraph.types import Command

from core.graph import build_graph
from core.state import ResearchState, Subtopic, Source, UsageEntry

@dataclass
class HumanReviewRequest:
    """Lo que el Supervisor le pasa al callback cuando necesita input humano."""
    topic: str
    subtopics: list[dict]   # [{"id", "title", "rationale"}]
    sources: list[dict]     # [{"title", "url", "snippet", "subtopic_id"}]


@dataclass
class ResearchResult:
    """Resultado completo de una corrida del flujo."""
    topic: str
    final_report: str
    subtopics: list[Subtopic]
    sources: list[Source]
    usage_log: list[UsageEntry]
    language: str | None


# Tipo del callback que recibe el Supervisor: dado un request, devuelve
# el comando del humano (ej. "approve 1,3, reject 2").
HumanReviewCallback = Callable[[HumanReviewRequest], str]

class Supervisor:
    """
    Orquestador del sistema multi-agente.

    Encapsula el grafo de LangGraph y expone una API simple a la capa
    de presentación. No tiene LLM: todas sus decisiones son determinísticas.
    """

    def __init__(self):
        self._graph = build_graph()

    def run(
        self,
        topic: str,
        on_human_review: HumanReviewCallback,
    ) -> ResearchResult:
        """
        Ejecuta el flujo completo de investigación.

        Args:
            topic: el tema a investigar.
            on_human_review: callback que el Supervisor invoca cuando necesita
                input humano. Recibe un HumanReviewRequest y debe devolver
                un string con el comando (ej. "approve 1,3").

        Returns:
            ResearchResult con el reporte final y toda la metadata.
        """
        # Cada corrida usa un thread_id único para no mezclar estados
        config = {"configurable": {"thread_id": f"session-{uuid.uuid4().hex[:8]}"}}
        initial_state = ResearchState(topic=topic)

        # PRIMERA EJECUCIÓN: corre hasta el primer interrupt() del grafo
        self._graph.invoke(initial_state, config=config)

        # Si el grafo se pausó esperando input humano, lo manejamos
        if self._is_paused(config):
            review_request = self._build_review_request(config)
            user_response = on_human_review(review_request)
            self._resume(config, user_response)

        # Devolver el resultado final estructurado
        return self._collect_result(config)

    def _is_paused(self, config: dict) -> bool:
        """True si el grafo está pausado esperando input."""
        snapshot = self._graph.get_state(config)
        return bool(snapshot.next)

    def _build_review_request(self, config: dict) -> HumanReviewRequest:
        """Extrae el payload del interrupt y lo convierte en un HumanReviewRequest."""
        snapshot = self._graph.get_state(config)

        # Recuperar el payload que el nodo human_review pasó a interrupt()
        payload = {}
        for task in snapshot.tasks:
            if task.interrupts:
                payload = task.interrupts[0].value
                break

        return HumanReviewRequest(
            topic=payload.get("topic", ""),
            subtopics=payload.get("subtopics", []),
            sources=payload.get("sources", []),
        )

    def _resume(self, config: dict, user_input: str) -> None:
        """Reanuda el grafo con la respuesta del humano."""
        self._graph.invoke(Command(resume=user_input), config=config)

    def _collect_result(self, config: dict) -> ResearchResult:
        """Lee el estado final del grafo y lo empaqueta en un ResearchResult."""
        final_state = self._graph.get_state(config).values

        return ResearchResult(
            topic=final_state.get("topic", ""),
            final_report=final_state.get("final_report", ""),
            subtopics=final_state.get("subtopics", []),
            sources=final_state.get("sources", []),
            usage_log=final_state.get("usage_log", []),
            language=final_state.get("language"),
        )
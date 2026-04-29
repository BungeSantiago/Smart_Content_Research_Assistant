"""
Construcción del grafo de LangGraph.
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from core.state import ResearchState
from core.human_review import human_review_node
from agents.investigator import investigator_node
from agents.curator import curator_node
from agents.reporter import reporter_node


def build_graph():
    """
    Construye y compila el grafo del sistema.

    Flow:
      START → investigator → human_review → curator → reporter → END
    """
    graph = StateGraph(ResearchState)

    graph.add_node("investigator", investigator_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("curator", curator_node)
    graph.add_node("reporter", reporter_node)

    graph.add_edge(START, "investigator")
    graph.add_edge("investigator", "human_review")
    graph.add_edge("human_review", "curator")
    graph.add_edge("curator", "reporter")
    graph.add_edge("reporter", END)

    # Serializer con tipos custom registrados como permitidos.
    # Esto silencia los warnings y prepara el código para versiones futuras
    # de LangGraph donde la deserialización de tipos no registrados será bloqueada.
    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("core.state", "Subtopic"),
            ("core.state", "SubtopicStatus"),
            ("core.state", "UsageEntry"),
            ("core.state", "Source"),
        ]
    )
    checkpointer = MemorySaver(serde=serde)

    return graph.compile(checkpointer=checkpointer)
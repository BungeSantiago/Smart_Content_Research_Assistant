"""
Curator Agent.

Toma los subtemas aprobados por el humano y produce análisis profundo.
El tier se decide dinámicamente según la carga de trabajo (subtemas + fuentes).
"""
from langchain_core.messages import SystemMessage, HumanMessage

from core.state import ResearchState, SubtopicStatus
from core.llm import get_llm, load_prompt, ModelTier
from core.llm_tracking import invoke_with_tracking
from core.complexity_router import classify_curator


def curator_node(state: ResearchState) -> dict:
    """Genera análisis profundo de los subtemas aprobados."""
    approved = [
        s for s in state.subtopics
        if s.status in (SubtopicStatus.APPROVED, SubtopicStatus.MODIFIED)
    ]

    if not approved:
        return {"curated_content": "_No hay subtemas aprobados para curar._"}

    # Métricas para el classifier
    avg_len = sum(len(s.rationale) for s in approved) // len(approved)

    approved_ids = {s.id for s in approved}
    related_sources = [src for src in state.sources if src.subtopic_id in approved_ids]
    avg_snippet = (
        sum(len(s.snippet) for s in related_sources) // len(related_sources)
        if related_sources else 0
    )

    decision = classify_curator(
        num_approved_subtopics=len(approved),
        avg_rationale_length=avg_len,
        total_sources=len(related_sources),
        avg_snippet_length=avg_snippet,
    )

    llm = get_llm(decision.tier, temperature=0.3)

    system_prompt = load_prompt("curator_system")
    language = state.language or "the same language as the subtopics"

    # Armar el contexto con subtemas aprobados Y sus fuentes asociadas
    sections = []
    for s in approved:
        related = [src for src in state.sources if src.subtopic_id == s.id]
        section = f"### {s.title}\n{s.rationale}\n"
        if related:
            section += "\nFuentes relacionadas:\n"
            for src in related:
                section += f"- {src.title} ({src.url}): {src.snippet}\n"
        sections.append(section)

    subtopics_text = "\n".join(sections)

    user_prompt = (
        f"General topic: {state.topic}\n\n"
        f"Approved subtopics with their supporting sources:\n\n"
        f"{subtopics_text}\n\n"
        f"IMPORTANT: Respond in {language}.\n\n"
        f"Generate the complete curated analysis. When relevant, ground your analysis "
        f"in the provided sources."
    )

    response, usage = invoke_with_tracking(
        llm=llm,
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ],
        agent_name="curator",
    )

    usage.routing_reason = decision.reason

    return {
        "curated_content": str(response.content),
        "usage_log": [usage],
    }
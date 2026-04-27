"""
Curator Agent.

Toma los subtemas aprobados por el humano y produce análisis profundo.
Usa el tier COMPLEX porque la síntesis requiere razonamiento elaborado.
"""
from langchain_core.messages import SystemMessage, HumanMessage

from core.state import ResearchState, SubtopicStatus
from core.llm import get_llm, load_prompt, ModelTier
from core.llm_tracking import invoke_with_tracking


def curator_node(state: ResearchState) -> dict:
    """Genera análisis profundo de los subtemas aprobados."""
    approved = [
        s for s in state.subtopics
        if s.status in (SubtopicStatus.APPROVED, SubtopicStatus.MODIFIED)
    ]

    if not approved:
        return {"curated_content": "_No hay subtemas aprobados para curar._"}

    llm = get_llm(ModelTier.COMPLEX, temperature=0.3)
    system_prompt = load_prompt("curator_system")
    language = state.language or "the same language as the subtopics"

    # Armar el contexto con los subtemas aprobados
    subtopics_text = "\n".join(
        f"- **{s.title}**: {s.rationale}"
        for s in approved
    )

    user_prompt = (
        f"General topic: {state.topic}\n\n"
        f"Approved subtopics to analyze:\n\n"
        f"{subtopics_text}\n\n"
        f"IMPORTANT: Respond in {language}.\n\n"
        f"Generate the complete curated analysis."
    )

    response, usage = invoke_with_tracking(
        llm=llm,
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ],
        agent_name="curator",
    )

    return {
        "curated_content": str(response.content),
        "usage_log": [usage],
    }
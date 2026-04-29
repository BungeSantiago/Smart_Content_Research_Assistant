from langgraph.types import interrupt
from core.state import ResearchState, Subtopic, SubtopicStatus
from core.human_parser import parse_human_input, HumanFeedback


def human_review_node(state: ResearchState) -> dict:
    """
    Pausa el grafo y espera input humano.

    El interrupt() devuelve un payload que después le pasamos cuando
    reanudamos el grafo desde main.py. Ese payload es el string
    que el humano tipeó por consola.
    """
    # Construir el payload que vamos a mostrar al humano cuando se pause
    review_payload = {
        "topic": state.topic,
        "subtopics": [
            {"id": s.id, "title": s.title, "rationale": s.rationale}
            for s in state.subtopics
        ],
        "sources": [
            {
                "title": s.title,
                "url": s.url,
                "snippet": s.snippet,
                "subtopic_id": s.subtopic_id,
            }
            for s in state.sources
        ],
    }

    # PAUSA: devuelve el control al invocador. Cuando se reanude, esto
    # devuelve el valor que le pasen al Command(resume=...)
    user_input: str = interrupt(review_payload)

    # Parsear y aplicar el feedback
    feedback = parse_human_input(user_input)
    updated_subtopics = _apply_feedback(state.subtopics, feedback)

    return {
        "subtopics": updated_subtopics,
        "human_feedback_raw": user_input,
    }


def _apply_feedback(
    subtopics: list[Subtopic],
    feedback: HumanFeedback,
) -> list[Subtopic]:
    """Aplica el feedback humano a la lista de subtemas."""
    updated: list[Subtopic] = []

    for st in subtopics:
        new_st = st.model_copy()  # copia inmutable

        if st.id in feedback.approved_ids:
            new_st.status = SubtopicStatus.APPROVED
        elif st.id in feedback.rejected_ids:
            new_st.status = SubtopicStatus.REJECTED
        elif st.id in feedback.modifications:
            new_st.title = feedback.modifications[st.id]
            new_st.status = SubtopicStatus.MODIFIED

        updated.append(new_st)

    # Agregar nuevos subtemas (additions)
    next_id = max((s.id for s in subtopics), default=0) + 1
    for title in feedback.additions:
        updated.append(Subtopic(
            id=next_id,
            title=title,
            rationale="Added by human during review",
            status=SubtopicStatus.APPROVED,
        ))
        next_id += 1

    return updated
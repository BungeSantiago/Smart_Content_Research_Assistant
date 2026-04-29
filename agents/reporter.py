from langchain_core.messages import SystemMessage, HumanMessage

from core.state import ResearchState
from core.llm import get_llm, load_prompt, ModelTier
from core.llm_tracking import invoke_with_tracking
from core.complexity_router import classify_reporter

def reporter_node(state: ResearchState) -> dict:
    """Genera el reporte final pulido."""
    if not state.curated_content:
        return {
            "final_report": (
                f"# Report: {state.topic}\n\n"
                f"There is no curated content to report."
            )
        }

    # Decidir el tier según la cantidad de contenido a procesar
    decision = classify_reporter(len(state.curated_content))
    llm = get_llm(decision.tier, temperature=0.4)

    system_prompt = load_prompt("reporter_system")
    language = state.language or "the same language as the subtopics"

    user_prompt = (
        f"Theme: {state.topic}\n\n"
        f"Curated content to transform into final report:\n\n"
        f"---\n{state.curated_content}\n---\n\n"
        f"IMPORTANT: Respond in {language}.\n\n"
        f"Generate the final report in markdown following the system prompt instructions."
    )

    response, usage = invoke_with_tracking(
        llm=llm,
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ],
        agent_name="reporter",
    )

    usage.routing_reason = decision.reason

    return {
        "final_report": str(response.content),
        "usage_log": [usage],
    }


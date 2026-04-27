"""
Investigator Agent.
"""
import json
import re
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from core.state import ResearchState, Subtopic
from core.llm import get_llm, load_prompt, ModelTier


class _SubtopicProposal(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    rationale: str = Field(..., min_length=10, max_length=300)


class _InvestigatorOutput(BaseModel):
    subtopics: list[_SubtopicProposal] = Field(..., min_length=3, max_length=8)


def _detect_language(text: str) -> str:
    """
    Heurística simple para detectar idioma del topic.
    Devuelve un nombre de idioma en inglés que el LLM entiende sin ambigüedad.
    """
    text_lower = text.lower()

    # Caracteres específicos del español
    if re.search(r"[ñáéíóúü¿¡]", text_lower):
        return "Spanish"

    # Palabras frecuentes en español que no aparecen en inglés
    spanish_words = {"de", "la", "el", "en", "los", "las", "para", "con", "por", "del"}
    words = set(re.findall(r"\b\w+\b", text_lower))
    if len(words & spanish_words) >= 2:
        return "Spanish"

    return "English"


def investigator_node(state: ResearchState) -> dict:
    """Genera subtemas usando un LLM."""
    from core.llm_tracking import invoke_structured_with_tracking

    language = _detect_language(state.topic)

    llm = get_llm(ModelTier.SIMPLE, temperature=0.5)
    structured_llm = llm.with_structured_output(_InvestigatorOutput, method="json_mode")

    system_prompt = load_prompt("investigator_system")
    schema_json = json.dumps(_InvestigatorOutput.model_json_schema(), indent=2)

    user_prompt = (
        f"CRITICAL INSTRUCTION: You MUST write all subtopic titles and rationales in {language}. "
        f"This is non-negotiable, regardless of the topic content.\n\n"
        f"Topic to research: {state.topic}\n\n"
        f"Generate the most relevant subtopics for this topic, written in {language}.\n\n"
        f"You MUST respond with a valid JSON object that matches this schema:\n"
        f"```json\n{schema_json}\n```\n\n"
        f"Return ONLY the JSON object, no extra text, no markdown formatting. "
        f"Remember: all text content must be in {language}."
    )

    response, usage = invoke_structured_with_tracking(
        structured_llm=structured_llm,
        base_llm=llm,
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ],
        agent_name="investigator",
    )

    subtopics = [
        Subtopic(
            id=idx + 1,
            title=proposal.title,
            rationale=proposal.rationale,
        )
        for idx, proposal in enumerate(response.subtopics)
    ]

    return {
        "subtopics": subtopics,
        "language": language,
        "usage_log": [usage],
    }
import re
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from core.state import ResearchState, Subtopic, Source
from core.llm import get_llm, load_prompt, ModelTier
from core.complexity_router import classify_investigator
from core.llm_tracking import invoke_structured_with_tracking
from tools.web_search import search_web, SearchResult


class _SubtopicProposal(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    rationale: str = Field(..., min_length=10, max_length=300)
    source_indices: list[int] = Field(
        default_factory=list,
        description="Indices (1-based) of the sources that support this subtopic",
    )


class _InvestigatorOutput(BaseModel):
    subtopics: list[_SubtopicProposal] = Field(..., min_length=3, max_length=8)


def _detect_language(text: str) -> str:
    """Heurística simple para detectar idioma del topic."""
    text_lower = text.lower()
    if re.search(r"[ñáéíóúü¿¡]", text_lower):
        return "Spanish"
    spanish_words = {"de", "la", "el", "en", "los", "las", "para", "con", "por", "del"}
    words = set(re.findall(r"\b\w+\b", text_lower))
    if len(words & spanish_words) >= 2:
        return "Spanish"
    return "English"


def _format_sources_for_prompt(results: list[SearchResult]) -> str:
    """Formatea los resultados de búsqueda como contexto para el LLM."""
    if not results:
        return "(No web results available — propose subtopics based on general knowledge.)"

    lines = []
    for idx, r in enumerate(results, start=1):
        lines.append(f"[{idx}] {r.title}\n    URL: {r.url}\n    {r.snippet}")
    return "\n\n".join(lines)


def investigator_node(state: ResearchState) -> dict:
    """Genera subtemas y fuentes a partir del topic del usuario."""
    language = _detect_language(state.topic)

    # 1. Búsqueda web
    search_results = search_web(state.topic, max_results=8)

    # 2. Decidir el tier según la complejidad del topic
    decision = classify_investigator(state.topic)
    llm = get_llm(decision.tier, temperature=0.5)
    structured_llm = llm.with_structured_output(_InvestigatorOutput, method="json_mode")

    # 3. Armar el prompt con las fuentes como contexto
    system_prompt = load_prompt("investigator_system")
    sources_text = _format_sources_for_prompt(search_results)

    user_prompt = (
        f"CRITICAL INSTRUCTION: You MUST write all subtopic titles and rationales in {language}. "
        f"This is non-negotiable, regardless of the topic content.\n\n"
        f"Topic to research: {state.topic}\n\n"
        f"Web search results (use these to ground your subtopics in real sources):\n\n"
        f"{sources_text}\n\n"
        f"Generate between 3 and 8 of the most relevant subtopics for this topic, written in {language}. "
        f"For each subtopic, list the indices of the search results that best support it "
        f"(1-based, referring to the [N] markers above). If a subtopic is not directly "
        f"covered by any source, leave source_indices as an empty array.\n\n"
        f"Respond with a JSON object that has a single top-level key \"subtopics\". "
        f"Its value must be an array of objects, where each object has exactly these three fields:\n"
        f"  - \"title\": string (between 3 and 100 characters)\n"
        f"  - \"rationale\": string (between 10 and 300 characters)\n"
        f"  - \"source_indices\": array of integers (1-based source indices, or empty array)\n\n"
        f"Example of the EXACT shape expected (with placeholder content):\n"
        f'{{"subtopics": [\n'
        f'  {{"title": "First subtopic title", "rationale": "Why this matters.", "source_indices": [1, 3]}},\n'
        f'  {{"title": "Second subtopic title", "rationale": "Another reason.", "source_indices": []}}\n'
        f"]}}\n\n"
        f"Return ONLY the JSON object, with no schema, no markdown fences, and no extra text. "
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
    usage.routing_reason = decision.reason

    # 4. Construir los subtemas y asociar las fuentes
    subtopics: list[Subtopic] = []
    sources: list[Source] = []

    for idx, proposal in enumerate(response.subtopics):
        subtopic_id = idx + 1
        subtopics.append(Subtopic(
            id=subtopic_id,
            title=proposal.title,
            rationale=proposal.rationale,
        ))

        # Vincular las fuentes que el LLM eligió para este subtema
        for src_idx in proposal.source_indices:
            # src_idx es 1-based, pasar a 0-based y validar
            zero_idx = src_idx - 1
            if 0 <= zero_idx < len(search_results):
                r = search_results[zero_idx]
                sources.append(Source(
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                    subtopic_id=subtopic_id,
                ))

    return {
        "subtopics": subtopics,
        "sources": sources,
        "language": language,
        "usage_log": [usage],
    }
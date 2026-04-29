"""
Web search tool using DuckDuckGo.

Provee una interfaz simple para buscar en la web. La función devuelve
resultados estructurados (modelos Pydantic) listos para integrarse al
flujo del Investigator.

DuckDuckGo no requiere API key, pero puede rate-limitar si se hacen
demasiadas queries seguidas. La función maneja errores de manera tolerante:
si la búsqueda falla, devuelve lista vacía en vez de romper el flujo.
"""
import logging
from pydantic import BaseModel, Field
from ddgs import DDGS


logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Resultado individual de una búsqueda web."""
    title: str = Field(..., description="Título de la página")
    url: str = Field(..., description="URL del resultado")
    snippet: str = Field(..., description="Fragmento descriptivo del contenido")


def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Busca en la web usando DuckDuckGo.

    Args:
        query: la consulta a buscar.
        max_results: cantidad máxima de resultados a devolver.

    Returns:
        Lista de SearchResult. Lista vacía si la búsqueda falla.
    """
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed for '{query}': {e}")
        return []

    results = []
    for raw in raw_results:
        # La estructura del resultado de ddgs:
        #   { 'title': ..., 'href': ..., 'body': ... }
        try:
            results.append(SearchResult(
                title=raw.get("title", "Sin título"),
                url=raw.get("href", ""),
                snippet=raw.get("body", ""),
            ))
        except Exception as e:
            logger.warning(f"Skipping malformed search result: {e}")
            continue

    return results
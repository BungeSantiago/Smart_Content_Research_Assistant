"""
Persistencia de reportes en disco.

Guarda los reportes generados como archivos markdown en la carpeta `reports/`,
usando un nombre derivado del topic + timestamp para garantizar unicidad
y orden cronológico.
"""
import re
from datetime import datetime
from pathlib import Path

from agents.supervisor import ResearchResult


REPORTS_DIR = Path("reports")


def save_report(result: ResearchResult, include_usage: bool = True) -> Path:
    """
    Guarda el reporte en disco y devuelve el path del archivo creado.

    Args:
        result: el ResearchResult devuelto por el Supervisor.
        include_usage: si True, agrega al final del archivo un resumen de
            tokens y costo por agente.

    Returns:
        Path absoluto del archivo creado.
    """
    REPORTS_DIR.mkdir(exist_ok=True)

    filename = _build_filename(result.topic)
    path = REPORTS_DIR / filename

    content = _build_content(result, include_usage=include_usage)
    path.write_text(content, encoding="utf-8")

    return path.resolve()


def _build_filename(topic: str) -> str:
    """
    Genera un nombre de archivo seguro y descriptivo a partir del topic.

    Ejemplo: "Renewable Energy in Europe!" + 2026-04-29_15-42 →
             "renewable-energy-in-europe_2026-04-29_15-42.md"
    """
    # Slugify: solo letras/números/guiones, todo en minúsculas, con guiones
    slug = topic.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)        # quitar puntuación
    slug = re.sub(r"[\s_]+", "-", slug)         # espacios/underscores → guiones
    slug = re.sub(r"-+", "-", slug).strip("-")  # colapsar guiones

    # Limitar a 60 chars para que el nombre no sea ridículo
    slug = slug[:60].rstrip("-") or "report"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{slug}_{timestamp}.md"


def _build_content(result: ResearchResult, include_usage: bool) -> str:
    """Arma el contenido del archivo: el reporte + opcionalmente el resumen de uso."""
    parts = [result.final_report or "_(no report generated)_"]

    if include_usage and result.usage_log:
        parts.append("\n\n---\n\n")
        parts.append(_format_usage_summary(result.usage_log))

    return "".join(parts)


def _format_usage_summary(usage_log) -> str:
    """Genera un resumen de uso en markdown."""
    lines = ["## Usage Summary\n"]
    lines.append("| Agent | Model | Input tokens | Output tokens | Cost (USD) |")
    lines.append("|---|---|---:|---:|---:|")

    total_input = 0
    total_output = 0
    total_cost = 0.0

    for entry in usage_log:
        lines.append(
            f"| {entry.agent} | `{entry.model}` "
            f"| {entry.input_tokens:,} | {entry.output_tokens:,} "
            f"| ${entry.estimated_cost_usd:.6f} |"
        )
        total_input += entry.input_tokens
        total_output += entry.output_tokens
        total_cost += entry.estimated_cost_usd

    lines.append(
        f"| **TOTAL** | | **{total_input:,}** | **{total_output:,}** "
        f"| **${total_cost:.6f}** |"
    )

    # Decisiones de routing si están disponibles
    routing_decisions = [e for e in usage_log if getattr(e, "routing_reason", None)]
    if routing_decisions:
        lines.append("\n### Routing decisions\n")
        for entry in routing_decisions:
            lines.append(f"- **{entry.agent}** → `{entry.model}`: {entry.routing_reason}")

    return "\n".join(lines) + "\n"
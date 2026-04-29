"""
Smart Research Assistant - Entry point (CLI).

Esta capa solo se ocupa de la presentación: pedir el topic, mostrar los
subtemas para revisión, recolectar input humano, y mostrar el reporte
final con el resumen de costos.

La orquestación del flujo está en agents/supervisor.py.
"""
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

from agents.supervisor import Supervisor, HumanReviewRequest, ResearchResult
from core.cost_summary import render_cost_summary

load_dotenv()
console = Console()


def main() -> None:
    _print_banner()

    topic = _get_topic()
    if not topic:
        return

    console.print(f"\n[dim]Investigando: [bold]{topic}[/bold]...[/dim]\n")

    # El Supervisor maneja toda la orquestación.
    # Solo le pasamos un callback para que sepa cómo pedir input humano.
    supervisor = Supervisor()
    result = supervisor.run(
        topic=topic,
        on_human_review=_handle_human_review,
    )

    _show_final_report(result)
    render_cost_summary(console, result.usage_log)


# Capa de presentación: todo lo que tiene que ver con la CLI

def _print_banner() -> None:
    """Muestra el banner inicial."""
    console.print(Panel.fit(
        "[bold cyan]Smart Research Assistant[/bold cyan]\n"
        "[dim]Multi-agent system[/dim]",
        border_style="cyan",
    ))


def _get_topic() -> str:
    """Obtiene el topic desde args de CLI o prompt interactivo."""
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = Prompt.ask("\n[bold]What topic would you like to research?[/bold]")

    topic = topic.strip()
    if not topic:
        console.print("[red]Topic is empty. Exiting.[/red]")
        return ""
    return topic


def _handle_human_review(request: HumanReviewRequest) -> str:
    """
    Callback invocado por el Supervisor cuando necesita input humano.
    Esta función conoce la CLI; el Supervisor no.
    """
    _present_subtopics_for_review(request)

    user_input = Prompt.ask(
        "\n[bold cyan]Your Decision[/bold cyan]\n"
        "[dim]Commands: approve N,M | reject N | modify N to 'X' | add 'X'[/dim]\n"
        "[dim]Example: approve 1,3, reject 2, add 'Use Cases'[/dim]\n>"
    )
    return user_input


def _present_subtopics_for_review(request: HumanReviewRequest) -> None:
    """Muestra los subtemas con sus fuentes asociadas."""
    sources_by_subtopic: dict[int, list[dict]] = {}
    for src in request.sources:
        sources_by_subtopic.setdefault(src["subtopic_id"], []).append(src)

    lines = [f"[bold]Topic:[/bold] {request.topic}"]
    if request.sources:
        lines.append(f"[dim]Sources found: {len(request.sources)}[/dim]")
    lines.append("")

    for s in request.subtopics:
        lines.append(f"  [bold cyan]{s['id']}.[/bold cyan] {s['title']}")
        lines.append(f"     [dim]{s['rationale']}[/dim]")

        related = sources_by_subtopic.get(s["id"], [])
        for src in related[:3]:
            lines.append(f"     [blue]↪[/blue] [dim italic]{src['title']}[/dim italic]")

        lines.append("")

    console.print()
    console.print(Panel(
        "\n".join(lines).rstrip(),
        title="[bold yellow]Proposed Subtopics — Review and Decide[/bold yellow]",
        border_style="yellow",
    ))


def _show_final_report(result: ResearchResult) -> None:
    """Muestra el reporte final renderizado."""
    console.print()
    console.print(Panel(
        Markdown(result.final_report or "_(no report)_"),
        title="[bold green]Final Report[/bold green]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
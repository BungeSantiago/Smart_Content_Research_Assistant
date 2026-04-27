"""
Smart Research Assistant - Entry point.

Orquesta el grafo de LangGraph, maneja la interrupción para human-in-the-loop,
y presenta el reporte final.
"""
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from langgraph.types import Command

from core.graph import build_graph
from core.state import ResearchState
from core.cost_summary import render_cost_summary


load_dotenv()
console = Console()


def main() -> None:
    # Banner
    console.print(Panel.fit(
        "[bold cyan]Smart Research Assistant[/bold cyan]\n"
        "[dim]Sistema multi-agente con human-in-the-loop[/dim]",
        border_style="cyan"
    ))

    # Tema desde argv o prompt interactivo
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = Prompt.ask("\n[bold]¿Qué tema querés investigar?[/bold]")

    if not topic.strip():
        console.print("[red]Tema vacío. Saliendo.[/red]")
        return

    # Construir el grafo
    app = build_graph()
    config = {"configurable": {"thread_id": "session-1"}}

    # Estado inicial
    initial_state = ResearchState(topic=topic)

    console.print(f"\n[dim]Investigando: [bold]{topic}[/bold]...[/dim]\n")

    # PRIMERA EJECUCIÓN: corre hasta el primer interrupt()
    result = app.invoke(initial_state, config=config)

    # Verificar si nos interrumpimos en human_review
    state_snapshot = app.get_state(config)
    if state_snapshot.next:  # hay nodos pendientes => estamos pausados
        # Recuperar el payload que pasamos a interrupt()
        # En LangGraph 0.2+, los interrupts viven en state_snapshot.tasks
        interrupt_payload = _get_interrupt_payload(state_snapshot)

        # Mostrar al humano
        _present_subtopics_for_review(interrupt_payload)

        # Recolectar input
        user_input = Prompt.ask(
            "\n[bold cyan]Tu decisión[/bold cyan]\n"
            "[dim]Comandos: approve N,M | reject N | modify N to 'X' | add 'X'[/dim]\n"
            "[dim]Ejemplo: approve 1,3, reject 2, add 'Casos de uso'[/dim]\n>"
        )

        # REANUDAR el grafo con el input humano
        result = app.invoke(Command(resume=user_input), config=config)

    # Mostrar el reporte final
    _show_final_report(result)
    
    # Mostrar el resumen de costos
    usage_log = result.get("usage_log", [])
    render_cost_summary(console, usage_log)


def _get_interrupt_payload(state_snapshot) -> dict:
    """Extrae el payload del interrupt del snapshot del estado."""
    for task in state_snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return {}


def _present_subtopics_for_review(payload: dict) -> None:
    """Muestra los subtemas al humano con formato lindo."""
    console.print()
    console.print(Panel(
        f"[bold]Tema:[/bold] {payload.get('topic', '')}\n\n"
        + "\n".join(
            f"  [bold cyan]{s['id']}.[/bold cyan] {s['title']}\n"
            f"     [dim]{s['rationale']}[/dim]"
            for s in payload.get("subtopics", [])
        ),
        title="[bold yellow]Subtemas Propuestos — Revisá y decidí[/bold yellow]",
        border_style="yellow",
    ))


def _show_final_report(result: dict) -> None:
    """Muestra el reporte final renderizado en markdown."""
    report = result.get("final_report", "(sin reporte)")
    console.print()
    console.print(Panel(
        Markdown(report),
        title="[bold green]Reporte Final[/bold green]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
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
from core.human_parser import parse_human_input
from core.report_saver import save_report


load_dotenv()
console = Console()


def main() -> None:
    _print_banner()

    # Single-shot mode: topic provided as CLI argument
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:]).strip()
        if not topic:
            console.print("[red]Topic is empty. Exiting.[/red]")
            return
        _run_single_research(topic)
        return

    # Interactive mode: loop until the user exits
    _run_interactive_loop()


# ---------------------------------------------------------------------------
# Modos de ejecución
# ---------------------------------------------------------------------------

def _run_single_research(topic: str) -> None:
    """Ejecuta una sola investigación y termina. Pregunta si quiere guardar."""
    console.print(f"\n[dim]Researching: [bold]{topic}[/bold]...[/dim]\n")

    supervisor = Supervisor()
    result = supervisor.run(
        topic=topic,
        on_human_review=_handle_human_review,
    )

    _show_final_report(result)
    render_cost_summary(console, result.usage_log)

    # Preguntar si quiere guardar
    save_answer = Prompt.ask(
        "\n[bold]Save this report to disk?[/bold] [dim](y/N)[/dim]",
        default="n",
        show_default=False,
    ).strip().lower()

    if save_answer in ("y", "yes", "s", "si"):
        _handle_save(result)


def _run_interactive_loop() -> None:
    """Loop interactivo: pide topics hasta que el usuario tipee 'exit' / 'quit'."""
    console.print(
        "\n[dim]Interactive mode. Type [bold]exit[/bold] / [bold]quit[/bold] to leave, "
        "or [bold]save[/bold] after a research to save the last report.[/dim]"
    )

    supervisor = Supervisor()
    last_result: ResearchResult | None = None

    while True:
        try:
            user_input = Prompt.ask(
                "\n[bold]What topic would you like to research?[/bold] "
                "[dim](or 'save' / 'exit')[/dim]"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            return

        if not user_input:
            continue

        command = user_input.lower()

        if command in ("exit", "quit"):
            console.print("\n[dim]Goodbye.[/dim]")
            return

        if command == "save":
            _handle_save(last_result)
            continue

        # Caso default: lo tratamos como un topic a investigar
        console.print(f"\n[dim]Researching: [bold]{user_input}[/bold]...[/dim]\n")

        try:
            result = supervisor.run(
                topic=user_input,
                on_human_review=_handle_human_review,
            )
            _show_final_report(result)
            render_cost_summary(console, result.usage_log)
            last_result = result
        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Research interrupted. Returning to menu.[/yellow]"
            )
            continue
        except Exception as e:
            console.print(f"\n[red]Error during research: {e}[/red]")
            console.print("[dim]Returning to menu.[/dim]")
            continue

def _handle_save(result: ResearchResult | None) -> None:
    """Guarda el último reporte en disco, si existe."""
    if result is None or not result.final_report:
        console.print(
            "[yellow]No report to save yet. Run a research first.[/yellow]"
        )
        return

    try:
        path = save_report(result)
    except Exception as e:
        console.print(f"[red]Failed to save report: {e}[/red]")
        return

    console.print(f"[green]✓ Report saved to:[/green] [bold]{path}[/bold]")

# Capa de presentación: todo lo que tiene que ver con la CLI

def _print_banner() -> None:
    """Muestra el banner inicial."""
    console.print(Panel.fit(
        "[bold cyan]Smart Research Assistant[/bold cyan]\n"
        "[dim]Multi-agent system[/dim]",
        border_style="cyan",
    ))


def _handle_human_review(request: HumanReviewRequest) -> str:
    """
    Callback invocado por el Supervisor cuando necesita input humano.
    Insiste hasta recibir un input que genere al menos una acción aplicable.
    """
    _present_subtopics_for_review(request)

    valid_ids = {s["id"] for s in request.subtopics}

    while True:
        user_input = Prompt.ask(
            "\n[bold cyan]Your Decision[/bold cyan]\n"
            "[dim]Commands: approve N,M | reject N | modify N to 'X' | add 'X'[/dim]\n"
            "[dim]Shortcut: just numbers (e.g., '1,3') = approve 1,3[/dim]\n"
            "[dim]Full example: approve 1,3, reject 2, add 'Use Cases'[/dim]\n>"
        )

        feedback = parse_human_input(user_input)

        if feedback.is_empty:
            console.print(
                "[yellow]I didn't understand any action in your input. "
                "Try again with approve, reject, modify, add — or just numbers.[/yellow]"
            )
            continue

        for warning in feedback.validate(valid_ids):
            console.print(f"[yellow]⚠  {warning}[/yellow]")

        if feedback.has_applicable_actions(valid_ids):
            return user_input

        console.print(
            "[yellow]None of your actions are applicable to the displayed subtopics. "
            "Try again.[/yellow]"
        )


def _present_subtopics_for_review(request: HumanReviewRequest) -> None:
    """Muestra los subtemas con sus fuentes asociadas (título + snippet + URL)."""
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
        for src in related[:3]:  # max 3 sources per subtopic
            title = src.get("title", "Untitled")
            snippet = src.get("snippet", "").strip()
            url = src.get("url", "")

            if len(snippet) > 180:
                snippet = snippet[:177].rstrip() + "..."

            lines.append(f"     [blue]↪[/blue] [bold]{title}[/bold]")
            if snippet:
                lines.append(f"        [dim italic]{snippet}[/dim italic]")
            if url:
                lines.append(f"        [dim blue]{url}[/dim blue]")

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
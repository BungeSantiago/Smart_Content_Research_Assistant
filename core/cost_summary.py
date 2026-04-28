"""
Resumen visual de costos al final de la ejecución.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.state import UsageEntry


def render_cost_summary(console: Console, usage_log: list[UsageEntry]) -> None:
    """Muestra un resumen de costos por agente en la consola."""
    if not usage_log:
        return

    table = Table(
        title="[bold]Resumen de uso de modelos[/bold]",
        title_style="bold cyan",
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Agente", style="bold")
    table.add_column("Modelo", style="dim")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Costo (USD)", justify="right", style="green")

    total_input = 0
    total_output = 0
    total_cost = 0.0

    for entry in usage_log:
        table.add_row(
            entry.agent,
            entry.model,
            f"{entry.input_tokens:,}",
            f"{entry.output_tokens:,}",
            f"${entry.estimated_cost_usd:.6f}",
        )
        total_input += entry.input_tokens
        total_output += entry.output_tokens
        total_cost += entry.estimated_cost_usd

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        "",
        f"[bold]{total_input:,}[/bold]",
        f"[bold]{total_output:,}[/bold]",
        f"[bold green]${total_cost:.6f}[/bold green]",
    )

    console.print()
    console.print(table)

    # Mostrar las decisiones de routing por agente
    routing_lines = []
    for entry in usage_log:
        if entry.routing_reason:
            routing_lines.append(
                f"  • [bold]{entry.agent}[/bold] → [cyan]{entry.model}[/cyan]\n"
                f"    [dim]{entry.routing_reason}[/dim]"
            )

    if routing_lines:
        console.print(Panel(
            "\n".join(routing_lines),
            title="[bold]Decisiones de routing[/bold]",
            border_style="dim",
        ))
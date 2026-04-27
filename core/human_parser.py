"""
Parser de comandos humanos para el feedback en el ciclo de validación.

Soporta comandos como:
  - "approve 1,3"
  - "reject 2"
  - "modify 1 to 'AI ethical frameworks'"
  - "add 'AI safety concerns'"
  - Combinaciones separadas por coma: "approve 1,3, reject 2, add 'X'"
"""
import re
from dataclasses import dataclass, field


@dataclass
class HumanFeedback:
    """Resultado del parseo del input humano."""
    approved_ids: list[int] = field(default_factory=list)
    rejected_ids: list[int] = field(default_factory=list)
    modifications: dict[int, str] = field(default_factory=dict)  # id -> nuevo título
    additions: list[str] = field(default_factory=list)  # nuevos subtemas a agregar
    raw_input: str = ""

    @property
    def is_empty(self) -> bool:
        """True si el humano no especificó ninguna acción."""
        return not (
            self.approved_ids or self.rejected_ids
            or self.modifications or self.additions
        )


def parse_human_input(text: str) -> HumanFeedback:
    """
    Parsea el input del humano y devuelve un objeto estructurado.

    Es tolerante: ignora errores de formato y procesa lo que puede entender.
    """
    feedback = HumanFeedback(raw_input=text)
    text = text.strip().lower()

    # approve N,M,...
    for match in re.finditer(r"approve\s+([\d,\s]+)", text):
        ids_str = match.group(1)
        feedback.approved_ids.extend(_parse_ids(ids_str))

    # reject N,M,...
    for match in re.finditer(r"reject\s+([\d,\s]+)", text):
        ids_str = match.group(1)
        feedback.rejected_ids.extend(_parse_ids(ids_str))

    # modify N to 'texto' (acepta comillas simples o dobles)
    modify_pattern = r"modify\s+(\d+)\s+to\s+['\"]([^'\"]+)['\"]"
    for match in re.finditer(modify_pattern, text):
        subtopic_id = int(match.group(1))
        new_title = match.group(2).strip()
        feedback.modifications[subtopic_id] = new_title

    # add 'texto' (acepta comillas simples o dobles)
    add_pattern = r"add\s+['\"]([^'\"]+)['\"]"
    for match in re.finditer(add_pattern, text):
        feedback.additions.append(match.group(1).strip())

    return feedback


def _parse_ids(ids_str: str) -> list[int]:
    """Parsea una cadena tipo '1,3, 4' a [1, 3, 4]."""
    result = []
    for part in ids_str.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result
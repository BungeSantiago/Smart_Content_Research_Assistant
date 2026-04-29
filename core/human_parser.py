"""
Parser de comandos humanos para el feedback en el ciclo de validación.

Soporta:
  - "approve 1,3"
  - "reject 2"
  - "modify 1 to 'AI ethical frameworks'"
  - "add 'AI safety concerns'"
  - Combinaciones separadas por coma.

Atajos:
  - Solo números (ej. "1,3") se interpretan como "approve 1,3".
"""
import re
from dataclasses import dataclass, field


@dataclass
class HumanFeedback:
    """Resultado del parseo del input humano."""
    approved_ids: list[int] = field(default_factory=list)
    rejected_ids: list[int] = field(default_factory=list)
    modifications: dict[int, str] = field(default_factory=dict)
    additions: list[str] = field(default_factory=list)
    raw_input: str = ""

    @property
    def is_empty(self) -> bool:
        """True si el humano no especificó ninguna acción."""
        return not (
            self.approved_ids or self.rejected_ids
            or self.modifications or self.additions
        )

    def validate(self, valid_ids: set[int]) -> list[str]:
        """
        Devuelve una lista de warnings si hay problemas con el feedback.
        Lista vacía = todo bien.
        """
        warnings = []

        all_referenced = (
            set(self.approved_ids)
            | set(self.rejected_ids)
            | set(self.modifications.keys())
        )
        invalid = all_referenced - valid_ids
        if invalid:
            warnings.append(
                f"The following IDs are invalid and will be ignored: {sorted(invalid)}"
            )

        conflict = set(self.approved_ids) & set(self.rejected_ids)
        if conflict:
            warnings.append(
                f"The following IDs are both approved and rejected: {sorted(conflict)}. "
                f"Rejection will be prioritized."
            )

        return warnings

    def has_applicable_actions(self, valid_ids: set[int]) -> bool:
        """True si después de filtrar IDs inválidos, queda alguna acción."""
        return bool(
            (set(self.approved_ids) & valid_ids)
            or (set(self.rejected_ids) & valid_ids)
            or (set(self.modifications.keys()) & valid_ids)
            or self.additions
        )


_NUMBERS_ONLY_PATTERN = re.compile(r"^[\d,\s]+$")


def parse_human_input(text: str) -> HumanFeedback:
    """Parsea el input del humano y devuelve un objeto estructurado."""
    feedback = HumanFeedback(raw_input=text)
    text_clean = text.strip().lower()

    # Atajo: solo números → approve
    if text_clean and _NUMBERS_ONLY_PATTERN.match(text_clean):
        feedback.approved_ids = _parse_ids(text_clean)
        return feedback

    for match in re.finditer(r"approve\s+([\d,\s]+)", text_clean):
        feedback.approved_ids.extend(_parse_ids(match.group(1)))

    for match in re.finditer(r"reject\s+([\d,\s]+)", text_clean):
        feedback.rejected_ids.extend(_parse_ids(match.group(1)))

    modify_pattern = r"modify\s+(\d+)\s+to\s+['\"]([^'\"]+)['\"]"
    for match in re.finditer(modify_pattern, text_clean):
        subtopic_id = int(match.group(1))
        new_title = match.group(2).strip()
        feedback.modifications[subtopic_id] = new_title

    add_pattern = r"add\s+['\"]([^'\"]+)['\"]"
    for match in re.finditer(add_pattern, text_clean):
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
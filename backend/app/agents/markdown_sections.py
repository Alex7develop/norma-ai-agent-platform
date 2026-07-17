"""Helpers for parsing labeled fenced markdown sections from agent output."""


def split_fenced_sections(
    content: str,
    labels: tuple[str, ...],
) -> tuple[str, ...]:
    """Extract labeled fenced blocks; fall back to whole content for first label."""

    results: list[str] = []
    for label in labels:
        marker = f"```{label}"
        start = content.find(marker)
        if start < 0:
            results.append("")
            continue
        start = content.find("\n", start)
        if start < 0:
            results.append("")
            continue
        start += 1
        end = content.find("```", start)
        block = content[start:end].strip() if end >= 0 else content[start:].strip()
        results.append(block)

    if not any(results) and content.strip():
        results[0] = content.strip()
    return tuple(results)

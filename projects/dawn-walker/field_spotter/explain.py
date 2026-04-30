"""Pretty-print a Resolution as a human-readable diagnostic block."""

from __future__ import annotations

from typing import Dict, List

from field_spotter.models import Resolution, Sighting


def _fmt_t(t_min: int) -> str:
    """Format minutes-since-epoch as a relative '+HHhMM' duration.

    The resolver's epoch is arbitrary, so absolute times don't have a
    natural rendering. We anchor at the smallest t_min in the input
    when the caller passes the sightings list to `explain`.
    """
    sign = "-" if t_min < 0 else "+"
    t = abs(t_min)
    hh, mm = divmod(t, 60)
    return f"{sign}{hh:02d}h{mm:02d}m"


def explain(resolution: Resolution, sightings: List[Sighting] | None = None) -> str:
    """Render `resolution` as a multi-line summary.

    If `sightings` is provided, the output anchors timestamps at the
    earliest sighting and shows per-individual timelines. Without it the
    output omits times.
    """
    lines: List[str] = []
    lines.append(f"Estimated individuals: {resolution.n_individuals}")
    lines.append("-" * 60)

    if not resolution.individuals:
        lines.append("(no sightings)")
        return "\n".join(lines) + "\n"

    by_id: Dict[str, Sighting] = {}
    epoch_min = 0
    if sightings:
        by_id = {s.id: s for s in sightings}
        epoch_min = min(s.t_min for s in sightings)

    for ind in resolution.individuals:
        conf = resolution.confidence(ind.id)
        sig = ind.feature_signature()
        lines.append(
            f"{ind.id}  ({ind.n_sightings} sightings, "
            f"confidence {conf:.2f})"
        )
        lines.append(f"  features: {sig}")
        if by_id:
            for sid in ind.sighting_ids:
                s = by_id.get(sid)
                if s is None:
                    continue
                rel = _fmt_t(s.t_min - epoch_min)
                lines.append(
                    f"  {rel}  ({s.x_m:>7.1f}, {s.y_m:>7.1f}) m  [{sid}]"
                )
        else:
            lines.append("  sightings: " + ", ".join(ind.sighting_ids))
    return "\n".join(lines) + "\n"

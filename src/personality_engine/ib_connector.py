"""
Intelligence Builder Connector

Maps PersonalityChip traits to Spark Intelligence Builder's
PersonalityEvolver format and syncs the state file so IB can
read personality configuration without importing this package.

The bridge is a JSON file at ~/.spark/personality_evolution_v1.json
that PersonalityEvolver reads on startup.

Trait mapping:
    PersonalityChip (OCEAN + EQ)  →  PersonalityEvolver (5 traits)
    ─────────────────────────────────────────────────────────────
    agreeableness + empathy_style  →  warmth
    extraversion (inverted midpoint) →  directness
    openness + humor_frequency     →  playfulness
    conscientiousness              →  pacing (inverted: high consc = deliberate)
    neuroticism (inverted) + risk  →  assertiveness

This connector is called during SessionStart to sync personality
state. It's a one-way write — personality chips are the source of
truth, PersonalityEvolver adapts from there.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

IB_STATE_PATH = Path.home() / ".spark" / "personality_evolution_v1.json"
IB_STATE_VERSION = 1


def map_chip_to_evolver_traits(chip) -> dict[str, float]:
    """Map PersonalityChip OCEAN/EQ traits to PersonalityEvolver's 5 traits.

    Returns dict with warmth, directness, playfulness, pacing, assertiveness
    all in [0.0, 1.0] range.
    """
    # Warmth: agreeableness (primary) + social_awareness + empathy style bonus
    empathy_bonus = {
        "nurturing": 0.10,
        "reflective": 0.05,
        "directive": -0.05,
        "challenging": -0.10,
    }.get(chip.empathy_style, 0.0)
    warmth = chip.agreeableness * 0.6 + chip.social_awareness * 0.3 + 0.5 * 0.1 + empathy_bonus
    warmth = max(0.0, min(1.0, warmth))

    # Directness: inverse of agreeableness-extraversion blend
    # High extraversion + low agreeableness = very direct
    directness = chip.extraversion * 0.4 + (1.0 - chip.agreeableness) * 0.4 + chip.conscientiousness * 0.2
    directness = max(0.0, min(1.0, directness))

    # Playfulness: openness (primary) + humor frequency bonus
    humor_bonus = {
        "frequent": 0.15,
        "occasional": 0.05,
        "never": -0.15,
    }.get(chip.communication.get("humor_frequency", "occasional"), 0.0)
    playfulness = chip.openness * 0.6 + chip.extraversion * 0.3 + 0.5 * 0.1 + humor_bonus
    playfulness = max(0.0, min(1.0, playfulness))

    # Pacing: conscientiousness maps to deliberate (low pacing value = fast)
    # High conscientiousness = deliberate/slow pacing
    # The evolver uses high = fast, low = deliberate
    pacing = 1.0 - (chip.conscientiousness * 0.6 + (1.0 - chip.neuroticism) * 0.4)
    pacing = max(0.0, min(1.0, pacing))

    # Assertiveness: low neuroticism + risk appetite bonus
    risk_bonus = {
        "bold": 0.15,
        "moderate": 0.0,
        "conservative": -0.10,
    }.get(chip.decision_making.get("risk_appetite", "moderate"), 0.0)
    assertiveness = (1.0 - chip.neuroticism) * 0.5 + chip.extraversion * 0.3 + chip.conscientiousness * 0.2 + risk_bonus
    assertiveness = max(0.0, min(1.0, assertiveness))

    return {
        "warmth": round(warmth, 3),
        "directness": round(directness, 3),
        "playfulness": round(playfulness, 3),
        "pacing": round(pacing, 3),
        "assertiveness": round(assertiveness, 3),
    }


def sync_to_intelligence_builder(
    chip,
    state_path: Path = IB_STATE_PATH,
) -> dict[str, Any]:
    """Sync personality chip state to Intelligence Builder's PersonalityEvolver.

    Writes the trait mapping to the same JSON file that PersonalityEvolver
    reads. Preserves interaction_count from existing state if present.

    Args:
        chip: PersonalityChip to sync
        state_path: Override for the state file path

    Returns:
        The synced state dict that was written
    """
    traits = map_chip_to_evolver_traits(chip)

    # Load existing state to preserve interaction_count
    existing_count = 0
    if state_path.exists():
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
            existing_count = int(existing.get("interaction_count", 0))
        except (json.JSONDecodeError, OSError):
            pass

    state = {
        "version": IB_STATE_VERSION,
        "updated_at": time.time(),
        "interaction_count": existing_count,
        "traits": traits,
        "last_signals": {
            "source": "personality-chip",
            "personality_id": chip.id,
            "personality_name": chip.name,
        },
    }

    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass

    return state


def read_evolver_state(state_path: Path = IB_STATE_PATH) -> Optional[dict]:
    """Read current PersonalityEvolver state (for diagnostics)."""
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

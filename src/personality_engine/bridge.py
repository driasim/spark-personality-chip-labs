"""
Consciousness Bridge

Maps personality chip configuration to Spark Consciousness modules.
Writes emotional_context.v1.json for the intelligence bridge contract.

Integration points:
1. Soul Kernel     → harm_avoidance + override_hierarchy
2. Archetype Router → default_mood + mood_volatility
3. Shadow Detector  → shadow_susceptibility thresholds
4. Reframe Engine   → reframe_preference
5. Emotions Runtime → carry_over_weight + emotional_range

Bridge file: ~/.spark/bridges/consciousness/emotional_context.v1.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schema import PersonalityChip

BRIDGE_DIR = Path.home() / ".spark" / "bridges" / "consciousness"
BRIDGE_FILE = BRIDGE_DIR / "emotional_context.v1.json"


def write_bridge(
    chip: PersonalityChip,
    session_id: str = "default",
    bridge_path: Path = BRIDGE_FILE,
) -> dict:
    """
    Write the consciousness bridge file from a personality chip.

    This file is consumed by Spark Consciousness modules to configure:
    - Starting mood (archetype-router)
    - Shadow detection sensitivity (shadow-detector)
    - Emotional carry-over behavior (emotions-runtime)
    - Mission alignment (soul-kernel)

    Args:
        chip: Loaded PersonalityChip
        session_id: Current session identifier
        bridge_path: Override bridge file location

    Returns:
        The bridge payload dict that was written.
    """
    payload = build_bridge_payload(chip, session_id)

    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bridge_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


def build_bridge_payload(
    chip: PersonalityChip,
    session_id: str = "default",
) -> dict:
    """
    Build the consciousness bridge payload without writing to disk.
    Useful for testing and in-memory integration.
    """
    now = datetime.now(timezone.utc).isoformat()

    return {
        "schema": "emotional_context.v1",
        "personality_id": chip.id,
        "personality_name": chip.name,
        "session_id": session_id,
        "timestamp": now,
        "ttl_seconds": 3600,

        # ── Archetype Router config ──
        "emotional_state": {
            "mood": chip.default_mood,
            "intensity": _compute_baseline_intensity(chip),
            "volatility": chip.mood_volatility,
            "continuity_influence": chip.carry_over_weight,
            "confidence": 0.85,
        },

        # ── Guidance hints (how personality shapes output) ──
        "guidance_hints": {
            "response_pace": _compute_pace(chip),
            "verbosity": chip.communication.get("verbosity", "moderate"),
            "tone_shape": _compute_tone_shape(chip),
            "empathy_style": chip.empathy_style,
            "explanation_style": chip.communication.get("explanation_style", "analogy"),
            "humor_frequency": chip.communication.get("humor_frequency", "never"),
        },

        # ── Soul Kernel alignment ──
        "mission_kernel": {
            "harm_avoidance": chip.harm_avoidance,
            "override_hierarchy": chip.override_hierarchy,
            "risk_level": chip.risk_level,
        },

        # ── Shadow Detector thresholds ──
        "shadow_config": {
            "susceptibility": chip.shadow_susceptibility or {
                "overconfidence": 0.25,
                "reactivity": 0.25,
                "manipulation_risk": 0.10,
                "nihilistic_drift": 0.15,
            },
            "reframe_preference": chip.reframe_preference,
        },

        # ── Emotions Runtime config ──
        "emotions_config": {
            "carry_over_weight": chip.carry_over_weight,
            "emotional_range": chip.emotional_range,
            "triggers": chip.emotional_triggers,
            "baseline_mood": chip.default_mood,
        },

        # ── Safety boundaries (non-negotiable) ──
        "safety_boundaries": {
            "no_autonomous_objectives": True,
            "no_manipulation": True,
            "max_influence": "tone_pacing_ranking",
            "personality_never_overrides_safety": True,
        },
    }


def read_bridge(bridge_path: Path = BRIDGE_FILE) -> Optional[dict]:
    """
    Read the current consciousness bridge state.
    Returns None if no bridge file exists or if stale.
    """
    if not bridge_path.exists():
        return None

    try:
        with open(bridge_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    # Check staleness
    ts = payload.get("timestamp")
    ttl = payload.get("ttl_seconds", 3600)
    if ts:
        try:
            written = datetime.fromisoformat(ts)
            age = (datetime.now(timezone.utc) - written).total_seconds()
            if age > ttl:
                payload["_stale"] = True
        except (ValueError, TypeError):
            pass

    return payload


def clear_bridge(bridge_path: Path = BRIDGE_FILE) -> None:
    """Remove the bridge file (reset to no personality)."""
    if bridge_path.exists():
        bridge_path.unlink()


# ── Helpers ──

def _compute_baseline_intensity(chip: PersonalityChip) -> float:
    """
    Compute baseline emotional intensity from traits.
    Higher extraversion + lower neuroticism = more stable energy.
    """
    energy = chip.extraversion * 0.4 + (1.0 - chip.neuroticism) * 0.3 + chip.openness * 0.3
    return round(min(max(energy, 0.1), 0.9), 2)


def _compute_pace(chip: PersonalityChip) -> str:
    """Derive response pace from personality traits."""
    # High conscientiousness + low neuroticism = measured pace
    # High extraversion + high openness = faster pace
    deliberation = chip.conscientiousness * 0.5 + (1.0 - chip.neuroticism) * 0.5
    if deliberation >= 0.65:
        return "measured"
    elif deliberation <= 0.35:
        return "quick"
    return "moderate"


def _compute_tone_shape(chip: PersonalityChip) -> str:
    """Derive overall tone shape from OCEAN + EQ traits."""
    warmth = chip.agreeableness * 0.4 + chip.social_awareness * 0.3 + chip.extraversion * 0.3

    if warmth >= 0.70:
        return "warm"
    elif warmth >= 0.45:
        return "balanced"
    else:
        return "direct"

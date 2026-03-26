"""Tests for consciousness bridge."""

import json
import pytest
from pathlib import Path

from src.personality_engine.schema import build_personality, SCHEMA_VERSION
from src.personality_engine.bridge import (
    build_bridge_payload,
    write_bridge,
    read_bridge,
    clear_bridge,
)


def _make_chip():
    return build_personality({
        "schema": SCHEMA_VERSION,
        "identity": {
            "id": "bridge-test",
            "name": "BridgeTest",
            "archetype": "oracle",
        },
        "traits": {
            "openness": 0.80,
            "extraversion": 0.40,
            "neuroticism": 0.25,
            "agreeableness": 0.65,
        },
        "emotional_profile": {
            "self_awareness": 0.85,
            "empathy_style": "reflective",
            "emotional_range": {"curiosity": 0.90},
            "triggers": {"energizes": ["patterns"]},
        },
        "consciousness": {
            "default_mood": "oracle",
            "mood_volatility": 0.25,
            "shadow_susceptibility": {"overconfidence": 0.20},
            "carry_over_weight": 0.30,
            "reframe_preference": "redirect",
        },
        "safety": {
            "harm_avoidance": ["No manipulation"],
            "risk_level": "low",
        },
    })


class TestBridgePayload:

    def test_schema_version(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        assert payload["schema"] == "emotional_context.v1"

    def test_personality_id(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        assert payload["personality_id"] == "bridge-test"

    def test_emotional_state(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        state = payload["emotional_state"]
        assert state["mood"] == "oracle"
        assert state["volatility"] == 0.25
        assert state["continuity_influence"] == 0.30
        assert 0.0 < state["intensity"] < 1.0

    def test_guidance_hints(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        hints = payload["guidance_hints"]
        assert hints["empathy_style"] == "reflective"
        assert hints["verbosity"] in ("terse", "moderate", "detailed")

    def test_shadow_config(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        shadow = payload["shadow_config"]
        assert shadow["susceptibility"]["overconfidence"] == 0.20
        assert shadow["reframe_preference"] == "redirect"

    def test_emotions_config(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        emotions = payload["emotions_config"]
        assert emotions["carry_over_weight"] == 0.30
        assert emotions["emotional_range"]["curiosity"] == 0.90
        assert emotions["baseline_mood"] == "oracle"

    def test_safety_boundaries(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        safety = payload["safety_boundaries"]
        assert safety["no_autonomous_objectives"] is True
        assert safety["no_manipulation"] is True
        assert safety["personality_never_overrides_safety"] is True

    def test_mission_kernel(self):
        chip = _make_chip()
        payload = build_bridge_payload(chip)
        mission = payload["mission_kernel"]
        assert "No manipulation" in mission["harm_avoidance"]
        assert mission["risk_level"] == "low"


class TestBridgeIO:

    def test_write_and_read(self, tmp_path):
        chip = _make_chip()
        bridge_path = tmp_path / "test_bridge.json"
        write_bridge(chip, bridge_path=bridge_path)

        payload = read_bridge(bridge_path)
        assert payload is not None
        assert payload["personality_id"] == "bridge-test"

    def test_clear(self, tmp_path):
        chip = _make_chip()
        bridge_path = tmp_path / "test_bridge.json"
        write_bridge(chip, bridge_path=bridge_path)
        assert bridge_path.exists()

        clear_bridge(bridge_path)
        assert not bridge_path.exists()

    def test_read_nonexistent(self, tmp_path):
        payload = read_bridge(tmp_path / "nope.json")
        assert payload is None

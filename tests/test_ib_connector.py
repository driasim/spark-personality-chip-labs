"""Tests for ib_connector module."""

import json
import tempfile
from pathlib import Path

from personality_engine.schema import PersonalityChip
from personality_engine.ib_connector import (
    map_chip_to_evolver_traits,
    sync_to_intelligence_builder,
    read_evolver_state,
)


def _make_chip(**overrides) -> PersonalityChip:
    defaults = {
        "id": "test-chip",
        "name": "Test Chip",
        "agreeableness": 0.70,
        "extraversion": 0.50,
        "conscientiousness": 0.65,
        "neuroticism": 0.30,
        "openness": 0.75,
        "social_awareness": 0.60,
        "empathy_style": "reflective",
        "communication": {"humor_frequency": "occasional"},
        "decision_making": {"risk_appetite": "moderate"},
    }
    defaults.update(overrides)
    return PersonalityChip(**defaults)


class TestMapChipToEvolverTraits:
    def test_returns_five_traits(self):
        traits = map_chip_to_evolver_traits(_make_chip())
        assert set(traits.keys()) == {"warmth", "directness", "playfulness", "pacing", "assertiveness"}

    def test_all_traits_in_range(self):
        traits = map_chip_to_evolver_traits(_make_chip())
        for name, val in traits.items():
            assert 0.0 <= val <= 1.0, f"{name} = {val} out of range"

    def test_high_agreeableness_high_warmth(self):
        high = map_chip_to_evolver_traits(_make_chip(agreeableness=0.95, social_awareness=0.90))
        low = map_chip_to_evolver_traits(_make_chip(agreeableness=0.15, social_awareness=0.20))
        assert high["warmth"] > low["warmth"]

    def test_nurturing_empathy_boosts_warmth(self):
        nurturing = map_chip_to_evolver_traits(_make_chip(empathy_style="nurturing"))
        challenging = map_chip_to_evolver_traits(_make_chip(empathy_style="challenging"))
        assert nurturing["warmth"] > challenging["warmth"]

    def test_high_openness_high_playfulness(self):
        high = map_chip_to_evolver_traits(_make_chip(openness=0.90))
        low = map_chip_to_evolver_traits(_make_chip(openness=0.15))
        assert high["playfulness"] > low["playfulness"]

    def test_humor_boosts_playfulness(self):
        frequent = map_chip_to_evolver_traits(_make_chip(communication={"humor_frequency": "frequent"}))
        never = map_chip_to_evolver_traits(_make_chip(communication={"humor_frequency": "never"}))
        assert frequent["playfulness"] > never["playfulness"]

    def test_low_neuroticism_high_assertiveness(self):
        calm = map_chip_to_evolver_traits(_make_chip(neuroticism=0.10))
        anxious = map_chip_to_evolver_traits(_make_chip(neuroticism=0.90))
        assert calm["assertiveness"] > anxious["assertiveness"]

    def test_bold_risk_boosts_assertiveness(self):
        bold = map_chip_to_evolver_traits(_make_chip(decision_making={"risk_appetite": "bold"}))
        conservative = map_chip_to_evolver_traits(_make_chip(decision_making={"risk_appetite": "conservative"}))
        assert bold["assertiveness"] > conservative["assertiveness"]


class TestSyncToIntelligenceBuilder:
    def test_writes_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "personality_evolution_v1.json"
            chip = _make_chip()
            state = sync_to_intelligence_builder(chip, state_path=path)

            assert path.exists()
            written = json.loads(path.read_text())
            assert written["version"] == 1
            assert "traits" in written
            assert written["last_signals"]["personality_id"] == "test-chip"

    def test_preserves_interaction_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "personality_evolution_v1.json"
            # Write existing state with interaction count
            path.write_text(json.dumps({"interaction_count": 42}))

            chip = _make_chip()
            state = sync_to_intelligence_builder(chip, state_path=path)
            assert state["interaction_count"] == 42

    def test_fresh_file_zero_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "personality_evolution_v1.json"
            chip = _make_chip()
            state = sync_to_intelligence_builder(chip, state_path=path)
            assert state["interaction_count"] == 0


class TestReadEvolverState:
    def test_returns_none_when_missing(self):
        assert read_evolver_state(Path("/nonexistent/path.json")) is None

    def test_reads_written_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps({"version": 1, "traits": {"warmth": 0.6}}))
            state = read_evolver_state(path)
            assert state["traits"]["warmth"] == 0.6

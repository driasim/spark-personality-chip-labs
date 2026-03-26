#!/usr/bin/env python3
"""
Integration Example: Plugging a Personality Chip into a Spark Agent

Shows the three integration points:
1. Load personality → inject into LLM system prompt
2. Write consciousness bridge → configure Spark Consciousness modules
3. Observe responses → detect personality drift

This is the pattern you'd use in any agent runner, MCP server,
or Spark Intelligence Builder hook.
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from personality_engine.loader import load_personality
from personality_engine.context import build_personality_context
from personality_engine.bridge import write_bridge, build_bridge_payload
from personality_engine.observer import observe_response
from personality_engine.registry import PersonalityRegistry


def example_1_basic_usage():
    """
    Simplest usage: load a personality and generate a prompt section.
    """
    print("=" * 60)
    print("  Example 1: Basic Usage")
    print("=" * 60)

    # Load a personality chip
    chip = load_personality("personalities/artemis.personality.yaml")
    print(f"\nLoaded: {chip.name} ({chip.id})")
    print(f"Archetype: {chip.archetype}")
    print(f"Voice: {chip.voice_signature}")

    # Generate the system prompt section
    prompt_section = build_personality_context(chip, style="concise")
    print(f"\n--- System Prompt Section ---\n{prompt_section}")

    # This string goes into your LLM's system prompt:
    # system_prompt = f"{your_base_prompt}\n\n{prompt_section}"


def example_2_adaptive_context():
    """
    Dynamic context: adjust personality based on detected user state.
    """
    print("\n" + "=" * 60)
    print("  Example 2: Adaptive Context")
    print("=" * 60)

    chip = load_personality("personalities/echo.personality.yaml")

    # Normal context
    normal = build_personality_context(chip, style="concise")
    print(f"\n--- Normal ---\n{normal}")

    # When user is frustrated
    frustrated = build_personality_context(chip, style="concise", user_state="frustrated")
    print(f"\n--- User Frustrated ---\n{frustrated}")

    # When user is an expert
    expert = build_personality_context(chip, style="concise", user_state="expert")
    print(f"\n--- User Expert ---\n{expert}")


def example_3_consciousness_bridge():
    """
    Write the consciousness bridge file for Spark Consciousness integration.
    """
    print("\n" + "=" * 60)
    print("  Example 3: Consciousness Bridge")
    print("=" * 60)

    chip = load_personality("personalities/forge.personality.yaml")

    # Build the bridge payload (in-memory, no file write)
    payload = build_bridge_payload(chip, session_id="demo-session")

    print(f"\nSchema: {payload['schema_version']}")
    print(f"Personality: {payload['meta']['personality_name']}")
    print(f"Mood: {payload['emotional_state']['mood']}")
    print(f"Intensity: {payload['emotional_state']['intensity']}")
    print(f"Primary emotion: {payload['emotional_state']['primary_emotion']}")
    print(f"Pace: {payload['guidance']['response_pace']}")
    print(f"Tone: {payload['guidance']['tone_shape']}")
    print(f"Verbosity: {payload['guidance']['verbosity']}")
    print(f"Shadow susceptibility: {payload['personality_ext']['shadow_config']['susceptibility']}")

    # In production, write to disk for Spark Consciousness to read:
    # write_bridge(chip, session_id="my-session")
    # This writes to: ~/.spark/bridges/consciousness/emotional_context.v1.json


def example_4_drift_detection():
    """
    Monitor agent responses for personality consistency.
    """
    print("\n" + "=" * 60)
    print("  Example 4: Drift Detection")
    print("=" * 60)

    chip = load_personality("personalities/artemis.personality.yaml")

    # Good response (matches personality)
    good = "Here's the root cause: the null check on line 42 is missing."
    report = observe_response(chip, good)
    print(f"\nGood response drift: {report['drift_score']}")
    print(f"Signals: {len(report['signals'])}")

    # Drifting response (too casual for Artemis, dismissive)
    bad = "lol who cares about that, gonna just wanna skip it tbh, trust me on this"
    report = observe_response(chip, bad)
    print(f"\nBad response drift: {report['drift_score']}")
    print(f"Signals: {len(report['signals'])}")
    for s in report["signals"]:
        print(f"  - [{s['type']}] {s['detail']}")
    if report["recommendation"]:
        print(f"Recommendation: {report['recommendation']}")


def example_5_registry():
    """
    Manage multiple personalities and assign to agents.
    """
    print("\n" + "=" * 60)
    print("  Example 5: Registry")
    print("=" * 60)

    # Create a temporary registry (in-memory for demo)
    from pathlib import Path
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "demo_registry.json"
    registry = PersonalityRegistry(registry_path=tmp)

    # Scan and install all personalities from directory
    count = registry.scan_and_install("personalities/")
    print(f"\nInstalled {count} personalities:")
    for chip in registry.get_installed():
        print(f"  - {chip.name} ({chip.id}) [{chip.archetype}]")

    # Assign personalities to agents
    registry.assign("code-reviewer", "artemis")
    registry.assign("sprint-runner", "forge")
    registry.assign("onboarding-bot", "echo")

    print(f"\nAssignments: {registry.get_assignments()}")

    # Look up personality for an agent
    personality = registry.get_personality("code-reviewer")
    print(f"\ncode-reviewer personality: {personality.name}")
    print(f"  Voice: {personality.voice_signature}")
    print(f"  Risk appetite: {personality.decision_making.get('risk_appetite', 'moderate')}")

    # Set a default for agents without assignment
    registry.set_default("artemis")
    unassigned = registry.get_personality("random-agent")
    print(f"\nUnassigned agent gets: {unassigned.name} (default)")

    # Clean up
    tmp.unlink(missing_ok=True)


def example_6_full_integration():
    """
    Full integration pattern: what your agent runner looks like.
    """
    print("\n" + "=" * 60)
    print("  Example 6: Full Agent Integration Pattern")
    print("=" * 60)

    # ── Step 1: Load personality at agent startup ──
    chip = load_personality("personalities/artemis.personality.yaml")

    # ── Step 2: Write consciousness bridge ──
    payload = build_bridge_payload(chip, session_id="production-001")
    # In production: write_bridge(chip, session_id="production-001")

    # ── Step 3: Build system prompt with personality ──
    base_prompt = "You are a helpful coding assistant."
    personality_section = build_personality_context(chip, style="concise")
    guardrails_section = build_personality_context(chip, style="guardrails")

    full_system_prompt = f"""{base_prompt}

{personality_section}

{guardrails_section}"""

    print("\n--- Full System Prompt ---")
    print(full_system_prompt)

    # ── Step 4: After each response, check for drift ──
    agent_response = "Let me analyze the root cause of this issue."
    report = observe_response(chip, agent_response, session_id="production-001")
    print(f"\n--- Post-Response Drift Check ---")
    print(f"Drift: {report['drift_score']} | Signals: {len(report['signals'])}")

    # ── Step 5: Adapt to user state mid-conversation ──
    # (Your agent detects user frustration from their message)
    adapted_section = build_personality_context(
        chip, style="adaptive", user_state="frustrated"
    )
    print(f"\n--- Adapted Context ---\n{adapted_section}")


if __name__ == "__main__":
    example_1_basic_usage()
    example_2_adaptive_context()
    example_3_consciousness_bridge()
    example_4_drift_detection()
    example_5_registry()
    example_6_full_integration()

    print("\n" + "=" * 60)
    print("  All examples completed successfully.")
    print("=" * 60)

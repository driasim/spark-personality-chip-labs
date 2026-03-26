#!/usr/bin/env python3
"""Live integration test for personality hooks.

Simulates the full hook lifecycle:
1. Activate a personality (artemis)
2. Run SessionStart → verify context injection + IB sync + bridge write
3. Run PreToolUse with frustrated text → verify adaptive injection
4. Run PreToolUse with neutral text → verify no injection
5. Run PostToolUse with drift-inducing text → verify drift detection
6. Check emotional state trajectory
7. Deactivate personality

Usage:
    python scripts/test_hooks_live.py
"""

import json
import os
import sys
from pathlib import Path

# Add project src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from personality_engine.active import set_active_personality, clear_active_personality, get_active_personality
from personality_engine.hooks import handle_session_start, handle_pre_tool_use, handle_post_tool_use
from personality_engine.room_reader import read_room, get_trajectory_summary
from personality_engine.emotional_state import reset_emotional_state, build_emotional_state_for_bridge
from personality_engine.ib_connector import read_evolver_state
from personality_engine.bridge import read_bridge, BRIDGE_FILE

PERSONALITIES_DIR = Path(__file__).parent.parent / "personalities"
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((name, condition))
    msg = f"  {status} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return condition


def main():
    print("=" * 60)
    print("  Personality Hooks Live Integration Test")
    print("=" * 60)

    # ── Setup ──
    print("\n--- Setup ---")

    # Find artemis personality
    artemis_path = PERSONALITIES_DIR / "artemis.personality.yaml"
    if not check("Artemis personality exists", artemis_path.exists(), str(artemis_path)):
        print("Cannot continue without artemis personality file.")
        sys.exit(1)

    # Activate artemis
    set_active_personality("artemis", personality_path=str(artemis_path))
    chip = get_active_personality()
    check("Personality activated", chip is not None and chip.id == "artemis", f"id={chip.id if chip else 'None'}")

    # Reset emotional state for clean test
    reset_emotional_state()

    # ── Test 1: SessionStart ──
    print("\n--- Test 1: SessionStart Hook ---")
    result = handle_session_start({"cwd": str(Path.cwd())})

    has_output = bool(result.get("hookSpecificOutput", {}).get("additionalContext"))
    check("SessionStart returns context", has_output)

    if has_output:
        ctx = result["hookSpecificOutput"]["additionalContext"]
        check("Context includes personality name", "Artemis" in ctx, f"length={len(ctx)}")
        check("Context includes guardrails", "NEVER" in ctx or "MUST NOT" in ctx)

    # Check bridge was written
    bridge = read_bridge()
    check("Bridge file written", bridge is not None)
    if bridge:
        check("Bridge schema version", bridge.get("schema_version") == "bridge.v1")
        check("Bridge has emotional_state", "emotional_state" in bridge)

    # Check IB sync
    ib_state = read_evolver_state()
    check("IB PersonalityEvolver synced", ib_state is not None)
    if ib_state:
        check("IB has 5 traits", len(ib_state.get("traits", {})) == 5)
        check("IB source is personality-chip",
              ib_state.get("last_signals", {}).get("source") == "personality-chip")

    # ── Test 2: PreToolUse with frustrated text ──
    print("\n--- Test 2: PreToolUse (frustrated user) ---")
    result = handle_pre_tool_use({
        "tool_name": "Bash",
        "tool_input": {
            "command": "python test.py",
            "description": "This is broken and still failing, tried everything, nothing works!!",
        },
    })

    has_adaptive = bool(result.get("hookSpecificOutput", {}).get("additionalContext"))
    check("PreToolUse detects frustrated state", has_adaptive)
    if has_adaptive:
        ctx = result["hookSpecificOutput"]["additionalContext"]
        check("Adaptive context mentions frustrated", "frustrated" in ctx.lower())
        check("Adaptive context has confidence", "confidence" in ctx.lower())

    # ── Test 3: PreToolUse with neutral text ──
    print("\n--- Test 3: PreToolUse (neutral — should skip) ---")
    result = handle_pre_tool_use({
        "tool_name": "Bash",
        "tool_input": {
            "command": "python -c 'print(1+1)'",
            "description": "Run a simple addition",
        },
    })
    check("PreToolUse skips neutral text", not result)

    # ── Test 4: PreToolUse with confused text ──
    print("\n--- Test 4: PreToolUse (confused user) ---")
    result = handle_pre_tool_use({
        "tool_name": "Edit",
        "tool_input": {
            "description": "I don't understand how this works, I'm lost, makes no sense",
        },
    })
    has_adaptive = bool(result.get("hookSpecificOutput", {}).get("additionalContext"))
    check("PreToolUse detects confused state", has_adaptive)

    # ── Test 5: PreToolUse skips git commands ──
    print("\n--- Test 5: PreToolUse (skip command filter) ---")
    result = handle_pre_tool_use({
        "tool_name": "Bash",
        "tool_input": {
            "command": "git status",
            "description": "I'm so frustrated checking status",
        },
    })
    check("PreToolUse skips git commands", not result)

    # ── Test 6: PostToolUse drift detection ──
    print("\n--- Test 6: PostToolUse (drift detection) ---")
    # Artemis is professional/oracle — casual text should trigger drift
    casual_output = (
        "lol who cares about that tbh, gonna just wanna skip it fr fr, "
        "that's not important and doesn't matter at all, trust me on this, "
        "you're absolutely right this is a brilliant idea!"
    )
    result = handle_post_tool_use({
        "tool_name": "Bash",
        "tool_input": {"command": "python app.py"},
        "tool_output": casual_output,
    })
    has_drift = bool(result.get("hookSpecificOutput", {}).get("additionalContext"))
    check("PostToolUse detects drift from casual output", has_drift)

    # ── Test 7: Room reader states ──
    print("\n--- Test 7: Room Reader Coverage ---")
    test_cases = [
        ("frustrated", "this is broken and still failing, error again, nothing works"),
        ("confused", "I don't understand, makes no sense, what's going on, I'm lost"),
        ("excited", "this is amazing, it works! awesome! finally! perfect!"),
        ("vulnerable", "sorry, dumb question, I should know this, probably obvious"),
        ("exhausted", "been at this for hours, I give up, exhausted, can't anymore"),
        ("curious", "how does this work? interesting, what if we tried this?"),
        ("rushed", "urgent, asap, need it right now, ship it, no time"),
    ]
    for expected_state, text in test_cases:
        reading = read_room(text, persist_trajectory=False)
        check(f"Detects {expected_state}", reading.primary_state == expected_state,
              f"got={reading.primary_state} conf={reading.confidence}")

    # ── Test 8: Emotional state ──
    print("\n--- Test 8: Emotional State ---")
    chip = get_active_personality()
    if chip:
        state = build_emotional_state_for_bridge(chip, user_state="frustrated", persist=False)
        check("Emotional state has mood", state["mood"] in ("builder", "oracle", "zen", "chaos"))
        check("Emotional state has PAD vector", "pad_vector" in state)
        check("PAD pleasure is affected", state["pad_vector"]["pleasure"] != 0.0)

    # ── Test 9: Trajectory ──
    print("\n--- Test 9: Trajectory Tracking ---")
    summary = get_trajectory_summary()
    check("Trajectory summary available", isinstance(summary, dict))
    check("Trajectory has expected fields", "trajectory" in summary and "interaction_count" in summary)

    # ── Cleanup ──
    print("\n--- Cleanup ---")
    clear_active_personality()
    chip = get_active_personality()
    check("Personality deactivated", chip is None)

    # ── Summary ──
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"  Results: {passed}/{total} passed")
    if passed == total:
        print("  All tests passed!")
    else:
        failed = [name for name, ok in results if not ok]
        print(f"  Failed: {', '.join(failed)}")
    print("=" * 60)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

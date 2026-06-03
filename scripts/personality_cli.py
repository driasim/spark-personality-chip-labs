#!/usr/bin/env python3
"""Personality Chip CLI

Simple CLI for activating/deactivating personality chips.

Usage:
    python scripts/personality_cli.py list                # Show available personalities
    python scripts/personality_cli.py activate artemis     # Set active personality
    python scripts/personality_cli.py deactivate           # Clear active personality
    python scripts/personality_cli.py status               # Show current state
    python scripts/personality_cli.py bridge                # Show bridge payload
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from personality_engine.loader import load_all_personalities, load_personality
from personality_engine.active import (
    get_active_personality_id,
    get_active_personality,
    set_active_personality,
    clear_active_personality,
    ACTIVE_FILE,
)
from personality_engine.bridge import build_bridge_payload, read_bridge, BRIDGE_FILE


def cmd_list(emit=None):
    """List all available personality chips."""
    chips = load_all_personalities()
    if not chips:
        if emit:
            emit({"chips": [], "count": 0}, "No personality chips found.\nPlace .personality.yaml files in personalities/ or ~/.spark/chips/personality/")
        else:
            print("No personality chips found.")
            print("Place .personality.yaml files in personalities/ or ~/.spark/chips/personality/")
        return

    text = [f"Found {len(chips)} personality chip(s):\n"]
    data = []
    for chip in chips:
        chip_data = {"id": chip.id, "name": chip.name, "archetype": chip.archetype}
        text.append(f"  {chip.id}")
        text.append(f"    Name:      {chip.name}")
        text.append(f"    Archetype: {chip.archetype}")
        if chip.voice_signature:
            chip_data["voice_signature"] = chip.voice_signature
            text.append(f"    Voice:     {chip.voice_signature}")
        if chip.tagline:
            chip_data["tagline"] = chip.tagline
            text.append(f"    Tagline:   {chip.tagline}")
        text.append("")
        data.append(chip_data)

    if emit:
        emit({"chips": data, "count": len(data)}, "\n".join(text))
    else:
        print("\n".join(text))


def cmd_activate(personality_id: str, emit=None):
    """Activate a personality chip."""
    # Try to find the personality first
    chips = load_all_personalities()
    match = None
    for chip in chips:
        if chip.id == personality_id:
            match = chip
            break

    if not match:
        msg = f"Personality '{personality_id}' not found."
        available = [chip.id for chip in chips]
        if emit:
            emit({"error": "not_found", "personality_id": personality_id, "available": available}, msg + "\nAvailable personalities:\n" + "\n".join(f"  - {cid}" for cid in available))
        else:
            print(msg)
            print("Available personalities:")
            for chip in chips:
                print(f"  - {chip.id}")
        sys.exit(1)

    set_active_personality(personality_id)
    data = {"activated": personality_id, "name": match.name, "archetype": match.archetype}
    text = f"Activated personality: {match.name} ({match.id})\n  Archetype: {match.archetype}"
    if match.voice_signature:
        data["voice_signature"] = match.voice_signature
        text += f"\n  Voice: {match.voice_signature}"
    text += f"\n\nWritten to: {ACTIVE_FILE}"
    data["active_file"] = str(ACTIVE_FILE)
    if emit:
        emit(data, text)
    else:
        print(text)


def cmd_deactivate(emit=None):
    """Clear the active personality."""
    current = get_active_personality_id()
    clear_active_personality()
    data = {"deactivated": current}
    if current:
        text = f"Deactivated personality: {current}"
    else:
        text = "No personality was active."
    data["was_active"] = bool(current)
    if emit:
        emit(data, text)
    else:
        print(text)


def cmd_status(emit=None):
    """Show current personality state."""
    pid = get_active_personality_id()
    data = {"active_personality_id": pid, "active_file": str(ACTIVE_FILE), "bridge_file": str(BRIDGE_FILE)}
    text = ["Personality Chip Status", "=" * 40]

    if pid:
        text.append(f"Active personality: {pid}")
        chip = get_active_personality()
        if chip:
            text.append(f"  Name:      {chip.name}")
            text.append(f"  Archetype: {chip.archetype}")
            data["name"] = chip.name
            data["archetype"] = chip.archetype
            if chip.voice_signature:
                text.append(f"  Voice:     {chip.voice_signature}")
                data["voice_signature"] = chip.voice_signature
        else:
            text.append(f"  (could not load personality '{pid}')")
    else:
        text.append("Active personality: None")

    text.append(f"\nActive file: {ACTIVE_FILE}")
    text.append(f"  Exists: {ACTIVE_FILE.exists()}")
    data["active_file_exists"] = ACTIVE_FILE.exists()

    text.append(f"\nBridge file: {BRIDGE_FILE}")
    text.append(f"  Exists: {BRIDGE_FILE.exists()}")
    data["bridge_file_exists"] = BRIDGE_FILE.exists()

    bridge = read_bridge()
    if bridge:
        stale = bridge.pop("_stale", False)
        text.append(f"  Schema: {bridge.get('schema_version', 'unknown')}")
        text.append(f"  Source: {bridge.get('source', 'unknown')}")
        meta = bridge.get("meta", {})
        text.append(f"  Personality: {meta.get('personality_name', 'unknown')}")
        text.append(f"  Stale: {stale}")
        data["bridge"] = {"schema": bridge.get("schema_version"), "source": bridge.get("source"), "personality": meta.get("personality_name"), "stale": stale}

    if emit:
        emit(data, "\n".join(text))
    else:
        print("\n".join(text))


def cmd_bridge(emit=None):
    """Show the current bridge payload."""
    chip = get_active_personality()
    if not chip:
        if emit:
            emit({"error": "no_active_personality"}, "No active personality. Use 'activate' first.")
        else:
            print("No active personality. Use 'activate' first.")
        sys.exit(1)

    payload = build_bridge_payload(chip)
    text = json.dumps(payload, indent=2)
    if emit:
        emit(payload, text)
    else:
        print(text)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Personality Chip CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["list", "activate", "deactivate", "status", "bridge"],
        help="Command to run",
    )
    parser.add_argument(
        "personality_id",
        nargs="?",
        default=None,
        help="Personality ID (required for activate)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="Output in JSON format (machine-readable)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write output to file instead of stdout",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    command = args.command

    def emit(data: dict, text_output: str):
        if args.json_mode:
            output = json.dumps(data, indent=2)
        else:
            output = text_output
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)

    if command == "list":
        cmd_list(emit)
    elif command == "activate":
        if not args.personality_id:
            print("Usage: personality_cli.py activate <personality_id>")
            sys.exit(1)
        cmd_activate(args.personality_id, emit)
    elif command == "deactivate":
        cmd_deactivate(emit)
    elif command == "status":
        cmd_status(emit)
    elif command == "bridge":
        cmd_bridge(emit)
    else:
        print(f"Unknown command: {command}")
        print("Available: list, activate, deactivate, status, bridge")
        sys.exit(1)


if __name__ == "__main__":
    main()

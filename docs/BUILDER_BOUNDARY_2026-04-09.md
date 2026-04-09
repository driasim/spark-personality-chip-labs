# Personality Chip x Builder Boundary

This repo is the source and import seam for persona, not the live owner of Telegram style mutation.

## This Repo Owns

- personality chip files
- chip schema and validation
- active personality resolution
- the Builder-facing `personality` hook
- conversion of chip identity/style into a Builder import payload

## Builder Owns After Import

Once Builder imports the personality hook result, `spark-intelligence-builder` owns the live conversational persona state:

- Telegram-visible style
- style training and feedback
- style presets
- style scoring/examples/compare
- undo
- savepoints and restore

Those systems are intentionally Builder-native. They are not mirrored back into the chip files during normal Telegram use.

## Why

The personality chip should stay portable and reusable.

Builder is the operator-facing runtime where the agent is actually felt. That is the right layer for:

- real-time conversation shaping
- per-agent live tuning
- rapid Telegram dogfooding

## Current Relationship

Use this mental model:

- personality chip = baseline persona package
- Builder = living conversational personality runtime
- voice chip = speech I/O around the Builder-owned personality

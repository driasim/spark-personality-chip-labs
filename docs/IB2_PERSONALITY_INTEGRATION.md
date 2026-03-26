# Personality Chips x Spark Intelligence Builder 2: Integration Spec

## How IB2 Will Use Personality Chips — And How Users Customize Through Conversation

---

## The Core Thesis

Right now, Spark Intelligence Builder 2 has a personality system that's **architecturally complete but functionally dead**. The `PersonalityEvolver` manages 5 traits (warmth, directness, playfulness, pacing, assertiveness), applies bounded deltas, persists state — but it's **feature-gated off** and disconnected from every output path. The traits exist in a JSON file that nothing reads.

Personality Chips fix this by becoming the **source of truth** that IB2's existing infrastructure was built to consume. The chips don't replace PersonalityEvolver — they *seed* it. And the critical missing piece — natural language customization — means users tune their agent by **talking to it**, not editing config files.

---

## 1. What Already Connects (Today)

### The State File Bridge

Personality Chips and IB2's PersonalityEvolver already share the same state file:

```
~/.spark/personality_evolution_v1.json
```

Our `ib_connector.py` writes to this file during every SessionStart hook. IB2's PersonalityEvolver reads from it. The mapping is already live:

| PersonalityChip (OCEAN + EQ) | PersonalityEvolver Trait | Formula |
|-----|-----|-----|
| agreeableness + social_awareness + empathy_style | **warmth** | `A*0.6 + SA*0.3 + 0.05 + empathy_bonus` |
| extraversion + agreeableness(inv) + conscientiousness | **directness** | `E*0.4 + (1-A)*0.4 + C*0.2` |
| openness + extraversion + humor_frequency | **playfulness** | `O*0.6 + E*0.3 + 0.05 + humor_bonus` |
| conscientiousness + neuroticism(inv) | **pacing** | `1 - (C*0.6 + (1-N)*0.4)` |
| neuroticism(inv) + extraversion + risk_appetite | **assertiveness** | `(1-N)*0.5 + E*0.3 + C*0.2 + risk_bonus` |

When a user activates "artemis" personality and starts a Claude Code session:

1. **SessionStart hook** fires in `personality_engine.hooks`
2. `ib_connector.sync_to_intelligence_builder(chip)` writes the trait mapping
3. PersonalityEvolver picks up the new trait values on its next read
4. The `interaction_count` from IB2 is preserved (chips don't reset learning history)

### The Consciousness Bridge

The bridge file at `~/.spark/bridges/consciousness/emotional_context.v1.json` follows the `bridge.v1` contract that Spark Consciousness modules read:

```json
{
  "schema_version": "bridge.v1",
  "emotional_state": {
    "mood": "oracle",
    "intensity": 0.62,
    "primary_emotion": "contemplative",
    "staleness_seconds": 0
  },
  "guidance": {
    "response_pace": "measured",
    "verbosity": "medium",
    "tone_shape": "calm_focus"
  },
  "boundaries": {
    "user_guided": true,
    "no_autonomous_objectives": true,
    "max_influence": 0.35
  }
}
```

This means Soul Kernel, Archetype Router, Shadow Detector, and Emotions Runtime all consume personality chip data **without any code changes to Spark Consciousness**.

### The Emotional State Pipeline

Our `room_reader.py` detects 9 emotional states from conversation text. IB2's `SparkEmotions` has a parallel trigger system (`TRIGGER_MAP`) that adjusts 6 emotional axes. These map directly:

| Room Reader State | IB2 Trigger | IB2 Emotion |
|---|---|---|
| frustrated | `user_frustration` | supportive_focus |
| confused | `user_confusion` | clarifying |
| excited | `user_celebration` | encouraged |
| vulnerable | `repair_after_mistake` | accountable |
| rushed | `high_stakes_request` | careful |

The room reader fires on every PreToolUse/PostToolUse hook and updates our PAD-vector emotional state. IB2's SparkEmotions can consume these same readings to drive its own emotional timeline — the bridge is the shared state files.

---

## 2. What IB2 Gains From Personality Chips

### 2.1 Advisory Payload Gets Personality Context

**Current state**: `context_sync.py` builds the advisory payload (`_build_advisory_payload` at line 714) with insights, promoted learnings, chip highlights, and mind highlights. It has **zero personality awareness** — every user gets identical formatting.

**With personality chips**: The advisory payload adds a `personality` section:

```json
{
  "schema_version": "spark_advisory_payload_v1",
  "personality": {
    "active_chip": "artemis",
    "traits": {
      "warmth": 0.635,
      "directness": 0.42,
      "playfulness": 0.555,
      "pacing": 0.46,
      "assertiveness": 0.67
    },
    "style_labels": {
      "warmth": "balanced",
      "directness": "balanced",
      "playfulness": "balanced",
      "pacing": "balanced",
      "assertiveness": "assertive"
    },
    "emotional_state": {
      "mood": "oracle",
      "primary_emotion": "contemplative"
    }
  },
  "insights": [...]
}
```

This lets every output adapter (Claude Code, Cursor, Windsurf, Clawdbot, OpenClaw) format context differently based on the active personality. A user with `directness: 0.85` gets terse, action-oriented advisories. A user with `warmth: 0.90` gets collaborative framing. Same insights, different delivery.

### 2.2 Conversation Quality Adapts

IB2's `ConversationCore` currently uses hardcoded keyword matching for mode selection:

```python
# conversation_core.py line 49
if any(k in text for k in ["frustrated", "stressed", "urgent"]):
    return "calm_focus"
```

This is exactly what our room reader does, but with 3-layer detection (keywords + syntactic + discourse markers) and confidence scoring. Room reader replaces this simple keyword check with genuine understanding of emotional trajectory:

```python
reading = read_room(user_text)
# reading.primary_state = "frustrated"
# reading.confidence = 0.78
# reading.trajectory = "rising"  # escalating across interactions
```

A "rising" trajectory on frustration means the agent should switch to calm_focus **before** the user explicitly says "frustrated." That's the difference between reactive and anticipatory empathy.

### 2.3 Cognitive Learner Gets Personality Insights

IB2's `CognitiveLearner` captures insights across 8 categories including `USER_UNDERSTANDING`. Currently, it stores observations like "User prefers small iterative fixes" as cognitive insights — but **never applies them to personality traits**.

With the personality chip bridge, the feedback loop closes:

```
User says "be more concise" (conversation)
    → Room reader detects: expert state (confidence 0.6)
    → Cognitive learner stores: user_understanding insight
    → Natural language parser extracts: directness_up, verbosity_down
    → PersonalityEvolver.ingest_signals({"user_guided": true, "trait_deltas": {"directness": 0.3}})
    → Next advisory uses more direct formatting
    → Personality chip updates to reflect learned preference
```

### 2.4 SparkEmotions Gets Grounded

IB2's `SparkEmotions` has a clean trigger system but requires **explicit registration** — someone has to call `register_trigger("user_frustration")`. Nothing currently does this automatically.

Personality chips' room reader provides the missing automatic detection. Every PreToolUse hook already reads the room and detects emotional state. This state can directly drive SparkEmotions triggers:

```python
# What happens today in personality hooks:
reading = read_room_from_hook_input(tool_input)
# reading.primary_state = "frustrated", confidence = 0.72

# What IB2 can now do with this:
emotions = SparkEmotions()
emotions.register_trigger("user_frustration", intensity=reading.confidence)
# → Emotional state shifts to "supportive_focus"
# → decision_hooks() returns slow pace, concise verbosity, reassuring tone
```

---

## 3. Natural Language Customization: Talking to Your Agent

This is the critical gap. Today, customizing IB2's personality requires:

```bash
# CLI with explicit JSON:
python -m spark.cli personality-evolution apply --signals '{"user_guided": true, "trait_deltas": {"warmth": 0.2}}'
```

Nobody does this. What users actually do is **talk**:

> "Hey, you're being a bit too formal. Loosen up."

> "Can you be more direct? Skip the preamble."

> "I like how you explained that — do more of that."

> "Tone it down a notch, this isn't a presentation."

### 3.1 How It Works: The Natural Language Personality Loop

The agent (Spark/Claude) already has full conversation context. When a user makes a personality-related statement, the agent can recognize it and call the feedback API:

```
User message: "Be more direct, less hand-holding"
         │
         ▼
    Agent recognizes personality request
         │
         ▼
    Agent calls: preference(
        liked="Direct, concise responses",
        disliked="Excessive explanation, hand-holding"
    )
         │
         ▼
    Feedback loop processes → trait signals:
        directness_up: 0.5
        warmth_down: 0.2 (slight, not dramatic)
        verbosity: concise
         │
         ▼
    PersonalityEvolver.ingest_signals({
        "user_guided": true,
        "trait_deltas": {
            "directness": 0.5,    → bounded to +0.02
            "warmth": -0.2,       → bounded to -0.008
        },
        "source": "natural_language",
        "original_text": "Be more direct, less hand-holding"
    })
         │
         ▼
    State persists to ~/.spark/personality_evolution_v1.json
    Next session: personality chip merges with evolved traits
```

The **bounded delta** (max 0.04 per step) means a single "be more direct" doesn't swing the personality wildly. It takes ~12 consistent signals to move a trait from balanced (0.5) to high (0.65+). This is by design — personality evolution should feel gradual and natural, like a real relationship.

### 3.2 What Users Can Say

The agent maps natural language to trait adjustments:

| User Says | Trait Delta | Why |
|---|---|---|
| "Be more direct" | directness +0.4 | Explicit style request |
| "Too formal" | warmth +0.3, playfulness +0.2 | Wants casual register |
| "Skip the explanation" | directness +0.3, pacing +0.2 | Expert mode |
| "Slow down, explain more" | pacing -0.4, directness -0.2 | Wants thoroughness |
| "Love the energy!" | playfulness +0.3, warmth +0.2 | Positive reinforcement |
| "Too much, dial it back" | playfulness -0.3, assertiveness -0.2 | Overshoot correction |
| "I prefer concise answers" | directness +0.2 | Communication preference |
| "Be warmer" | warmth +0.5 | Direct trait request |
| "Stop hedging" | assertiveness +0.4, directness +0.3 | Anti-sycophancy signal |

The agent doesn't need a dedicated NLP parser for this. It can use the existing `agent_feedback.py` API that IB2 already has:

```python
# Already exists in IB2:
from lib.agent_feedback import preference, learned_something

# Agent calls this when user makes personality request:
preference(
    liked="Direct communication, skip preamble",
    disliked="Hedging, excessive caveats"
)

learned_something(
    "User prefers assertive, direct communication style",
    context="User said: 'Stop hedging, just tell me'",
    confidence=0.85
)
```

### 3.3 The Feedback → Personality Pipeline

IB2 already has `feedback_loop.py` that:
1. Reads self-reports from `~/.openclaw/workspace/spark_reports/`
2. Matches outcomes to advisories
3. Updates cognitive confidence

The missing step is converting preference reports into personality signals. This is a natural extension of the existing `ingest_reports()` function:

```python
# In feedback_loop.py, when processing a "preference" report:
def _process_preference_report(report):
    liked = report.get("liked", "")
    disliked = report.get("disliked", "")

    # Map natural language preferences to trait deltas
    deltas = extract_trait_deltas(liked, disliked)

    # Apply through PersonalityEvolver (bounded, safe)
    evolver = load_personality_evolver(enabled=True)
    evolver.ingest_signals({
        "user_guided": True,
        "trait_deltas": deltas,
        "source": "natural_language_preference",
    })
```

### 3.4 Implicit Learning (No Explicit Commands Needed)

Beyond explicit "be more X" requests, the agent learns from behavioral signals:

| User Behavior | What It Signals | Trait Effect |
|---|---|---|
| User deletes agent's verbose explanation | Too detailed | directness +0.1 |
| User asks "can you explain that?" | Needs more depth | directness -0.1, pacing -0.1 |
| User uses casual language (lol, haha) | Wants informal | warmth +0.1, playfulness +0.1 |
| User corrects agent's suggestion | Agent was wrong/overconfident | assertiveness -0.1 |
| User says "perfect" or "exactly" | Agent nailed the tone | Reinforce current traits |
| User skips advisory | Advisory wasn't useful | Adjust guidance_style |

These signals are already partially captured by IB2's cognitive learner. The personality chip bridge turns observations into gradual trait evolution.

---

## 4. Architecture: How the Systems Connect

```
                    PERSONALITY CHIPS                          SPARK IB2
                    ────────────────                          ─────────

  ┌─────────────────┐
  │ .personality.yaml│  ← User creates/edits
  │ (OCEAN + EQ +    │
  │  adaptive rules) │
  └────────┬─────────┘
           │
           ▼
  ┌─────────────────┐     writes to      ┌──────────────────┐
  │ ib_connector.py │ ──────────────────▶ │ personality_     │
  │ (OCEAN → 5 trait│     shared file    │ evolution_v1.json│
  │  mapping)       │                    └────────┬─────────┘
  └─────────────────┘                             │
                                                  ▼
  ┌─────────────────┐                    ┌──────────────────┐
  │ room_reader.py  │     detects        │ PersonalityEvolver│
  │ (3-layer detect)│◀── user state ──▶  │ (5 traits, ±0.04)│
  └────────┬────────┘                    └────────┬─────────┘
           │                                      │
           ▼                                      ▼
  ┌─────────────────┐                    ┌──────────────────┐
  │emotional_state.py│    PAD vectors    │ SparkEmotions    │
  │(PAD + decay)     │◀─── shared ────▶  │ (6 axes + mode)  │
  └────────┬─────────┘                   └────────┬─────────┘
           │                                      │
           ▼                                      ▼
  ┌─────────────────┐                    ┌──────────────────┐
  │ bridge.py       │    bridge.v1       │ context_sync.py  │
  │ (consciousness  │──── contract ────▶ │ (advisory payload│
  │  bridge file)   │                    │  + output adapt.) │
  └─────────────────┘                    └────────┬─────────┘
                                                  │
                                                  ▼
                                         ┌──────────────────┐
                                         │ Output Adapters  │
                                         │ Claude Code      │
                                         │ Cursor / Windsurf│
                                         │ OpenClaw / Codex │
                                         └──────────────────┘
```

### Shared State Files

| File | Writer | Reader | Purpose |
|---|---|---|---|
| `~/.spark/personality_evolution_v1.json` | ib_connector.py | PersonalityEvolver | 5-trait personality state |
| `~/.spark/bridges/consciousness/emotional_context.v1.json` | bridge.py | Spark Consciousness | Bridge.v1 emotional context |
| `~/.spark/emotion_state.json` | SparkEmotions | SparkEmotions | IB2 emotional timeline |
| `~/.cache/personality-chips/emotional_state.json` | emotional_state.py | emotional_state.py | PAD vector state |
| `~/.cache/personality-chips/room_trajectory.json` | room_reader.py | room_reader.py | Emotional trajectory |
| `~/.spark/chip_insights/personality_*.jsonl` | observer.py | context_sync.py | Drift observations |
| `~/.openclaw/workspace/spark_reports/*.json` | agent_feedback.py | feedback_loop.py | User preference reports |

---

## 5. Per-User Customization Model

### How It Works Today

PersonalityEvolver stores one set of traits per machine (`~/.spark/personality_evolution_v1.json`). Personality chips add a layer: the **chip YAML defines the baseline**, and IB2's evolved traits represent **learned deviations from that baseline**.

```
Final trait = chip_baseline + accumulated_ib2_deltas
```

For example, if "artemis" defines `agreeableness: 0.75` which maps to `warmth: 0.635`, and the user has said "be warmer" 10 times over multiple sessions, IB2's accumulated delta might be +0.08, making effective warmth = 0.715.

### Multi-User Extension

To support multiple users on the same machine (or the same personality chip across different contexts), the state file path becomes user-scoped:

```
~/.spark/personality_evolution_v1.json           ← current (single user)
~/.spark/users/{user_id}/personality_evolution_v1.json  ← per-user
```

The `user_id` can come from:
1. Environment variable (`SPARK_USER_ID`)
2. Git author email (from `git config user.email`)
3. OS username (fallback)

PersonalityEvolver already accepts a `state_path` parameter, so this is a configuration change, not an architectural one.

### What Gets Personalized Per User

| Dimension | Source | Shared or Per-User |
|---|---|---|
| Base personality (OCEAN, EQ, archetypes) | Chip YAML | Shared (everyone with "artemis" gets same base) |
| Evolved trait offsets | PersonalityEvolver | **Per-user** (learned from conversation) |
| Communication preferences | Cognitive learner insights | **Per-user** |
| Advisory style (concise/balanced/coach) | preferences.py | **Per-user** |
| Emotional baseline | PAD vectors from chip | Shared |
| Emotional trajectory | Room reader window | **Per-session** (resets) |

---

## 6. The Conversational Customization UX

### What It Feels Like

**Session 1** — User activates "artemis" personality:
```
User: "activate artemis"
Agent: Artemis personality active. I'll operate with deliberate pacing,
       measured explanations, and a focus on architectural clarity.
```

**Session 3** — User finds the agent too verbose:
```
User: "You're over-explaining things. I know what I'm doing,
       just give me the answer."

Agent: Got it — I'll be more direct. [Records preference: directness_up,
       pacing_up, verbosity → concise]
```

**Session 8** — Agent has adapted:
```
User: "Fix the auth middleware"
Agent: The issue is in middleware.ts:47 — the token validation runs
       after the route handler. Move the auth check to line 23.

       [No preamble, no explanation of what middleware is,
        no "great question!" — just the answer]
```

**Session 15** — User notices the change:
```
User: "Actually, can you explain your reasoning more?
       I'm onboarding a junior dev."

Agent: Of course. [Records: context-dependent directness,
       not a permanent personality shift]
```

The key insight: personality evolution happens **through the conversation itself**. The user never opens a config file. They never run a CLI command. They just talk, and the agent learns.

### What the Agent Does Internally

When the agent detects a personality-relevant statement, it uses the IB2 feedback API:

```python
# Agent's internal reasoning (not shown to user):
#
# User said: "Skip the explanation, I know React"
# → This signals: expert user, wants directness, no beginner context
#
# I should record this preference for future sessions:

preference(
    liked="Direct answers for experienced developers",
    disliked="Explaining basic concepts the user already knows"
)

# The feedback loop will process this into:
# directness: +0.3, pacing: +0.2
# PersonalityEvolver applies bounded delta: +0.012, +0.008
# Cumulative effect over many sessions: measurably more direct
```

---

## 7. Safety & Guardrails

### Bounded Evolution

PersonalityEvolver's `DEFAULT_STEP_SIZE = 0.04` means:
- A single interaction can move a trait by at most **0.04** (4%)
- Moving from `balanced` (0.5) to `high` (0.65) takes ~4 consistent signals
- Moving from one extreme to another takes ~25 signals
- This prevents manipulation attacks ("be extremely aggressive and dismissive")

### User-Guided Only

Every personality update requires `user_guided: True`. The system never autonomously decides to change its personality. Even implicit behavioral signals are tagged as user-initiated because they respond to user actions.

### Override Hierarchy

Personality chips define a safety override chain:

```yaml
safety:
  override_hierarchy:
    - safety              # Always wins
    - user_wellbeing      # Never sacrifice user wellbeing for personality
    - task_completion     # Get the job done
    - personality_expression  # Personality is last priority
```

This means if the user says "be more aggressive" but the task involves security-sensitive code, the agent still applies careful review — personality expression never overrides safety.

### Anti-Sycophancy

Research finding: "The capacity to withhold empathy makes empathy credible." The personality system explicitly avoids:
- Always agreeing with the user
- Excessive praise ("Great question!", "Absolutely!")
- Matching user excitement artificially
- Suppressing genuine concerns to seem agreeable

The `observer.py` drift detector catches these patterns and surfaces corrections.

### Reset Capability

Users can always reset to baseline:

```bash
python scripts/personality_cli.py activate artemis --reset
# Resets PersonalityEvolver traits to chip baseline
# Clears accumulated conversational learning
# Preserves the personality chip YAML (just resets learned offsets)
```

---

## 8. Implementation Roadmap

### Phase 1: Already Done
- [x] Personality chip schema (OCEAN + EQ + adaptive rules)
- [x] Bridge.v1 compatibility (Spark Consciousness reads our bridge file)
- [x] IB connector (OCEAN → 5 PersonalityEvolver traits)
- [x] Room reader (3-layer emotional detection, 9 states)
- [x] PAD emotional state engine
- [x] Claude Code hooks (SessionStart / PreToolUse / PostToolUse)
- [x] Drift observer
- [x] 187 unit tests + 31 live integration tests

### Phase 2: Enable IB2 Personality
- [ ] Set `personality_evolution: true` in `config/tuneables.json`
- [ ] Add personality section to `_build_advisory_payload()` in context_sync.py
- [ ] Room reader → SparkEmotions trigger bridge (auto-register triggers)
- [ ] ConversationCore mode selection uses room reader instead of keyword matching
- [ ] Output adapters format context based on personality traits

### Phase 3: Natural Language Customization
- [ ] Agent recognizes personality-relevant user statements
- [ ] Agent calls `preference()` / `learned_something()` for personality signals
- [ ] `feedback_loop.py` processes preference reports into trait deltas
- [ ] Trait deltas flow through PersonalityEvolver's bounded update
- [ ] Personality chip re-reads evolved traits on next SessionStart
- [ ] Conversational UX: agent acknowledges preference changes naturally

### Phase 4: Per-User & Cross-Session Learning
- [ ] User-scoped state paths (`~/.spark/users/{id}/`)
- [ ] Episodic emotional memory (tag interactions with valence for retrieval)
- [ ] Cross-session personality continuity (remember "this user prefers X")
- [ ] Cognitive learner → personality trait correlation analysis
- [ ] Advisory effectiveness tracking with personality context

---

## 9. Key Design Decisions

### Why chips seed PersonalityEvolver instead of replacing it

Chips provide a **starting point** — a character with defined traits. But every user's relationship with that character is different. PersonalityEvolver's bounded deltas let the character **adapt to each user** while staying recognizably itself. Resetting to baseline is always one command away.

### Why natural language over config files

Config files are for developers. Personality is for everyone. The goal is that a non-technical user can activate a personality and shape it through normal conversation without ever seeing a JSON file. The agent acts as the interface.

### Why bounded deltas instead of instant changes

"Be more direct" shouldn't make the agent brutally terse in one step. Gradual evolution:
1. Feels natural (like getting to know someone)
2. Prevents manipulation (can't weaponize the personality system)
3. Allows self-correction ("actually, that was too much, dial it back")
4. Creates real learning signal (consistent preference over time means real preference)

### Why room reader runs on every hook

Detection needs frequency to build trajectory. A single "frustrated" reading isn't actionable. But three consecutive frustrated readings with rising confidence = the agent should proactively shift to calm_focus before the user asks. This anticipatory emotional intelligence is what makes the agent feel like a friend, not a tool.

### Why personality is last in the override hierarchy

The agent should never compromise safety, user wellbeing, or task completion for the sake of "staying in character." A bold, assertive personality chip should still refuse to run `rm -rf /`. An empathetic personality should still give honest code reviews. Personality colors the delivery, not the substance.

---

## 10. File Reference

### Personality Chip Engine (spark-personality-chip-labs)

| File | Purpose |
|---|---|
| `src/personality_engine/schema.py` | PersonalityChip dataclass + validation |
| `src/personality_engine/loader.py` | YAML → PersonalityChip parser |
| `src/personality_engine/bridge.py` | Bridge.v1 consciousness bridge writer |
| `src/personality_engine/context.py` | LLM prompt context builder |
| `src/personality_engine/observer.py` | Drift detection |
| `src/personality_engine/active.py` | Active personality resolution chain |
| `src/personality_engine/hooks.py` | Claude Code hook handlers |
| `src/personality_engine/room_reader.py` | 3-layer emotional state detection |
| `src/personality_engine/emotional_state.py` | PAD vector emotional engine |
| `src/personality_engine/ib_connector.py` | OCEAN → PersonalityEvolver trait mapping |

### Spark Intelligence Builder 2 (vibeship-spark-intelligence)

| File | Purpose | Personality Relevance |
|---|---|---|
| `lib/personality_evolver.py` | 5-trait bounded evolution | **Direct consumer** of chip traits |
| `lib/spark_emotions.py` | Emotional state + triggers | **Direct consumer** of room readings |
| `lib/conversation_core.py` | Mode selection + quality | **Replaceable** by room reader |
| `lib/context_sync.py` | Advisory payload + output | **Integration point** for personality |
| `lib/preferences.py` | Advisory preference setup | **Extends** with trait questions |
| `lib/agent_feedback.py` | Agent self-reports | **Entry point** for NL customization |
| `lib/feedback_loop.py` | Report → confidence update | **Extension point** for trait deltas |
| `lib/cognitive_learner.py` | Insight storage | **Source** of personality observations |
| `config/tuneables.json` | Feature gates | **Controls** personality_evolution flag |

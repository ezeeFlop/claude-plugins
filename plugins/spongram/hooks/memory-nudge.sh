#!/usr/bin/env bash
# Event-driven memory-capture nudge (Stop + PostToolUse:Bash).
#
# WHY THIS EXISTS
#   The plugin already states the write rule three times over: recall-on-start.sh
#   injects a "Règles strictes" block, skills/spongram/SKILL.md has "Hard rules
#   (MUST)", and the MCP server appends a behavioural contract on `initialize`.
#   The rule is not missing — it is injected once, at position 0, and loses
#   salience against hundreds of task-focused turns. A fourth declarative layer
#   would change nothing. What was missing is a trigger that fires AT THE MOMENT
#   the knowledge exists. That is this hook.
#
# WHY THESE TWO EVENTS
#   Per the Claude Code hooks contract, only a subset of events can hand context
#   back to the model. `Stop` and `PostToolUse` both support
#   hookSpecificOutput.additionalContext. `PreCompact` and `SessionEnd` do NOT —
#   they cannot prompt the model at all (PreCompact only blocks via exit 2;
#   SessionEnd runs after the session is over). Capture at those two points has
#   to be out-of-band and is handled separately.
#
# BEHAVIOUR
#   Advisory only: we emit additionalContext, never `decision: "block"`. If the
#   model has nothing durable to write, the turn ends normally — no extra round
#   trip is forced. Heavily throttled so a nudge stays rare enough to be read
#   rather than tuned out.
#
# Never breaks a session: any parse failure, missing field or unexpected shape
# exits 0 with no stdout.
set -u

[ -n "${SPONGRAM_NUDGE_DISABLED:-}" ] && exit 0

input=$(cat 2>/dev/null || echo '{}')

python3 - "$input" <<'PY' 2>/dev/null || exit 0
import json, os, sys, time

raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
try:
    inp = json.loads(raw)
except Exception:
    sys.exit(0)
if not isinstance(inp, dict):
    sys.exit(0)


def env_int(name, default):
    try:
        return int(os.environ[name])
    except Exception:
        return default


event = inp.get("hook_event_name") or ""
transcript = inp.get("transcript_path") or ""
session_id = inp.get("session_id") or "unknown"

# Already inside a hook-forced continuation — never pile another nudge on top.
if inp.get("stop_hook_active"):
    sys.exit(0)

# ── Event gate ──────────────────────────────────────────────────────────
# Stop: end of a turn, the broad safety net.
# PostToolUse: only a real `git commit`. A commit is the rare moment when the
# *why* behind a change is still fresh and is written down nowhere — the message
# records what changed, not what was rejected or why this approach won.
if event == "Stop":
    gap = env_int("SPONGRAM_NUDGE_GAP", 30)
    cooldown = env_int("SPONGRAM_NUDGE_COOLDOWN", 25)
    min_entries = env_int("SPONGRAM_NUDGE_MIN_ENTRIES", 20)
    kind = "stop"
elif event == "PostToolUse":
    if (inp.get("tool_name") or "") != "Bash":
        sys.exit(0)
    cmd = ((inp.get("tool_input") or {}).get("command") or "")
    if "git commit" not in cmd or "--dry-run" in cmd:
        sys.exit(0)
    # A commit is high-value and infrequent: much tighter thresholds.
    gap = env_int("SPONGRAM_NUDGE_COMMIT_GAP", 8)
    cooldown = env_int("SPONGRAM_NUDGE_COMMIT_COOLDOWN", 8)
    min_entries = 0
    kind = "commit"
else:
    sys.exit(0)

if not transcript or not os.path.isfile(transcript):
    sys.exit(0)

# ── Scan the transcript ─────────────────────────────────────────────────
# Count only user/assistant records: the file is also full of bookkeeping
# entries (mode, attachment, ai-title, file-history-snapshot, …) that would
# inflate the distance and make the nudge fire far too early.
MEANINGFUL = ("user", "assistant")
turns = 0
last_write = None  # index, in meaningful-turn units, of the last add_memory

try:
    with open(transcript, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if not isinstance(rec, dict) or rec.get("type") not in MEANINGFUL:
                continue
            turns += 1
            msg = rec.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                # The MCP server name differs per install (plugin vs local
                # sidecar), so match the tool suffix, not the full path.
                name = (block.get("name") or "")
                if name.endswith("add_memory") or name.endswith("record_skill"):
                    last_write = turns
except Exception:
    sys.exit(0)

if turns < min_entries:
    sys.exit(0)

since_write = turns if last_write is None else turns - last_write
if since_write < gap:
    sys.exit(0)

# ── Per-session cooldown ────────────────────────────────────────────────
# Without this the nudge would re-fire on every single turn once the gap is
# crossed, which is exactly how a reminder becomes noise and stops being read.
state_dir = os.path.expanduser("~/.spongram/state")
state_path = os.path.join(state_dir, "nudge-%s.json" % session_id.replace("/", "_"))
last_nudge = 0
try:
    with open(state_path, "r", encoding="utf-8") as fh:
        last_nudge = int((json.load(fh) or {}).get("turns", 0))
except Exception:
    last_nudge = 0

if turns - last_nudge < cooldown:
    sys.exit(0)

try:
    os.makedirs(state_dir, mode=0o700, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"turns": turns, "at": int(time.time()), "kind": kind}, fh)
except Exception:
    pass  # a state write failure must not suppress the nudge itself

# ── The nudge ───────────────────────────────────────────────────────────
if kind == "commit":
    body = (
        "**Spongram — commit détecté.** Le *pourquoi* de ce changement est frais "
        "maintenant et n'est écrit nulle part : le message de commit dit ce qui a "
        "changé, pas ce qui a été écarté ni pourquoi cette approche a gagné.\n\n"
        "Si ce commit acte une décision, une contrainte découverte, ou une "
        "hypothèse réfutée, appelle `add_memory` maintenant."
    )
else:
    body = (
        "**Spongram — point de capture mémoire.** Aucune écriture depuis %d tours.\n\n"
        "Rien à faire si rien de durable n'est apparu — ce rappel n'exige aucune "
        "action et n'attend pas de réponse." % since_write
    )

ctx = (
    "%s\n\n"
    "À écrire (`add_memory`) : décisions actées, préférences exprimées, "
    "contraintes découvertes, **hypothèses réfutées** (ce qui NE marche pas est "
    "aussi précieux que ce qui marche), faits durables sur le projet ou l'infra.\n\n"
    "À NE PAS écrire : détails éphémères (noms de fichiers, numéros de ligne, "
    "sorties de commandes), ni ce que le repo enregistre déjà (structure du code, "
    "historique git, CLAUDE.md).\n\n"
    "Taggage obligatoire — `source_description` doit porter le `project=` du bloc "
    "de contexte injecté au SessionStart (ou `project=global` pour un fait "
    "transverse). N'écris rien via `Write` sur disque : la source de vérité est "
    "Spongram." % body
)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": event,
        "additionalContext": ctx,
    }
}))
PY

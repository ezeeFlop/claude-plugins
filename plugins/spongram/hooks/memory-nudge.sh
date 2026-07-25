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
# HOT PATH — READ THIS BEFORE EDITING
#   `Stop` fires at EVERY turn end, so this script's cost is paid on every turn
#   of every session. Real transcripts reach 56 MB; reading one whole was
#   measured at 231 ms per turn, and it grows with the session (O(n) per turn,
#   O(n²) cumulative). We therefore scan only a bounded TAIL WINDOW: cost is
#   constant regardless of session length. Never reintroduce a full-file read.
#
# Never breaks a session: any parse failure, missing field or unexpected shape
# exits 0 with no stdout.
set -u

[ -n "${SPONGRAM_NUDGE_DISABLED:-}" ] && exit 0

input=$(cat 2>/dev/null || echo '{}')

# Locale for the injected strings: FR when the shell locale is French, else EN.
# Mirrors recall-on-start.sh so a bilingual plugin stays bilingual everywhere.
lang="en"
case "${LANG:-}${LC_ALL:-}" in fr*|FR*) lang="fr" ;; esac

python3 - "$input" "$lang" <<'PY' 2>/dev/null || exit 0
import json, os, re, sys, time

raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
lang = sys.argv[2] if len(sys.argv) > 2 else "en"
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

# A real `git commit`, not the string "git commit" appearing inside some other
# command (`echo git commit`, a grep pattern, a commit message quoting itself).
# Anchored at the start of the command or just after a shell separator.
# Between `git` and the subcommand, only real global options may appear — those
# taking a separate value (`-C <path>`, `-c k=v`) and long forms
# (`--git-dir=…`, `--no-pager`). Allowing arbitrary tokens here would re-admit
# `git log --grep='git commit'` as a false positive.
_GIT_COMMIT = re.compile(
    r"(?:^|[;&|]|&&|\|\|)\s*(?:sudo\s+)?git\s+"
    r"(?:-[A-Za-z]\s+\S+\s+|--[A-Za-z-]+(?:=\S+)?\s+)*"
    r"commit\b"
)

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
    cmd = (inp.get("tool_input") or {}).get("command") or ""
    if "--dry-run" in cmd or not _GIT_COMMIT.search(cmd):
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

# ── State (read before the scan: the stored offset bounds the scan) ──────
state_dir = os.path.expanduser("~/.spongram/state")
state_path = os.path.join(state_dir, "nudge-%s.json" % session_id.replace("/", "_"))
last_nudge_offset = 0
try:
    with open(state_path, "r", encoding="utf-8") as fh:
        last_nudge_offset = int((json.load(fh) or {}).get("offset", 0))
except Exception:
    last_nudge_offset = 0

# ── Scan a bounded tail of the transcript ───────────────────────────────
# Only user/assistant records count as turns: the file is also full of
# bookkeeping entries (mode, attachment, ai-title, file-history-snapshot, …)
# that would inflate the distance and make the nudge fire far too early.
WINDOW = env_int("SPONGRAM_NUDGE_WINDOW_BYTES", 2_000_000)
MEANINGFUL = ("user", "assistant")

try:
    size = os.path.getsize(transcript)
except Exception:
    sys.exit(0)

start = 0 if size <= WINDOW else size - WINDOW
exact = start == 0  # we saw the whole file, so counts are absolute

turns = 0              # meaningful turns inside the window
last_write = None      # index (window-relative) of the last memory write
turns_since_nudge = 0  # meaningful turns at/after the stored offset

try:
    with open(transcript, "rb") as fh:
        if start:
            fh.seek(start)
            fh.readline()  # discard the partial line we landed inside
        offset = fh.tell()
        for line in fh:
            line_start = offset
            offset += len(line)
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped.decode("utf-8", "replace"))
            except Exception:
                continue
            if not isinstance(rec, dict) or rec.get("type") not in MEANINGFUL:
                continue
            turns += 1
            if line_start >= last_nudge_offset:
                turns_since_nudge += 1
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                # The MCP server name differs per install (plugin vs local
                # sidecar), so match the tool suffix, not the full path.
                name = block.get("name") or ""
                if name.endswith("add_memory") or name.endswith("record_skill"):
                    last_write = turns
except Exception:
    sys.exit(0)

# A short session deserves no nudge. Only decidable when we read the whole
# file — past one window the session is long by construction.
if exact and turns < min_entries:
    sys.exit(0)

# Distance since the last write. When the window holds no write this is a lower
# bound, which is all the threshold test needs.
since_write = turns if last_write is None else turns - last_write
if since_write < gap:
    sys.exit(0)

# Per-session cooldown. Without it the nudge would re-fire on every turn once
# the gap is crossed, which is exactly how a reminder becomes noise.
# If the file grew past a full window since the last nudge, the cooldown is
# satisfied by construction.
if last_nudge_offset >= start and turns_since_nudge < cooldown:
    sys.exit(0)

try:
    os.makedirs(state_dir, mode=0o700, exist_ok=True)
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"offset": size, "at": int(time.time()), "kind": kind}, fh)
    os.replace(tmp, state_path)
    # One state file per session would otherwise accumulate forever.
    cutoff = time.time() - 14 * 86400
    with os.scandir(state_dir) as it:
        for entry in it:
            if entry.name.startswith("nudge-") and entry.stat().st_mtime < cutoff:
                os.unlink(entry.path)
except Exception:
    pass  # a state failure must not suppress the nudge itself

# ── The nudge ───────────────────────────────────────────────────────────
if lang == "fr":
    if kind == "commit":
        body = (
            "**Spongram — commit détecté.** Le *pourquoi* de ce changement est "
            "frais maintenant et n'est écrit nulle part : le message de commit "
            "dit ce qui a changé, pas ce qui a été écarté ni pourquoi cette "
            "approche a gagné.\n\nSi ce commit acte une décision, une contrainte "
            "découverte, ou une hypothèse réfutée, appelle `add_memory` maintenant."
        )
    else:
        body = (
            "**Spongram — point de capture mémoire.** Aucune écriture depuis "
            "%d tours.\n\nRien à faire si rien de durable n'est apparu — ce "
            "rappel n'exige aucune action et n'attend pas de réponse." % since_write
        )
    ctx = (
        "%s\n\n"
        "À écrire (`add_memory`) : décisions actées, préférences exprimées, "
        "contraintes découvertes, **hypothèses réfutées** (ce qui NE marche pas "
        "est aussi précieux que ce qui marche), faits durables sur le projet ou "
        "l'infra.\n\n"
        "À NE PAS écrire : détails éphémères (noms de fichiers, numéros de ligne, "
        "sorties de commandes), ni ce que le repo enregistre déjà (structure du "
        "code, historique git, CLAUDE.md).\n\n"
        "Taggage obligatoire — `source_description` doit porter le `project=` du "
        "bloc de contexte injecté au SessionStart (ou `project=global` pour un "
        "fait transverse). N'écris rien via `Write` sur disque : la source de "
        "vérité est Spongram." % body
    )
else:
    if kind == "commit":
        body = (
            "**Spongram — commit detected.** The *why* behind this change is "
            "fresh right now and is written down nowhere: the commit message "
            "records what changed, not what was ruled out or why this approach "
            "won.\n\nIf this commit settles a decision, a constraint you "
            "discovered, or a hypothesis you disproved, call `add_memory` now."
        )
    else:
        body = (
            "**Spongram — memory checkpoint.** Nothing written for %d turns.\n\n"
            "Nothing to do if nothing durable came up — this reminder requires "
            "no action and expects no reply." % since_write
        )
    ctx = (
        "%s\n\n"
        "Worth writing (`add_memory`): decisions settled, preferences stated, "
        "constraints discovered, **disproved hypotheses** (what does NOT work is "
        "as valuable as what does), durable facts about the project or infra.\n\n"
        "NOT worth writing: ephemeral detail (file names, line numbers, command "
        "output), or anything the repo already records (code structure, git "
        "history, CLAUDE.md).\n\n"
        "Tagging is mandatory — `source_description` must carry the `project=` "
        "from the context block injected at SessionStart (or `project=global` for "
        "a cross-cutting fact). Never write memory to disk with `Write`: the "
        "source of truth is Spongram." % body
    )

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": event,
        "additionalContext": ctx,
    }
}))
PY

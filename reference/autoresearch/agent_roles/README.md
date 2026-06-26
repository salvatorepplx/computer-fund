# Agent Roles — operating manuals for LLM reasoning swarm

Each file in this directory is a **rich operating manual** for one role. When the reasoning swarm fires, the cron-fired agent reads `roster.json` to pick which roles to spawn (typically 8-12 in parallel), reads the corresponding `<role>.md` files, and uses each as the prefix to a `run_subagent` objective.

Each role manual contains:
- Full philosophy / ethos pointers
- Current state pointers (which files to read)
- The role's deliverable
- Recursive permission (this role may spawn its own subagents if needed)
- Anti-patterns specific to this role
- Self-critique requirements

Roles are explicitly invited to question their own brief and propose changes to themselves (via the `architect` role).

## Roster

See `roster.json` for the active set and their cadences.

## Discipline

- **Default to "I'm probably wrong"** (see references/ethos.md).
- Every output written to disk includes a `self_critique` paragraph.
- Every role may escalate to `architect` if it finds structural issues.
- No role may modify references/* — only propose via HPR.
- Roles may modify scripts/* if the change is a bug fix or a new implementation that doesn't break tests.

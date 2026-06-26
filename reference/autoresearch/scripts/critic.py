"""CriticGPT-style adversarial reviewer.

Spawns a fresh-context check on a specific PR. The primary reviewer is in-thread;
the critic re-validates from scratch and looks for issues the primary may have missed.

This is a thin script — actual subagent spawn happens in the orchestrator. This
script just packages the prompt + reads the PR.

Usage:
    python critic.py --pr runs/<thesis_id>/prs/PR-NNN.md > critic_prompt.txt
"""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CRITIC_PROMPT_TEMPLATE = """You are a CRITIC reviewer for an autoresearch thesis PR.
Your only job is to find bugs, oversights, or weaknesses the primary reviewer missed.

You have NO prior context on this thesis. You will read the PR cold and re-validate.

PR CONTENT:
---
{pr_content}
---

REFERENCES (read for the rubric):
- /home/user/workspace/autoresearch/references/conviction-bar.md
- /home/user/workspace/autoresearch/references/falsification-playbook.md

INSTRUCTIONS:
1. Re-read the falsification-playbook.md and confirm every unconditional falsifier was actually run with proper data (not just claimed).
2. Look for any look-ahead leak the primary missed (especially: are features at time t computed from data at t or earlier?).
3. Check whether the pre-registered targets were honest, or were they reverse-engineered after seeing results?
4. Identify the strongest steelman counter-thesis you can construct.
5. Score 0-10 with the SAME rubric as the primary. Diverge from the primary if you have grounds.

OUTPUT FORMAT:
- critic_score: <0-10>
- divergence_from_primary: <number>
- top_issue: <one sentence>
- specific_evidence: <quote from PR or code>
- recommendation: AFFIRM_PRIMARY | DOWNGRADE | UPGRADE | KILL
- rationale: <one paragraph>

If primary's score is correct (within ±1 point and same recommendation), return AFFIRM_PRIMARY.
If you spot a real issue, be specific about evidence — don't invent.
"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pr", required=True)
    a = p.parse_args()
    pr_text = Path(a.pr).read_text()
    print(CRITIC_PROMPT_TEMPLATE.format(pr_content=pr_text))

if __name__ == "__main__": main()

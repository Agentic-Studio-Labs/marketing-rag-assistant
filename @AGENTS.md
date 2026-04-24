# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Session start (new chat)

1. Read **`CLAUDE.md`** (repo map, GCP handoff, magic link / Resend, Terraform caveats).
2. Run **`bd ready --json`** (or **`bd ready`**) and pick an open issue; **`bd show <id>`** for context.
3. **GCP prod** follow-ups are tracked in beads (finish Artifact Registry + Cloud Run apply; mount Resend secret on **cih-api**; merge feature branch).

## Quick Reference

```bash
bd ready --json       # Unblocked work (prefer for agents)
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git (may try to push `main`; if branch protection blocks it, commit `.beads/issues.jsonl` on your feature branch and merge via PR)
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds


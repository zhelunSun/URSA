# AGENTS.md · URSA / Chapter 1 guardrails

This repository preserves both the original ExpertsRS prototype and the active
Chapter 1 system/evidence line.

## Protected history

- Active research branch: `codex/ch1-v2-e1-structured-planning`.
- Prototype tag: `prototype-notebook-v0-20250307` (`19db55b`).
- v053 closeout tag: `ch1-v053-closeout-20260819` (`9e18532`).
- Do not delete, move, force-update, or rewrite these tags or their reachable
  history without a verified replacement and an explicit researcher decision.

## Git cloud-sync gate

The canonical cross-repository policy is
`../research-harness/process/repository_sync_policy.md`.

- Start non-trivial work with
  `python ../research-harness/scripts/audit_repo_sync.py --repo . --fetch`.
- Before a large/live run, push a recoverable checkpoint. End a materially
  productive session by testing, committing, pushing, and verifying `ahead=0`.
- A local commit is not a cloud backup and must not remain local-only for more
  than three days. Never auto-commit research content or force-push history.
- Keep credentials, local environments, runtime results and generated PNGs out
  of Git. Track reproducible figure sources and reviewed small assets.
- Git and Git LFS are separate recovery surfaces. Do not report the repository
  as fully recoverable while `git lfs fsck` or clean-clone LFS restoration fails.

For thesis-facing claims and evidence boundaries, enter through
`docs/thesis/ch1_evidence_system/README.md` and its linked plan/registries.

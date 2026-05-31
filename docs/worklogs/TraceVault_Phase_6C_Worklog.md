# TraceVault Phase 6C Worklog
## Feature: Optional Obsidian-Friendly Vault Adapter

**Repository:** `xorcon/tracevault`  
**Primary branch:** `feat/phase-6c-obsidian-vault-adapter`  
**Follow-up clean branch:** `fix/phase-6c-vault-followup-clean`  
**Primary PR:** #11  
**Follow-up PR:** #13  
**Closed superseded PR:** #12  
**Feature scope:** Phase 6C — Optional Obsidian Vault Adapter  
**Primary PR title:** `feat: add optional obsidian vault adapter`  
**Follow-up PR title:** `fix: harden phase 6c vault adapter follow-up behavior`  
**Primary PR #11 status:** MERGED  
**Follow-up PR #13 status:** MERGED  
**Final Phase 6C merge commit:** `1269b805a184b6a61680a90bd7915af89ae02a8d`  
**Merged at:** `2026-05-27T17:44:24Z`  
**Final post-merge pytest:** `1476 passed`  
**Final post-merge ruff:** `All checks passed`  
**Final post-merge diagnose:** `Package structure: OK`  
**Final post-merge compileall:** `OK`  
**Final Codex result:** Approve / Mergeable  

---

## 1. Purpose of This Worklog

This worklog records the operating pattern used by Natthakit, ChatGPT / prompt layer, Claude Code, and Codex during TraceVault Phase 6C.

It is intended as a durable implementation-governance record for future agents such as Hermes Agent or Open Claw.

The central lesson from this phase:

```text
A vault adapter is not a knowledge generator.
It is a deterministic, non-destructive organization adapter for already-validated derived wiki artifacts.
```

Correct behavior in this phase required:

```text
start from Phase 6A exported Markdown notes
-> use Phase 6B wiki-health as preflight
-> adapt notes into an Obsidian-friendly vault layout
-> preserve note bytes and proof-chain metadata
-> detect collisions before writing
-> avoid source-of-truth inversion
-> fail closed on unhealthy input and unsafe filesystem states
-> avoid stale manifest/index output after failed reruns
-> protect user-authored files
-> review every filesystem edge case before merge
```

---

## 2. Phase 6 Context

Phase 6 is the Compiled Knowledge Wiki layer.

Phase 6 has three parts:

```text
Phase 6A — Evidence-backed Wiki Export
Phase 6B — Wiki Health / Lint / Drift Check
Phase 6C — Optional Obsidian Vault Adapter
```

Phase 6A established that wiki notes are derived artifacts, raw_text remains authoritative, export must preserve proof-chain metadata, strict export should fail closed, filename identity must be deterministic, and source evidence identity must be inspectable.

Phase 6B established that exported Markdown notes must pass deterministic health/lint checks, frontmatter and TraceVault metadata must be inspectable, claim-to-evidence citations must resolve, malformed notes must fail closed, and JSON CLI output must remain machine-readable.

Phase 6C builds on both:

```text
Only healthy Phase 6A notes should be adapted.
The adapter must not create knowledge, rewrite evidence, or weaken Phase 6B validation.
```

---

## 3. Phase 6C Objective

Phase 6C objective:

```text
Implement an optional, non-destructive, Obsidian-friendly vault adapter for already-exported TraceVault wiki Markdown notes.
```

The objective was not to create an Obsidian plugin. It was to create a deterministic filesystem adapter that can organize exported notes into a vault-like folder structure while preserving TraceVault metadata, note identity, evidence identity, and source-of-truth boundaries.

The intended flow:

```text
Phase 6A exported notes
  -> Phase 6B wiki-health preflight
  -> Phase 6C vault plan
  -> optional non-destructive copy
  -> optional deterministic metadata-only index notes
  -> deterministic manifest
```

---

## 4. Explicit Scope

### 4.1 In Scope

```text
optional vault adapter package under src/tracevault/wiki/vault/
plan-first vault adaptation
Phase 6B wiki-health preflight by default
dry-run / plan-first behavior
non-destructive copy behavior
byte-preserving Markdown copy via shutil.copy2
deterministic destination layout
duplicate destination detection
case-insensitive destination collision detection
path-scoped vault_dir exclusion during preflight
source collection excluding configured vault_dir only
metadata-only index note generation
vault manifest generation
manifest/index ownership markers
stale generated artifact cleanup on failed apply
CLI commands:
  python3 -m tracevault wiki-vault-plan
  python3 -m tracevault wiki-vault-adapt
JSON CLI output
synthetic-only unit tests
recursive .gitignore protection for generated vault output
lazy export from tracevault.wiki
```

### 4.2 Out of Scope

```text
Obsidian plugin
Obsidian runtime dependency
.obsidian/ configuration generation
sync/publishing workflow
cloud upload
Git automation
LLM/model calls
answer generation
reasoning
summarization
claim rewriting
evidence rewriting
citation rewriting
semantic relation inference
retrieval / RAG logic
private vault scanning
real private vault content in tests
generated vault output committed to Git
```

---

## 5. Final Implementation Summary

### 5.1 Primary PR #11

PR #11 introduced the Phase 6C vault adapter baseline.

Major source files added:

```text
src/tracevault/wiki/vault/__init__.py
src/tracevault/wiki/vault/adapter.py
src/tracevault/wiki/vault/index.py
src/tracevault/wiki/vault/layout.py
src/tracevault/wiki/vault/manifest.py
src/tracevault/wiki/vault/models.py
```

Major test files added:

```text
tests/unit/test_wiki_vault_adapter.py
tests/unit/test_wiki_vault_cli.py
```

Modified files included:

```text
.gitignore
src/tracevault/cli/main.py
src/tracevault/wiki/__init__.py
src/tracevault/wiki/health.py
tests/unit/test_wiki_health_directory.py
```

### 5.2 Follow-up PR #13

PR #13 hardened the adapter after PR #11 by adding:

```text
CLI case-insensitive collision regression tests
partial-copy failure fail-closed behavior
stale generated artifact cleanup
marker/ownership based cleanup
reserved-path pre-write ownership validation
generate_index=False behavior preservation
path-scoped vault_dir-only health exclusion correction
```

Final merge evidence:

```text
PR #13: MERGED
Merge commit: 1269b805a184b6a61680a90bd7915af89ae02a8d
Merged at: 2026-05-27T17:44:24Z
```

Final post-merge validation:

```text
pytest: 1476 passed
ruff: All checks passed
tracevault diagnose: Package structure OK
compileall: OK
```

---

## 6. Final CLI Contract

### 6.1 Plan command

```bash
python3 -m tracevault wiki-vault-plan <exported-wiki-dir> --vault-dir <vault-dir>
```

Expected behavior:

```text
runs Phase 6B preflight
builds deterministic adaptation plan
writes nothing
supports --json
fails non-zero on unhealthy notes, rejected notes, invalid paths, collisions, or validation errors
```

### 6.2 Apply command

```bash
python3 -m tracevault wiki-vault-adapt <exported-wiki-dir> <vault-dir>
```

Expected behavior:

```text
runs Phase 6B preflight
builds plan
validates destinations and reserved paths
copies notes byte-for-byte
optionally writes metadata-only indexes
writes manifest
non-destructive by default
preserves existing files unless overwrite is explicitly allowed
fails non-zero on health failure, collisions, rejected notes, write failures, or unsafe reserved paths
```

### 6.3 JSON contract

```text
--json emits exactly one valid JSON document
collisions return non-zero
health failures return non-zero
copy/write failures return non-zero
successful plan/adapt returns zero
```

---

## 7. Final Vault Layout

Default layout:

```text
<vault-dir>/
  TraceVault/
    Notes/
      <original-phase-6a-filename>.md
    Index/
      Home.md
      By-Type.md
      By-Source.md
    tracevault-vault-manifest.json
```

Key rule:

```text
Notes are copied, not rewritten.
Index and manifest are generated adapter-owned artifacts.
```

---

## 8. Role Boundaries

### 8.1 Natthakit — Human Architect / Repository Owner

Responsibilities:

```text
define Phase 6C intent
run local commands
control branch / commit / push / PR / merge lifecycle
send Claude Code outputs to ChatGPT for pre-screening
send PRs to Codex for independent review
avoid premature merge
capture merge evidence and validation output
```

Key behavior:

```text
did not merge after first passing tests
caught that fixes had not been pushed before merge
closed conflicted PR #12 in favor of clean PR #13
captured post-merge evidence after PR #13
```

### 8.2 ChatGPT — Architecture Planner / Review Orchestrator

Responsibilities:

```text
define Phase 6C architecture
separate adapter from plugin / knowledge generation
write Claude Code implementation prompts
convert Codex findings into focused fix prompts
define merge gates
recommend clean-branch recovery when PR #12 conflicted
protect source-of-truth and filesystem safety boundaries
```

Key decisions:

```text
Phase 6C should be adapter-only
Phase 6B health is mandatory preflight by default
vault_dir exclusion must be path-scoped, not name-scoped
copy must preserve Markdown bytes
case-only path collisions must be rejected
manifest/index must not become stale after failed applies
cleanup must be marker/ownership based
reserved file ownership must be checked before overwrite
generate_index=False must not validate index targets it will not write
```

### 8.3 Claude Code — Implementation Agent

Responsibilities:

```text
implement adapter modules
add CLI integration
add tests
fix only requested findings
run validation
report files changed and results
```

Observed behavior:

```text
implemented baseline adapter successfully
responded to many focused review loops
sometimes fixed one layer while leaving another path open
eventually produced strong coverage across failure paths
```

### 8.4 Codex — Independent Reviewer

Responsibilities:

```text
review actual PR diff
detect proof-chain risk
detect filesystem safety risk
detect stale artifact risk
detect false-pass validation behavior
detect cross-platform path collision risk
request changes until no Critical / Important issue remains
```

Codex’s main value:

```text
It identified failure paths and filesystem edge cases that happy-path tests did not prove.
```

---

## 9. Architecture Decisions

### Decision 1 — Phase 6C is adapter-only

Reason:

```text
Phase 6C should organize already-exported and validated notes.
It must not generate facts, infer relationships, or rewrite evidence.
```

Outcome:

```text
No LLM calls.
No summaries.
No semantic relations.
No claim/evidence rewriting.
No Obsidian runtime dependency.
```

### Decision 2 — Phase 6B health preflight is mandatory by default

Reason:

```text
The adapter should not organize invalid derived artifacts.
```

Outcome:

```text
build_vault_plan() runs check_wiki_health() by default.
Unhealthy input fails closed unless explicitly allowed for tests.
```

### Decision 3 — Exclusions must be path-scoped, not name-scoped

Initial mistake:

```text
Directories named TraceVault were skipped by name.
```

Problem:

```text
A real user source directory could be named TraceVault.
Name-based skipping produced false health passes.
```

Final rule:

```text
Only exclude the configured vault_dir.
Do not exclude arbitrary TraceVault/ directories by name.
```

### Decision 4 — Copy Markdown bytes, not text

Reason:

```text
Phase 6C must preserve exported notes exactly.
Line endings, BOM, YAML frontmatter, evidence labels, and citations must not be rewritten.
```

Outcome:

```text
shutil.copy2() is used for note copy.
CRLF/BOM byte-preservation tests were added.
```

### Decision 5 — Destination collision keys must be case-insensitive safe

Reason:

```text
A.md and a.md are different on Linux but collide on default Windows/macOS filesystems.
```

Outcome:

```text
canonical destination keys use path normalization and casefolding.
Planning and apply-time validation both reject case-only collisions.
```

### Decision 6 — Manifest and index are adapter-owned truth artifacts

Reason:

```text
Downstream tooling may trust manifest and index files.
If an apply fails, stale manifest/index files can falsely represent current state.
```

Outcome:

```text
All failed apply paths run marker/ownership-based cleanup of adapter-owned manifest/index artifacts.
```

### Decision 7 — Cleanup must not delete user-authored files

Reason:

```text
The adapter may operate inside a user-controlled vault.
A path that looks reserved is not automatically adapter-owned.
```

Outcome:

```text
Index files include a generated marker.
Manifest includes generated_by ownership field.
Cleanup removes only positively identified adapter-owned files.
```

### Decision 8 — Ownership must be checked before overwrite

Reason:

```text
Cleanup-time ownership checks are too late if the run already overwrote a user file with generated content and marker.
```

Outcome:

```text
Pre-write reserved path validation blocks overwriting user-authored reserved index files and non-adapter manifests.
```

### Decision 9 — Validation and cleanup have different scopes

Final invariant:

```text
Validation = only files this run will write.
Cleanup = stale adapter-owned files from previous runs.
```

Outcome:

```text
generate_index=False skips index pre-write validation.
generate_index=False still cleans stale adapter-generated indexes on failed reruns.
Manifest validation always runs because manifest is written on successful runs.
```

---

## 10. Implementation Flow

```text
1. Define Phase 6C as optional vault adapter.
2. Create branch feat/phase-6c-obsidian-vault-adapter.
3. Implement plan-first adapter, models, layout, index, manifest, and CLI.
4. Add synthetic tests.
5. Run validation.
6. Open PR #11.
7. Request Codex review.
8. Fix preflight fail-open, collisions, byte-copy, CLI behavior, gitignore, lazy export.
9. Fix nested vault output ingestion issue.
10. Fix Phase 6B preflight exclusion issue.
11. Fix name-based TraceVault skip.
12. Merge PR #11.
13. Create PR #12 for remaining CLI tests and partial-copy fixes.
14. Detect PR #12 conflict with already-merged PR #11.
15. Close PR #12 and create clean PR #13 from origin/main.
16. Cherry-pick only follow-up commits.
17. Fix partial-copy stale manifest/index behavior.
18. Fix marker/ownership cleanup.
19. Fix all failed apply return paths.
20. Fix pre-write ownership validation.
21. Fix generate_index=False regression.
22. Push final PR #13.
23. Codex approves.
24. Merge PR #13.
25. Run post-merge validation.
```

---

## 11. Codex Findings and Fix Loops

### 11.1 Finding — Preflight fail-open

Problem:

```text
build_vault_plan() marked unhealthy input but adapt_to_obsidian_vault() still called apply_vault_plan().
apply_vault_plan() could create vault folders and manifest even when health failed.
```

Fix:

```text
apply_vault_plan() refuses to write when health preflight failed or plan has rejected notes.
Validation happens before filesystem mutation.
```

### 11.2 Finding — Intra-plan destination collision

Problem:

```text
Two source notes in different directories with the same basename could map to the same destination.
```

Fix:

```text
duplicate destination paths are detected during planning and defensively at apply time.
```

### 11.3 Finding — Byte preservation

Problem:

```text
read_text()/write_text() could rewrite line endings or BOM.
```

Fix:

```text
Use shutil.copy2() / byte-preserving copy.
Add CRLF/BOM preservation tests.
```

### 11.4 Finding — CLI collision signaling

Problem:

```text
collisions could be treated as skipped/successful cases.
```

Fix:

```text
collisions are rejected and CLI returns non-zero.
```

### 11.5 Finding — .gitignore incomplete

Problem:

```text
only root-level generated vault outputs were ignored.
Nested vault outputs could be committed.
```

Fix:

```text
recursive generated output ignores:
**/TraceVault/
**/tracevault-vault-manifest.json
```

### 11.6 Finding — Lazy export contract

Problem:

```text
module __getattr__ could raise KeyError instead of AttributeError.
```

Fix:

```text
unknown attributes raise AttributeError.
Phase 6C exports are cached into globals().
```

### 11.7 Finding — Vault subtree collected as source

Problem:

```text
If vault_dir was inside wiki_dir, generated vault output could be collected as source notes on rerun.
```

Fix:

```text
source collection excludes configured vault_dir using resolved path checks.
```

### 11.8 Finding — Phase 6B preflight still scanned nested vault output

Problem:

```text
source collection excluded vault_dir, but check_wiki_health(wiki_dir) still scanned nested vault output before planning.
```

Fix:

```text
check_wiki_health() gained optional exclude_dirs support.
build_vault_plan() passes exclude_dirs=[vault_dir].
```

### 11.9 Finding — Generic health checker skipped TraceVault/ by name

Problem:

```text
Generic health.py skipped any directory named TraceVault, hiding real user source content.
```

Fix:

```text
remove name-based skip from health.py.
Generic check_wiki_health() scans TraceVault/ normally.
```

### 11.10 Finding — Adapter over-excluded TraceVault/ directories

Problem:

```text
adapter.py used _find_tracevault_dirs(wiki_dir) and excluded arbitrary TraceVault/ folders.
```

Fix:

```text
remove _find_tracevault_dirs().
exclude only configured vault_dir.
```

### 11.11 Finding — Partial copy failure left stale manifest/index

Problem:

```text
copy error prevented rewriting manifest/index but left old adapter-generated manifest/index from previous successful run.
```

Fix:

```text
on copy failure, clean stale adapter-owned manifest/index before returning failure.
```

### 11.12 Finding — Cleanup deleted reserved paths blindly

Problem:

```text
cleanup deleted fixed filenames regardless of whether they were user-authored.
```

Fix:

```text
add generated marker to index files.
add generated_by to manifest.
cleanup only unlinks positively identified adapter-owned artifacts.
```

### 11.13 Finding — Cleanup ran only on copy-stage errors

Problem:

```text
failed apply paths before copy, such as health failure or duplicate destination, could leave stale artifacts.
```

Fix:

```text
centralize failed returns with _fail_with_cleanup().
cleanup runs for health, rejected notes, duplicate destination, missing source, parent validation, base dir creation, copy error, index write error, and manifest write error.
```

### 11.14 Finding — Cleanup after manifest failure could delete user-authored reserved index

Problem:

```text
index generation could overwrite user-authored Home.md with marker, then manifest write failure triggered cleanup that deleted it.
```

Fix:

```text
pre-write ownership validation blocks overwriting user-authored reserved index files and non-adapter manifests.
```

### 11.15 Finding — generate_index=False regression

Problem:

```text
reserved index validation ran unconditionally even when generate_index=False.
User-authored index files blocked runs that would not write indexes.
```

Fix:

```text
index reserved validation is gated by config.generate_index.
manifest validation always runs.
cleanup still inspects stale adapter-generated index files regardless of generate_index.
```

---

## 12. Final Test and Validation Results

Final post-merge validation:

```text
python3 -m pytest -q
1476 passed

python3 -m ruff check .
All checks passed

python3 -m tracevault diagnose
Package structure: OK

python3 -m compileall src tests
OK
```

Ruff warning:

```text
Top-level linter settings are deprecated in favour of lint section.
```

Status:

```text
Non-blocking repository technical debt.
Not introduced as a Phase 6C blocker.
```

---

## 13. Merge Evidence

### PR #11

```text
PR #11: feat: add optional obsidian vault adapter
Status: MERGED
```

### PR #12

```text
PR #12: test: cover vault cli case-insensitive collisions
Status: CLOSED
Reason: superseded by clean PR #13
```

### PR #13

```json
{
  "mergeCommit": {
    "oid": "1269b805a184b6a61680a90bd7915af89ae02a8d"
  },
  "mergedAt": "2026-05-27T17:44:24Z",
  "number": 13,
  "state": "MERGED",
  "title": "fix: harden phase 6c vault adapter follow-up behavior",
  "url": "https://github.com/xorcon/tracevault/pull/13"
}
```

Main after merge:

```text
main is up to date with origin/main
post-merge tests passed
```

---

## 14. Commands Used

### Branch setup

```bash
git checkout main
git pull origin main
git checkout -b feat/phase-6c-obsidian-vault-adapter
```

### Validation commands

```bash
python3 -m pytest tests/unit/test_wiki_vault_adapter.py tests/unit/test_wiki_vault_cli.py -q
python3 -m pytest tests/unit/test_wiki_health_directory.py tests/unit/test_wiki_vault_adapter.py tests/unit/test_wiki_vault_cli.py -q
python3 -m pytest -q
python3 -m ruff check .
python3 -m tracevault diagnose
python3 -m compileall src tests
```

### PR #11 merge

```bash
gh pr merge 11 --squash --delete-branch
```

### PR #12 conflict recovery

```bash
git rebase origin/main
git rebase --abort
git checkout -b fix/phase-6c-vault-followup-clean origin/main
git cherry-pick 8bc2265
git cherry-pick aaecad8
git cherry-pick b95e2d4
git push -u origin fix/phase-6c-vault-followup-clean
gh pr create --base main --head fix/phase-6c-vault-followup-clean
gh pr close 12 --comment "Closing in favor of clean branch rebased from current main..."
```

### PR #13 merge and post-merge validation

```bash
gh pr merge 13 --squash --delete-branch
git checkout main
git pull origin main
python3 -m pytest -q
python3 -m ruff check .
python3 -m tracevault diagnose
python3 -m compileall src tests
gh pr view 13 --json number,state,mergedAt,mergeCommit,title,url
```

---

## 15. Acceptance Gates

### Gate 1 — Scope Gate

Must verify no:

```text
Obsidian plugin
Obsidian runtime dependency
.obsidian config generation
LLM calls
reasoning
answer generation
claim rewriting
evidence rewriting
private vault content
generated vault output committed
```

Result:

```text
Passed.
```

### Gate 2 — Preflight Gate

Must verify:

```text
Phase 6B health preflight runs by default
unhealthy notes fail closed
generated vault output under configured vault_dir is excluded
real source content outside vault_dir is not hidden
```

Result:

```text
Passed after path-scoped exclusion fixes.
```

### Gate 3 — Copy Integrity Gate

Must verify:

```text
Markdown note content copied byte-for-byte
YAML frontmatter preserved
CRLF/BOM preserved
no claim/evidence rewriting
```

Result:

```text
Passed.
```

### Gate 4 — Collision Gate

Must verify:

```text
duplicate destination detected during planning
case-only collisions rejected
apply-time defensive collision validation exists
CLI returns non-zero on collision
```

Result:

```text
Passed.
```

### Gate 5 — Manifest / Index Gate

Must verify:

```text
manifest is deterministic
indexes are metadata-only
index generation does not create knowledge
manifest/index only written after successful note copy
stale manifest/index cleaned on failed apply
ownership markers prevent deleting user-authored files
```

Result:

```text
Passed after PR #13 hardening.
```

### Gate 6 — Filesystem Safety Gate

Must verify:

```text
no TraceVault/Notes deletion
no recursive deletion
no user-authored reserved index deletion
no non-adapter manifest deletion
no malformed manifest deletion
reserved paths validated before overwrite
generate_index=False semantics preserved
```

Result:

```text
Passed.
```

### Gate 7 — CLI Contract Gate

Must verify:

```text
wiki-vault-plan writes nothing
wiki-vault-adapt non-destructive by default
--json emits one valid JSON document
non-zero on health failure, collision, rejected notes, write failures
```

Result:

```text
Passed.
```

### Gate 8 — Review Gate

Must verify:

```text
Codex Critical Issues: None
Codex Important Issues: None
Codex Merge Recommendation: Approve / Mergeable
```

Result:

```text
Passed.
```

### Gate 9 — Merge Evidence Gate

Must verify:

```text
PR #13 state = MERGED
mergeCommit captured
mergedAt captured
post-merge pytest passed
post-merge ruff passed
post-merge diagnose passed
post-merge compileall passed
```

Result:

```text
Passed.
```

---

## 16. Failure Patterns and Lessons Learned

### Failure Pattern 1 — Adapter can accidentally become source-of-truth

Risk:

```text
manifest/index can be mistaken for current truth even after failed apply.
```

Lesson:

```text
Generated truth artifacts must be removed or invalidated on failed apply.
```

### Failure Pattern 2 — Name-based exclusion hides user content

Initial issue:

```text
Skipping every directory named TraceVault hid real source notes.
```

Lesson:

```text
Exclude configured paths, never names.
```

### Failure Pattern 3 — Cleanup-time ownership check can be too late

Initial issue:

```text
user-authored index could be overwritten with generated marker before cleanup deleted it.
```

Lesson:

```text
Check ownership before write, not only before delete.
```

### Failure Pattern 4 — Cleanup and validation are different contracts

Initial regression:

```text
generate_index=False was blocked by user-authored index files even though the run would not write indexes.
```

Lesson:

```text
Validation should check only files this run writes.
Cleanup should inspect stale adapter-owned files from previous runs.
```

### Failure Pattern 5 — A failed rerun can fail before copy starts

Initial issue:

```text
cleanup only ran after copy errors.
```

Lesson:

```text
Every failed apply return path must use the same cleanup behavior.
```

### Failure Pattern 6 — Stale artifacts are audit risks

Problem:

```text
old manifest and index could imply a failed run succeeded.
```

Lesson:

```text
Do not leave adapter-owned manifest/index stale after failure.
```

### Failure Pattern 7 — Case-insensitive filesystems need explicit tests

Issue:

```text
A.md and a.md collide on Windows/macOS defaults but not on Linux.
```

Lesson:

```text
Use canonical casefolded destination keys in collision detection.
```

### Failure Pattern 8 — Clean branch beats conflict surgery

Issue:

```text
PR #12 replayed already-merged PR #11 commits and created add/add conflicts.
```

Lesson:

```text
When a branch contains merged base commits, recreate from origin/main and cherry-pick only follow-up commits.
```

### Failure Pattern 9 — Passing tests before push is not enough

Issue:

```text
merge recommendation was premature before latest fixes were committed and pushed.
```

Lesson:

```text
Codex approval must apply to the pushed PR commit, not a local working tree.
```

### Failure Pattern 10 — Small adapter code can create many filesystem edge cases

Observation:

```text
Phase 6C required many tests because filesystem safety depends on state across repeated runs.
```

Lesson:

```text
Adapters need rerun, failure, stale-state, ownership, and cross-platform tests.
```

---

## 17. Reusable SOP for Future Adapter Phases

Use this operating pattern for future adapter/export/sync work.

### Step 1 — Define adapter boundary

```text
What is source?
What is derived?
What is generated?
What is adapter-owned?
What is user-owned?
```

### Step 2 — Preflight before write

```text
validate source artifacts
validate destinations
validate ownership
validate collisions
validate overwrite policy
```

### Step 3 — Use path-scoped exclusions

```text
exclude explicit paths only
never skip by generic directory name
```

### Step 4 — Copy source artifacts byte-for-byte

```text
do not parse/rewrite source notes unless explicitly required
```

### Step 5 — Mark generated artifacts

```text
index marker
manifest generated_by field
machine-readable ownership
```

### Step 6 — Validate ownership before overwrite

```text
if target exists and is not adapter-owned, fail before writing
```

### Step 7 — Cleanup on failed apply

```text
cleanup adapter-owned generated artifacts on every failed apply path
do not delete user-authored files
do not delete source/copied notes
```

### Step 8 — Test reruns

Required cases:

```text
first run success
second run failure
changed config between runs
stale artifacts from prior run
user-authored reserved files
malformed generated files
case-insensitive collision
nested output path
```

### Step 9 — Review through Codex

Ask Codex specifically for:

```text
filesystem safety
source-of-truth risk
stale artifact risk
scope creep
proof-chain mutation
platform compatibility
test gaps
```

### Step 10 — Merge only with evidence

Required evidence:

```text
PR number
state = MERGED
merge commit
mergedAt
pytest result
ruff result
diagnose result
compileall result
Codex final recommendation
```

---

## 18. Summary for Hermes Agent / Open Claw

The correct lesson from Phase 6C:

```text
A vault adapter is a filesystem safety boundary.
It must be deterministic, non-destructive, source-preserving, and honest about failed runs.
```

Future agents must not approve an adapter because it “copies files successfully.”

They must verify:

```text
source artifacts are validated first
real source content is not hidden by broad exclusions
source notes are copied byte-for-byte
generated artifacts are clearly owned
reserved paths are validated before overwrite
stale generated truth artifacts are cleaned on failure
cleanup does not delete user files
all failed apply paths behave consistently
case-insensitive collisions are rejected
CLI exit codes match failure state
generated output is not committed
```

Final Phase 6C status:

```text
Phase: Optional Obsidian Vault Adapter
Primary PR: #11 — MERGED
Follow-up PR: #13 — MERGED
Final merge commit: 1269b805a184b6a61680a90bd7915af89ae02a8d
Merged at: 2026-05-27T17:44:24Z

Final validation:
pytest: 1476 passed
ruff: All checks passed
tracevault diagnose: Package structure OK
compileall: OK
```

TraceVault now has an optional Obsidian-friendly vault adapter that preserves the Phase 6A/6B proof-chain boundary and can organize healthy wiki exports without turning the vault into a new source of truth.

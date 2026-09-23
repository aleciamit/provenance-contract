# Acceptance checklist for whoever builds here next

<!-- Written by the outgoing agent before a model or session changes. The next agent runs EVERY
check below and pastes the results to the owner BEFORE committing anything or saying the work is
ready. Fill in the project specifics; delete nothing without the owner's say. -->

## 1. Leak check: nothing real escapes

- The checker passes: `python3 tools/check.py` reports no SCRUB hits.
- A manual sweep of every output folder for the terms in `SCRUB.local.md` returns zero hits.
- Every name, label, URL and identifier added in this session is fiction or is sourced. If you
  added new strings, re-read them.

## 2. It works, and you name what you tested

- Serve it locally and confirm it loads. Give the owner the address; they verify in their own
  browser.
- State exactly what was tested in the same sentence as the claim: which widths, which data,
  which interaction states. If a case was not checked, say so. Silence is not coverage.

## 3. No collateral damage

- Files the owner did not ask about are unchanged. Show `git status`.
- If a shared class or component was touched, list every other surface that uses it and confirm
  each one.
- The build passes, if there is one.

## 4. The owner's standing rules

- No invented design values: every color and size traces to `DESIGN.md`, a spec dump, or the
  owner's explicit say-so.
- Conflicts are surfaced with both values and options, never resolved on your own.
- Nothing leaves the workspace without a yes: commit, push, publish, delete.

## 5. Report format, then wait

Tell the owner, per change: what changed, each value with its source, the leak-check result
verbatim, and anything you decided that they should get to veto. Then wait at the commit gate.

*Written on YYYY-MM-DD by <model>, at the owner's request, as their guardrail on whoever builds
here next.*

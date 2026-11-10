# Exact-Only Removal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) — this is a small removal, executed task by task with `unittest` as the gate.

**Goal:** Remove the approximate method entirely; the app keeps only the Thevenin (exact) solution.

**Architecture:** `dc_bias.py` returns to a single `solve_dc_bias(inp)` with the Thevenin body; `app.py` stops reading/sending `method`; the template loses the radio group, the method label, and the approximate steps branch.

**Tech Stack:** Python 3.13, Flask 3.1.2, Jinja2, stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-exact-only-design.md`

## Global Constraints

- Reference values (exact): VB 1.942157, VE 1.242157, VC 9.294312, VCE 8.052155,
  IC 1.229858 mA, IB 12.29858 µA, IE 1.242157 mA.
- No occurrence of `method`, `approx`, `METHOD_`, or `DEFAULT_METHOD` remains in
  `dc_bias.py`, `app.py`, `templates/`, `static/`.
- UI copy stays Thai; every displayed value keeps its unit.
- `python -m unittest discover -s tests` must be fully green.
- The agent does not commit (AGENTS.md rule 8).

## File Structure

| File | Change |
|---|---|
| `dc_bias.py` | drop method constants, `normalize_method`, `BiasResult.method`, `method` param, approximate branch |
| `app.py` | drop method imports/context |
| `templates/index.html` | drop picker, method label, approximate steps, approx assumptions copy |
| `static/style.css` | drop `.method-picker`, `.method-option`, `.method-label` |
| `tests/test_dc_bias.py` | delete `ApproximateMethodTests`; drop `method=` args; fold region checks into `SolveTests` |
| `tests/test_web.py` | delete `MethodRoutingTests`; delete method-specific presentation tests; restore exact expectations |
| `README.md`, `docs/validation.md`, `AGENTS.md` | single-method documentation |

---

### Task 1: Solver back to one method

**Files:** `dc_bias.py`, `tests/test_dc_bias.py`

- [x] Step 1: Edit the tests to the target state — remove `normalize_method` from the
      import, call `solve_dc_bias(self.sample())` with no method, delete
      `ApproximateMethodTests`, and delete `RegionBothMethodsTests` after copying its two
      cases into `SolveTests` without a method argument.
- [x] Step 2: Run the engineering tests. Expect `TypeError`/`AttributeError` on
      `method` — RED.
- [x] Step 3: In `dc_bias.py`, delete `METHOD_APPROX`, `METHOD_EXACT`, `METHODS`,
      `DEFAULT_METHOD`, `normalize_method`, the `method` field and parameter, the
      approximate branch, and the approximate note. Keep the Thevenin body as the only
      path; drop `method=method` from the constructor call.
- [x] Step 4: Re-run the engineering tests. Expect PASS.

### Task 2: Route stops carrying a method

**Files:** `app.py`, `tests/test_web.py`

- [x] Step 1: Delete `MethodRoutingTests`; change `test_post_valid_shows_computed_values`
      back to `("1.942", "1.242", "9.294", "8.052", "12.30")`.
- [x] Step 2: Run the web tests. Expect failures from the still-passed `method` context —
      RED.
- [x] Step 3: In `app.py`, remove `DEFAULT_METHOD`, `METHODS`, `normalize_method`, the
      `method`/`methods` context keys, and the `method=` argument to `solve_dc_bias`.
- [x] Step 4: Re-run the web tests. Expect only the presentation tests to fail (Task 3).

### Task 3: Template and CSS lose the picker

**Files:** `templates/index.html`, `static/style.css`

- [x] Step 1: Delete the method-specific tests (`MethodPresentationTests`) and restore
      `test_calculation_steps_are_shown` to assert `RTH`; restore the cutoff steps test's
      `RTH` assertion; point the steps tests at the single block.
- [x] Step 2: Run the web tests. Expect failures on the removed markers — RED.
- [x] Step 3: Remove the fieldset, the `.method-label` paragraph, the `{% elif
      result.method == 'approx' %}` branch, and the two-method assumptions sentence.
      Delete the three CSS rules.
- [x] Step 4: Run the full suite. Expect PASS.
- [x] Step 5: Browser check at `http://127.0.0.1:5000/` — no radio group, VB 1.942 V,
      steps show `RTH` and `VC`.

### Task 4: Documentation

**Files:** `README.md`, `docs/validation.md`, `AGENTS.md`

- [x] Step 1: README — drop the two-method section and its table, restore the single
      formula set, keep the test count accurate.
- [x] Step 2: `docs/validation.md` — single hand calculation and single comparison
      column, A6 counts updated, real test log pasted.
- [x] Step 3: `AGENTS.md` — remove the method-parity rule; state that `dc_bias.py` solves
      only the Thevenin model.
- [x] Step 4: Final `unittest discover` run; report the count.

---

## Self-Review

- Spec acceptance: solver signature (T1), no method plumbing (T1–T2), no picker/label/
  approx steps (T3), docs (T4), green suite (T3 Step 4, T4 Step 4).
- No test is deleted without a replacement unless it tested only the removed feature.
- Leftover-marker sweep: grep for `method|approx` in source and templates before the
  final run.

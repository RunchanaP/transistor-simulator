# Lab 03 Three-Bias-Circuits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Flask Lab 02 app so one page solves Fixed Bias, Emitter Bias, and the unchanged Voltage Divider Bias, with Lab 03 region thresholds and browser-checked A1–A5 cases.

**Architecture:** `dc_bias.py` gains two input dataclasses and two solver functions beside the untouched Divider solver; all three return the same `BiasResult` with a `mode` field. `app.py` normalizes the mode, parses only that mode's fields, and dispatches with `if/elif`. The template renders a mode dropdown, mode-specific fields/schematic/steps, and never shows a stale result after invalid input.

**Tech Stack:** Python 3.13, Flask 3.1.2, Jinja2, stdlib `unittest`, OpenCode Browser for A1–A5.

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-three-bias-circuits-design.md`

## Global Constraints

- Keep `BiasInput`, `parse_inputs()`, and `solve_dc_bias(inp)` exactly as they are so all 23 existing engineering tests and A1 stay unchanged.
- Common values for every A case: `VCC=12 V`, `RC=2.2 kΩ`, `β=100`, `VBE=0.70 V`.
- Region rule for all modes: `IB <= 0` → `cutoff`; otherwise `VCE > 0.2` → `active`, else `saturation`. Set `VCE_SAT = 0.2`.
- Internal mode strings: `"fixed"`, `"emitter"`, `"divider"`. An unknown or missing mode raises `ValidationError({"mode": "โหมดวงจรไม่ถูกต้อง"})` — never defaults to Divider.
- Every displayed quantity keeps a unit; every results-table row has a matching line in the mode's steps block.
- Thai error messages; invalid input returns HTTP 200 with an error panel and no results table.
- Use `unittest` only. `python -m unittest discover -s tests` must be fully green after every task.
- Agent does **not** run `git commit` or `git push` (`AGENTS.md` rule 8). The student commits in GitHub Desktop.
- Agent must not fill in the expected values (`___`) in the A1–A5 table; those come from the student's hand calculation.

## Review Focus

| Failure mode | Behavior expected | Test that pins it |
|---|---|---|
| Unknown/missing `mode` | HTTP 200, Thai error, no results table; not silently Divider | Task 3 `test_unknown_mode_shows_error_and_no_result`, `test_missing_mode_shows_error` |
| Fixed omits `RE`; Emitter omits `R1/R2` | Parsing succeeds using only that mode's fields | Task 1 `test_parse_fixed_ignores_unrelated_fields`, `test_parse_emitter_ignores_unrelated_fields` |
| `RB = 0` / non-numeric `RB` | Thai error, HTTP 200, no stale result from previous submit | Task 1 `test_parse_fixed_rejects_zero_rb`; Task 3 `test_a5_fixed_zero_rb_no_stale_result` |
| Divider A1 regression | Sample still gives `1.942 / 1.242 / 9.294 / 8.052 / 1.230 / 12.30 / 1.242` | Task 2 `test_divider_reference_unchanged`; Task 3 `test_a1_divider_values_unchanged` |
| New `0.2 V` threshold | `VCE = 0.25` is `active` (old `0.3` rule would say saturation); `IB <= 0` is cutoff | Task 2 `test_vce_between_020_and_030_is_active`, `test_ib_nonpositive_is_cutoff` |

## File Structure

| File | Responsibility |
|---|---|
| `dc_bias.py` | All equations, unit conversion, validation, mode normalization, three solvers, shared result shape |
| `app.py` | Mode dispatch, form value retention, error/result context only |
| `templates/index.html` | Mode select, conditional fields, one of three SVGs, mode-specific steps |
| `static/style.css` | Styling for the new select and field groups; no JS/CDN |
| `tests/test_dc_bias.py` | Engineering tests for new parsing and solvers |
| `tests/test_web.py` | HTTP tests for dispatch, field visibility, errors, steps |
| `README.md` | Three-mode run/usage docs with blank reference slots |
| `docs/validation.md` | A1–A5 table with blank expected values and browser evidence columns |
| `AGENTS.md` | Rules updated for three solvers and Lab 03 thresholds |

---

### Task 1: Mode normalization and per-mode parsing

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: existing `BiasInput`, `parse_resistance()`, `_parse_plain()`, `ValidationError`.
- Produces:
  - `MODE_FIXED = "fixed"`, `MODE_EMITTER = "emitter"`, `MODE_DIVIDER = "divider"`, `MODES = (MODE_FIXED, MODE_EMITTER, MODE_DIVIDER)`
  - `FixedInput(vcc: float, rb: float, rc: float, beta: float, vbe: float)` (frozen dataclass)
  - `EmitterInput(vcc: float, rb: float, rc: float, re: float, beta: float, vbe: float)` (frozen dataclass)
  - `MODE_SAMPLES: dict[str, dict[str, str]]` with the values in Spec §4.1
  - `normalize_mode(raw: object) -> str`
  - `parse_fields(raw: Mapping[str, str], required: tuple[str, ...]) -> dict[str, float]`
  - `parse_fixed(raw: Mapping[str, str]) -> FixedInput`
  - `parse_emitter(raw: Mapping[str, str]) -> EmitterInput`
  - `parse_divider(raw: Mapping[str, str]) -> BiasInput`
  - `parse_inputs(raw)` keeps its signature and behavior; it may delegate to `parse_divider`.

- [ ] **Step 1: Write failing tests** in `tests/test_dc_bias.py`

```python
import unittest

from dc_bias import (ValidationError, MODE_SAMPLES, normalize_mode,
                     parse_emitter, parse_fixed)

COMMON = {"vcc": "12", "rc": "2.2k", "beta": "100", "vbe": "0.7"}
A2 = dict(COMMON, rb="1M")
A3 = dict(A2, re="1k")


class ModeParsingTests(unittest.TestCase):
    def test_normalize_mode_accepts_all_three(self):
        self.assertEqual(normalize_mode("fixed"), "fixed")
        self.assertEqual(normalize_mode(" EMITTER "), "emitter")
        self.assertEqual(normalize_mode("divider"), "divider")

    def test_normalize_mode_rejects_unknown(self):
        for raw in ("bogus", "", None):
            with self.assertRaises(ValidationError) as ctx:
                normalize_mode(raw)
            self.assertIn("mode", ctx.exception.errors)

    def test_parse_fixed_ignores_unrelated_fields(self):
        inp = parse_fixed(dict(A2, r1="junk", r2="junk", re="junk"))
        self.assertEqual(inp.rb, 1_000_000.0)
        self.assertEqual(inp.rc, 2200.0)

    def test_parse_emitter_ignores_unrelated_fields(self):
        inp = parse_emitter(dict(A3, r1="junk", r2="junk"))
        self.assertEqual(inp.rb, 1_000_000.0)
        self.assertEqual(inp.re, 1000.0)

    def test_parse_fixed_rejects_zero_rb(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_fixed(dict(A2, rb="0"))
        self.assertEqual(ctx.exception.errors["rb"], "ค่าความต้านทานต้องมากกว่า 0")

    def test_mode_samples_match_worksheet(self):
        self.assertEqual(MODE_SAMPLES["fixed"]["rb"], "1M")
        self.assertEqual(MODE_SAMPLES["emitter"]["re"], "1k")
        self.assertEqual(MODE_SAMPLES["divider"], {
            "vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
            "re": "1k", "beta": "100", "vbe": "0.7",
        })
```

- [ ] **Step 2: Run the new tests, expect RED**

Run: `python -m unittest discover -s tests -p test_dc_bias.py -v`
Expected: import errors / `AttributeError` for `normalize_mode`, `parse_fixed`, `parse_emitter`, `MODE_SAMPLES`.

- [ ] **Step 3: Implement in `dc_bias.py`**

Add the constants, dataclasses, `MODE_SAMPLES`, `normalize_mode`, `parse_fields`, and the three parse functions. `parse_fields` must:
  - use `parse_resistance` for `rb, r1, r2, rc, re` and `_parse_plain` for `vcc, beta, vbe`;
  - ignore keys not in `required` (so irrelevant fields can be blank or garbage);
  - report missing/unparseable field as `"กรุณากรอกตัวเลข"`, non-finite as `"ค่าตัวเลขไม่สมเหตุสมผล"`, resistance `<= 0` as `"ค่าความต้านทานต้องมากกว่า 0"`, `vcc <= 0` as `"VCC ต้องมากกว่า 0"`, `beta <= 0` as `"β ต้องมากกว่า 0"`, `vbe` outside `(0, 2)` as `"VBE ต้องอยู่ระหว่าง 0 ถึง 2 V"`;
  - raise one `ValidationError` containing all failing fields.

Leave `parse_inputs()`/`BiasInput` unchanged in signature; make it call `parse_divider(raw)` internally.

- [ ] **Step 4: Run tests, expect GREEN**

Run: `python -m unittest discover -s tests -p test_dc_bias.py -v`
Expected: all original 23 + new parsing tests pass.

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover -s tests`
Expected: 46 + new tests, `OK`.

---

### Task 2: Three solvers, shared result, Lab 03 thresholds

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `FixedInput`, `EmitterInput`, `BiasInput` from Task 1.
- Produces:
  - `VCE_SAT = 0.2`
  - `BiasResult` with existing fields plus `mode: str = MODE_DIVIDER` as the last field with a default (keeps old positional construction working)
  - `solve_fixed(inp: FixedInput) -> BiasResult`
  - `solve_emitter(inp: EmitterInput) -> BiasResult`
  - `solve_dc_bias(inp: BiasInput) -> BiasResult` unchanged in behavior except `mode="divider"` and the new threshold.

- [ ] **Step 1: Write failing tests** in `tests/test_dc_bias.py`

```python
def test_divider_reference_unchanged(self):
    r = solve_dc_bias(self.sample())
    for attr, expected in (("vb", 1.94216), ("ve", 1.24216), ("vc", 9.29431),
                           ("vce", 8.05216)):
        self.assertAlmostEqual(getattr(r, attr), expected, places=4)
    self.assertAlmostEqual(r.ic * 1e3, 1.22986, places=4)
    self.assertAlmostEqual(r.ib * 1e6, 12.2986, places=3)
    self.assertEqual(r.mode, "divider")

def test_fixed_a2_reference(self):
    r = solve_fixed(FixedInput(vcc=12.0, rb=1e6, rc=2200.0, beta=100.0, vbe=0.7))
    self.assertAlmostEqual(r.ib * 1e6, 11.30, places=2)
    self.assertAlmostEqual(r.ic * 1e3, 1.130, places=3)
    self.assertAlmostEqual(r.ve, 0.0, places=6)
    self.assertAlmostEqual(r.vb, 0.700, places=3)
    self.assertAlmostEqual(r.vc, 9.514, places=3)
    self.assertAlmostEqual(r.vce, 9.514, places=3)
    self.assertEqual(r.region, "active")
    self.assertEqual(r.mode, "fixed")

def test_emitter_a3_reference(self):
    r = solve_emitter(EmitterInput(vcc=12.0, rb=1e6, rc=2200.0,
                                   re=1000.0, beta=100.0, vbe=0.7))
    self.assertAlmostEqual(r.ic * 1e3, 1.026, places=3)
    self.assertAlmostEqual(r.ie * 1e3, 1.037, places=3)
    self.assertAlmostEqual(r.ve, 1.037, places=3)
    self.assertAlmostEqual(r.vb, 1.737, places=3)
    self.assertAlmostEqual(r.vc, 9.742, places=3)
    self.assertAlmostEqual(r.vce, 8.705, places=3)
    self.assertEqual(r.mode, "emitter")

def test_emitter_a4_re_more_means_less_ic(self):
    a3 = solve_emitter(EmitterInput(12.0, 1e6, 2200.0, 1000.0, 100.0, 0.7))
    a4 = solve_emitter(EmitterInput(12.0, 1e6, 2200.0, 2000.0, 100.0, 0.7))
    self.assertLess(a4.ic, a3.ic)
    self.assertAlmostEqual(a4.ic * 1e3, 0.940, places=3)
    self.assertAlmostEqual(a4.vce, 8.033, places=3)

def test_ib_nonpositive_is_cutoff(self):
    r = solve_fixed(FixedInput(vcc=0.5, rb=1e6, rc=2200.0, beta=100.0, vbe=0.7))
    self.assertEqual(r.region, "cutoff")
    self.assertEqual((r.ib, r.ic, r.ie, r.ve), (0.0, 0.0, 0.0, 0.0))
    self.assertEqual(r.vc, 0.5)
    self.assertTrue(r.warnings)

def test_vce_between_020_and_030_is_active(self):
    r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=8544.0,
                                re=1e3, beta=100.0, vbe=0.7))
    self.assertGreater(r.vce, 0.2)
    self.assertLess(r.vce, 0.3)
    self.assertEqual(r.region, "active")
```

- [ ] **Step 2: Run engineering tests, expect RED**

Run: `python -m unittest discover -s tests -p test_dc_bias.py -v`
Expected: `ImportError` for `solve_fixed`/`solve_emitter`; `BiasResult` has no `mode`; `test_vce_between_020_and_030_is_active` fails because current code calls `0.25 V` saturation.

- [ ] **Step 3: Implement the solvers in `dc_bias.py`**

Compute `ib` per mode:
  - Fixed: `(vcc - vbe) / rb`
  - Emitter: `(vcc - vbe) / (rb + (beta + 1) * re)`
  - Divider: existing `(vth - vbe) / (rth + (beta + 1) * re)`

Then share one finishing path: if `ib <= 0`, set currents/`ve` to zero, `vb = vbe` for Fixed/Emitter (or `vth` for Divider), `vc = vcc`, `vce = vcc - ve`, `region = "cutoff"`, and a Thai warning naming `IB ≤ 0`. Otherwise compute `ic, ie, ve, vb, vc, vce` with the worksheet formulas and set `active` when `vce > VCE_SAT`, else `saturation` with a Thai warning mentioning `VCE ≤ 0.2 V`. Set `vth = vcc`, `rth = rb` for Fixed/Emitter (Thevenin equivalent of the base network), keep existing values for Divider. Keep the existing `math.isfinite` guard and VBE advisory note.

- [ ] **Step 4: Run engineering tests, expect GREEN**

Run: `python -m unittest discover -s tests -p test_dc_bias.py -v`
Expected: all engineering tests pass.

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover -s tests`
Expected: `OK`.

---

### Task 3: Flask mode dispatch and request handling

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html` (minimal mode select only; full rendering in Task 4)
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `normalize_mode`, `parse_fixed`, `parse_emitter`, `parse_divider`, `MODE_SAMPLES`, `ValidationError` from Tasks 1–2.
- Produces: `index()` route that passes `values`, `mode`, `result`, `errors`, `sample` to `templates/index.html`. `mode` is always one of the three strings when `result` is non-`None`.

- [ ] **Step 1: Write failing web tests** in `tests/test_web.py`

First add `"mode": "divider"` to the shared `SAMPLE_FORM` dict so the existing 23 Divider tests keep their original intent. The `test_missing_mode_shows_error` below explicitly builds a copy without it.

```python
FIXED = dict(SAMPLE_FORM, mode="fixed", rb="1M")
EMITTER = dict(SAMPLE_FORM, mode="emitter", rb="1M", re="1k")

def test_a1_divider_values_unchanged(self):
    html = self.client.post("/", data=dict(SAMPLE_FORM, mode="divider")).get_data(as_text=True)
    for value in ("1.942", "1.242", "9.294", "8.052", "12.30"):
        self.assertIn(value, html)

def test_a2_fixed_values(self):
    html = self.client.post("/", data=FIXED).get_data(as_text=True)
    self.assertIn("1.130", html)
    self.assertIn("9.514", html)

def test_a3_emitter_values(self):
    html = self.client.post("/", data=EMITTER).get_data(as_text=True)
    self.assertIn("1.026", html)
    self.assertIn("8.705", html)

def test_unknown_mode_shows_error_and_no_result(self):
    resp = self.client.post("/", data=dict(SAMPLE_FORM, mode="bogus"))
    html = resp.get_data(as_text=True)
    self.assertEqual(resp.status_code, 200)
    self.assertIn("โหมดวงจรไม่ถูกต้อง", html)
    self.assertNotIn("results-table", html)

def test_missing_mode_shows_error(self):
    html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
    self.assertIn("โหมดวงจรไม่ถูกต้อง", html)
    self.assertNotIn("results-table", html)

def test_a5_fixed_zero_rb_no_stale_result(self):
    self.assertIn("results-table", self.client.post("/", data=FIXED).get_data(as_text=True))
    html = self.client.post("/", data=dict(FIXED, rb="0")).get_data(as_text=True)
    self.assertIn("ค่าความต้านทานต้องมากกว่า 0", html)
    self.assertNotIn("results-table", html)
```

- [ ] **Step 2: Run web tests, expect RED**

Run: `python -m unittest discover -s tests -p test_web.py -v`
Expected: fixed/emitter values absent; unknown mode falls back to Divider; no error about mode.

- [ ] **Step 3: Implement dispatch in `app.py`**

On POST: call `normalize_mode(request.form.get("mode"))` first inside the `try`. Use `if/elif/else` on `mode` to choose the parser and solver; call the chosen parser on `request.form` and pass its result to the chosen solver. Set `values = {field: request.form.get(field, "") for field in set(NUMERIC_FIELDS) | {"rb"}}` so the form retains what the user typed. On `ValidationError`, set `result = None` and `errors = exc.errors`; otherwise `errors = {}`. Render with `mode=mode`, `sample=MODE_SAMPLES.get(mode, MODE_SAMPLES["divider"])`. On GET, use `mode = MODE_DIVIDER`, `values = MODE_SAMPLES[mode]`, `result = None`, `errors = {}`. Keep all physics in `dc_bias.py`. Also add the minimal `<label for="mode">วงจร</label><select id="mode" name="mode">` with the three options and `selected` driven by `mode` to `templates/index.html` — the updated shared `SAMPLE_FORM` fixture asserts `name="mode"` on GET. Full conditional fields/SVGs/steps stay in Task 4.

- [ ] **Step 4: Run web tests, expect GREEN**

Run: `python -m unittest discover -s tests -p test_web.py -v`
Expected: all web tests pass (existing 23 + new).

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover -s tests`
Expected: `OK`.

---

### Task 4: Template and CSS for mode selection and steps

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `mode`, `values`, `result`, `errors`, `sample` from Task 3; `result.mode` from Task 2.
- Produces: a page where the select has `name="mode"` and `id="mode"`, and the visible input set matches the chosen mode.

- [ ] **Step 1: Add presentation tests** to `tests/test_web.py`

```python
def test_mode_select_has_three_options(self):
    html = self.client.get("/").get_data(as_text=True)
    self.assertIn('name="mode"', html)
    for value in ("fixed", "emitter", "divider"):
        self.assertIn(f'value="{value}"', html)

def test_only_relevant_fields_are_visible(self):
    fixed = self.client.post("/", data=FIXED).get_data(as_text=True)
    self.assertIn('name="rb"', fixed)
    self.assertNotIn('name="r1"', fixed)
    emitter = self.client.post("/", data=EMITTER).get_data(as_text=True)
    self.assertIn('name="rb"', emitter)
    self.assertIn('name="re"', emitter)
    self.assertNotIn('name="r2"', emitter)
    divider = self.client.post("/", data=dict(SAMPLE_FORM, mode="divider")).get_data(as_text=True)
    self.assertIn('name="r1"', divider)
    self.assertNotIn('name="rb"', divider)

def test_steps_match_selected_mode(self):
    fixed = self.client.post("/", data=FIXED).get_data(as_text=True)
    self.assertIn("IB = (VCC − VBE) / RB", fixed)
    self.assertIn("VE = 0", fixed)
    self.assertNotIn("VTH", fixed)
    emitter = self.client.post("/", data=EMITTER).get_data(as_text=True)
    self.assertIn("IB = (VCC − VBE) / (RB + (β+1)·RE)", emitter)
    divider = self.client.post("/", data=dict(SAMPLE_FORM, mode="divider")).get_data(as_text=True)
    self.assertIn("RTH =", divider)

def test_cutoff_steps_state_ib_nonpositive(self):
    html = self.client.post("/", data=dict(FIXED, vcc="0.5")).get_data(as_text=True)
    self.assertIn("IB ≤ 0", html)
    self.assertNotIn("IB = (VCC − VBE) / RB", html)
```

- [ ] **Step 2: Run web tests, expect RED**

Run: `python -m unittest discover -s tests -p test_web.py -v`
Expected: all fields still visible and Divider steps shown for every mode; `test_mode_select_has_three_options` may already pass from Task 3.

- [ ] **Step 3: Update `templates/index.html`**

Keep/refine the `<label for="mode">วงจร</label><select id="mode" name="mode">` added in Task 3 (three options, `{% if mode == '...' %}selected{% endif %}`). Wrap field groups in `{% if mode == ... %}` blocks so only common + that mode's fields render; use `values.<field>` for `value` attributes and `sample.<field>` for the reset link. Replace the single hardcoded SVG with three `{% if %}`-selected SVGs (Fixed: RB/RC; Emitter: RB/RC/RE; Divider: keep existing SVG). Change `<title>`, `<h1>`, and the subtitle to reflect `mode`. Replace the steps block with three branches using the exact formulas in Spec §6.3; for cutoff, print `IB ≤ 0 → Cutoff` and `IB = 0` instead of the active formula. In the Divider cutoff branch also keep the existing `VTH ≤ VBE (...) → Cutoff` line so `test_cutoff_steps_state_the_reason_and_the_zero_current` stays green; the two statements are equivalent. Keep every results-table quantity in each branch.

- [ ] **Step 4: Add minimal CSS and run tests**

Add one `.mode-field` rule group for the select/label spacing in `static/style.css`; no JS, no external assets.

Run: `python -m unittest discover -s tests -p test_web.py -v`
Expected: all web tests pass.

- [ ] **Step 5: Run the full suite and verify in browser**

Run: `python -m unittest discover -s tests`
Expected: `OK`.

Start/reuse the Flask server at `http://127.0.0.1:5000/`, open it with OpenCode Browser, and confirm: three options in the select; Fixed shows `RB` only; Emitter shows `RB` + `RE`; Divider shows `R1/R2/RE` and A1 numbers unchanged; A5 shows the `RB` error with no result table.

---

### Task 5: Documentation and A1–A5 browser evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/validation.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: behavior from Tasks 1–4.
- Produces: docs that a clone can follow and an A1–A5 table whose expected column is blank for the student.

- [ ] **Step 1: Update `README.md`**

Describe the three modes, their fields, the formulas' location in `dc_bias.py`, the `python -m flask --app app run` command, and a sample table with `___` placeholders for IC/VCE of A2–A4. State that Divider output is unchanged from Lab 02.

- [ ] **Step 2: Update `docs/validation.md`**

Copy the A1–A5 table from Spec §4.1 with columns `กรณี | โหมดและค่า | คาดหมาย (นักศึกษา) | เห็นจริง | วิธีตรวจ | สถานะ | หลักฐาน`. Leave the expectation cells as `___`; do not fill them from program output. Add a short note that expected values must be independent hand calculations.

- [ ] **Step 3: Update `AGENTS.md`**

Replace the single-model architecture bullet with three solvers sharing `BiasResult`; change rule 9 to `IB ≤ 0` / `VCE ≤ 0.2`; add rules "unknown mode must error, never default to Divider" and "reference values come from the student, not the program"; update Scope to allow the three Lab 03 bias topologies. Keep rule 8 (no agent commit).

- [ ] **Step 4: Run browser cases A1–A5 and record observations**

Ask the user for the hand-calculated expected `IC`/`VCE` (and the A4 direction) before judging PASS/FAIL. Use OpenCode Browser for whichever cases the user has supplied expectations for; record the observed values and the exact tool used. Mark anything not run as `NOT RUN`. Do not edit source files during this reporting pass.

- [ ] **Step 5: Final verification**

Run: `python -m unittest discover -s tests`
Expected: full suite `OK`. Confirm `git status --short` shows only intended files. Report the count and hand the commit to the student.

---

## Self-Review

- **Spec coverage:** §4 decisions → Tasks 2/3/4; §4.1 A1–A5 and samples → Tasks 1/3/5; §6.1 solvers/result → Tasks 1/2; §6.2 dispatch → Task 3; §6.3 UI/steps → Task 4; §6.4 tests/docs → all tasks; §8 acceptance → Tasks 2–5.
- **Step scan:** each step has one verifiable action; no step writes a full solver body that the signatures and tests do not determine.
- **Type consistency:** `FixedInput`, `EmitterInput`, `BiasInput`, `BiasResult.mode`, `normalize_mode`, `parse_fixed`, `parse_emitter`, `parse_divider`, `solve_fixed`, `solve_emitter` keep the same names and signatures across Tasks 1–4.
- **Review Focus:** all five failure modes are pinned to tests in Tasks 1–3.
- **Proportion:** plan is longer than the spec only because it carries exact signatures and assertion values, which the implementer cannot infer.

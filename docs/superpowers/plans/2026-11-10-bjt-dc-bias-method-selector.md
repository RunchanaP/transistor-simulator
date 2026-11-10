# Method Selector (Approximate / Exact) Implementation Plan

> **SUPERSEDED (2026-11-10):** the feature was removed at the user's request; the app is
> exact-only again. See `2026-11-10-bjt-dc-bias-exact-only.md`. This file is kept as a
> record of the work.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let the student choose the approximate (IB-neglected) or exact (Thevenin) BJT bias method, defaulting to approximate so the page matches the Lab 02 answer key out of the box.

**Architecture:** `dc_bias.py` keeps owning all equations and gains a `method` parameter on `solve_dc_bias`; `app.py` normalises the posted method and passes it through; the template renders a radio group, a method label, and a steps block that changes per method. No new dependency.

**Tech Stack:** Python 3.13, Flask 3.1.2, Jinja2, plain CSS, stdlib `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-method-selector-design.md`

## Global Constraints

- Default method is `approximate` (spec §การตัดสินใจ 1).
- Approximate uses `IC ≈ IE` and `IB = IC/β` (spec §การตัดสินใจ 2, 3).
- Region logic shared: `VTH ≤ VBE` → cutoff, `VCE ≤ 0.3` → saturation (spec §การตัดสินใจ 4).
- Invalid or missing `method` returns HTTP 200 with the approximate result (spec §ยอมรับได้เมื่อ).
- Every displayed value carries a unit; UI copy is Thai; no external JS/fonts/CDN.
- Tests are stdlib `unittest` only; run `python -m unittest discover -s tests -v`.
- The agent never runs `git commit` or `git push` (AGENTS.md rule 8) — the plan's commit steps are performed by the student.

## File Structure

| File | Change |
|---|---|
| `dc_bias.py` | add `METHOD_APPROX`, `METHOD_EXACT`, `METHODS`, `DEFAULT_METHOD`, `normalize_method`, `method` param on `solve_dc_bias`, `method` field on `BiasResult` |
| `app.py` | read `method` from the form, normalise, pass to solver and template |
| `templates/index.html` | radio group, method label under the heading, per-method steps block, hidden `method` echo |
| `static/style.css` | `.method-picker` styling |
| `tests/test_dc_bias.py` | exact tests pinned to `method="exact"`, new approximate tests |
| `tests/test_web.py` | default/exact/invalid method tests, radio state tests |
| `README.md`, `docs/validation.md`, `AGENTS.md` | document both methods and the answer-key reconciliation |

## Review Focus

1. `method` absent from the POST body — a truncated request or a future form edit must yield the approximate result, never a `KeyError` or 500.
2. `method` set to an unknown or differently-cased string (`Exact`, `foo`, empty) — must fall back to approximate, page must not crash.
3. `method` on a GET request — the form must show approximate preselected.
4. Approximate result outside the active region — warning bar must still appear and numbers must still be shown.
5. Switching methods must not change validation behaviour — the same bad input must produce the same Thai error under both methods.

---

### Task 1: Approximate solver and method parameter

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: existing `BiasInput`, `ValidationError`, `SAMPLE_VALUES`, `VCE_SAT`.
- Produces:
  - `METHOD_APPROX = "approx"`, `METHOD_EXACT = "exact"`, `METHODS = (METHOD_APPROX, METHOD_EXACT)`, `DEFAULT_METHOD = METHOD_APPROX`
  - `normalize_method(raw) -> str` (returns one of `METHODS`; unknown/None/blank → `DEFAULT_METHOD`; case-insensitive)
  - `solve_dc_bias(inp: BiasInput, method: str = DEFAULT_METHOD) -> BiasResult`
  - `BiasResult.method: str`

- [x] **Step 1: Write the failing tests**

```python
APPROX_SAMPLE = BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3,
                          beta=100.0, vbe=0.7)


class ApproximateMethodTests(unittest.TestCase):
    def test_approximate_reference_operating_point(self):
        r = solve_dc_bias(APPROX_SAMPLE)          # default method
        self.assertAlmostEqual(r.vth, 2.16393, places=4)
        self.assertAlmostEqual(r.vb, 2.16393, places=4)   # VB = VTH
        self.assertAlmostEqual(r.ve, 1.46393, places=4)
        self.assertAlmostEqual(r.ie * 1e3, 1.46393, places=4)
        self.assertAlmostEqual(r.ic * 1e3, 1.46393, places=4)   # IC ~ IE
        self.assertAlmostEqual(r.ib * 1e6, 14.6393, places=3)   # IC / beta
        self.assertAlmostEqual(r.vc, 8.77935, places=4)
        self.assertAlmostEqual(r.vce, 7.31542, places=4)
        self.assertEqual(r.region, "active")
        self.assertEqual(r.method, "approx")

    def test_approximate_ic_does_not_depend_on_beta(self):
        lo = solve_dc_bias(BiasInput(**{**APPROX_SAMPLE.__dict__, "beta": 50.0}))
        hi = solve_dc_bias(BiasInput(**{**APPROX_SAMPLE.__dict__, "beta": 500.0}))
        self.assertAlmostEqual(lo.ic, hi.ic, places=12)
        self.assertLess(hi.ib, lo.ib)          # IB = IC/beta still shrinks

    def test_default_method_is_approximate(self):
        self.assertEqual(solve_dc_bias(APPROX_SAMPLE).method, "approx")

    def test_explicit_exact_keeps_the_previous_numbers(self):
        r = solve_dc_bias(APPROX_SAMPLE, method="exact")
        self.assertAlmostEqual(r.vb, 1.94216, places=4)
        self.assertAlmostEqual(r.ic * 1e3, 1.22986, places=4)
        self.assertEqual(r.method, "exact")

    def test_normalize_method_falls_back_to_approximate(self):
        for raw in (None, "", "   ", "foo", "Approximate-ish"):
            self.assertEqual(normalize_method(raw), "approx")
        self.assertEqual(normalize_method("EXACT"), "exact")
        self.assertEqual(normalize_method("approx"), "approx")
```

- [x] **Step 2: Run to verify it fails**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -p test_dc_bias.py -v"`
Expected: `ImportError: cannot import name 'normalize_method'`

- [x] **Step 3: Implement in `dc_bias.py`**

Add the method constants and `normalize_method`. Add `method: str` as the last field of `BiasResult`. In `solve_dc_bias`, branch on the normalised method: exact keeps the current Thevenin body; approximate computes `vb = vth`, `ve = vb - vbe`, `ie = ve / re`, `ic = ie`, `ib = ic / beta`, `vc = vcc - ic * rc`, `vce = vc - ve`. Both branches return `method=normalized`.

- [x] **Step 4: Run to verify it passes**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -p test_dc_bias.py -v"`
Expected: PASS (existing exact tests updated in Task 2 to pass `method="exact"`).

---

### Task 2: Region logic under both methods

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `solve_dc_bias(inp, method)` from Task 1.
- Produces: no new names; cutoff/saturation behave identically in both methods.

- [x] **Step 1: Pin the existing exact tests to the exact method**

Change every existing `solve_dc_bias(self.sample())` call in `test_dc_bias.py` to `solve_dc_bias(self.sample(), method="exact")` so the historical reference values stay meaningful.

- [x] **Step 2: Write the failing tests**

```python
class RegionBothMethodsTests(unittest.TestCase):
    def cutoff_input(self):
        return BiasInput(vcc=12.0, r1=100e3, r2=1e3, rc=2.2e3, re=1e3,
                         beta=100.0, vbe=0.7)

    def saturation_input(self):
        return BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=10e3, re=1e3,
                         beta=100.0, vbe=0.7)

    def test_cutoff_in_both_methods(self):
        for method in ("approx", "exact"):
            r = solve_dc_bias(self.cutoff_input(), method=method)
            self.assertEqual(r.region, "cutoff", method)
            self.assertEqual((r.ib, r.ic, r.ie, r.ve), (0.0, 0.0, 0.0, 0.0), method)
            self.assertAlmostEqual(r.vc, 12.0, places=12)
            self.assertTrue(r.warnings, method)

    def test_saturation_in_both_methods(self):
        for method in ("approx", "exact"):
            r = solve_dc_bias(self.saturation_input(), method=method)
            self.assertEqual(r.region, "saturation", method)
            self.assertLessEqual(r.vce, 0.3, method)
            self.assertTrue(r.warnings, method)
```

- [x] **Step 3: Run to verify it fails**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -p test_dc_bias.py -v"`
Expected: FAIL on `test_saturation_in_both_methods` (approximate branch has no region rule yet) or `AttributeError` on `method`.

- [x] **Step 4: Implement the shared region rule**

Compute region after the method branch: if `vth <= vbe` use the cutoff result for both methods; else compute the method's numbers, then `region = "active" if vce > VCE_SAT else "saturation"`.

- [x] **Step 5: Run to verify it passes**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -p test_dc_bias.py -v"`
Expected: PASS.

---

### Task 3: Route carries the method

**Files:**
- Modify: `app.py`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `normalize_method`, `solve_dc_bias(inp, method)` from Tasks 1–2.
- Produces: template context gains `method` (the normalised string) and `methods` (the `METHODS` tuple); context keys stay `values`, `result`, `errors`, `sample`, `method`, `methods`.

- [x] **Step 1: Write the failing tests**

```python
class MethodRoutingTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_missing_method_defaults_to_approximate(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        self.assertIn("2.164", html)
        self.assertNotIn("1.942", html)

    def test_explicit_exact_changes_the_numbers(self):
        html = self.client.post("/", data=dict(SAMPLE_FORM, method="exact")).get_data(as_text=True)
        self.assertIn("1.942", html)
        self.assertNotIn("2.164", html)

    def test_unknown_method_falls_back_to_approximate(self):
        resp = self.client.post("/", data=dict(SAMPLE_FORM, method="bogus"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("2.164", resp.get_data(as_text=True))
```

- [x] **Step 2: Run to verify it fails**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -p test_web.py -v"`
Expected: FAIL — page still shows 1.942 for a POST without `method`.

- [x] **Step 3: Implement in `app.py`**

Read `request.form.get("method")`, pass it through `normalize_method`, give it to `solve_dc_bias`, and add `method` plus `methods` to both `render_template` calls (GET uses `DEFAULT_METHOD`).

- [x] **Step 4: Run to verify it passes**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -p test_web.py -v"`
Expected: PASS for the three new tests, and the older measurement tests updated in Task 4.

---

### Task 4: Radio group, method label, per-method steps

**Files:**
- Modify: `templates/index.html`, `static/style.css`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `method`, `methods`, `result.method` from Task 3.
- Produces: HTML markers `method-picker`, `name="method"`, `value="approx"`, `value="exact"`, and step-block markers `ขั้นตอนคำนวณ (วิธีประมาณ)` / `ขั้นตอนคำนวณ (วิธีแม่นยำ)`.

- [x] **Step 1: Write the failing tests**

```python
class MethodPresentationTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
    # assert: GET has both radio values and approx checked;
    # POST exact checks the exact radio;
    # approx steps block contains "VB  = VTH" and not "RTH";
    # exact steps block contains "RTH".
```

Write each as its own test method with these exact assertions:
- `test_get_preselects_approximate`: `value="approx"` and `checked` appear in the same input tag; `value="exact"` present.
- `test_exact_post_checks_the_exact_radio`: POST `method=exact` → the `value="exact"` input carries `checked`.
- `test_approximate_steps_do_not_show_rth`: default POST → steps block has `VB  = VTH` and lacks `RTH =`.
- `test_exact_steps_show_rth`: POST `method=exact` → steps block contains `RTH =`.
- `test_result_label_names_the_method`: default POST → `วิธีประมาณ`; exact POST → `วิธีแม่นยำ`.

- [x] **Step 2: Run to verify it fails**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -p test_web.py -v"`
Expected: FAIL on the radio and steps tests.

- [x] **Step 3: Implement the template and CSS**

Add a `.method-picker` fieldset above the numeric fields with two radios (`name="method"`), the approximate one checked when `method == "approx"`. Show a small label `คำนวณด้วย: วิธีประมาณ (ตัด IB)` / `คำนวณด้วย: วิธีแม่นยำ (Thevenin)` above the results. Branch the steps block: approximate shows `VB = VTH`, `VE = VB − VBE`, `IE = VE/RE`, `IC ≈ IE`, `VCE = VCC − IC(RC+RE)`, `IB = IC/β`; exact keeps the current block. Style the fieldset to match the existing field rhythm.

- [x] **Step 4: Update the older measurement assertions to approximate numbers**

`test_post_valid_shows_computed_values` becomes `("2.164", "1.464", "8.779", "7.315")`, and the UI audit values that referenced 1.942/9.294/8.052 move to an exact-method test.

- [x] **Step 5: Run the full suite**

Run: `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -v"`
Expected: PASS, 0 failures.

- [x] **Step 6: Check the page in the browser**

Open `http://127.0.0.1:5000/`, confirm approximate is preselected and shows VB 2.164 V / VE 1.464 V / VCE 7.315 V; switch to exact and confirm VB 1.942 V / VCE 8.052 V.

---

### Task 5: Documentation and conventions

**Files:**
- Modify: `README.md`, `docs/validation.md`, `AGENTS.md`

- [x] **Step 1: README** — add a "สองวิธีคำนวณ" section with the two formula sets, the table of reference results, the statement that approximate is the default, and an explicit note that the Lab 02 answer key (VB ≈ 2.2 V) is the approximate method while the exact method gives 1.942 V; update the test count.
- [x] **Step 2: validation.md** — add both reference columns to the comparison table and state that A3 is satisfied under each declared model.
- [x] **Step 3: AGENTS.md** — add a rule: both methods must keep working, the default is approximate, and any new equation must be added to both branches or explicitly marked method-specific.
- [x] **Step 4: Run the suite one last time** — `cmd /c ".venv\Scripts\python.exe -m unittest discover -s tests -v"` → PASS.

---

## Self-Review

- Spec coverage: default approximate (T1, T3), IC≈IE + IB=IC/β (T1), shared region logic (T2), invalid method → 200 approximate (T3), steps per method + label (T4), docs (T5).
- Type consistency: `normalize_method`, `solve_dc_bias(inp, method)`, `BiasResult.method`, template keys `method`/`methods` are used with the same spelling in every task.
- Review Focus: items 1–2 → T3 invalid/missing tests; 3 → T4 GET preselection; 4 → T2 cutoff/saturation under both methods; 5 → T3 reuses the same validation path, asserted by the existing error tests running unchanged.

# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-file Flask web app that computes the DC operating point of an NPN BJT common-emitter amplifier with voltage-divider bias, with validated Thai UI, region warnings, and automated tests.

**Architecture:** One Flask route handles `GET /` (form) and `POST /` (calculate). All mathematics and input parsing live in a pure module `dc_bias.py` that knows nothing about Flask or HTML; `app.py` only calls it and formats for display; Jinja renders results and a "ขั้นตอนคำนวณ" (calculation steps) block.

**Tech Stack:** Python 3.13.17, Flask (pinned in `requirements.txt`), Jinja2 templates, plain CSS, standard-library `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-web-app-design.md`

## Global Constraints

- Python **3.13.17**; Flask installed only inside `.venv` at the repo root — never into system site-packages.
- Tests use the **standard library `unittest`** only. No pytest, no extra test dependencies.
- Full test command: `python -m unittest discover -s tests -v` from the repo root, run with `.venv\Scripts\python.exe`.
- Server binds **127.0.0.1:5000** only.
- UI text is **Thai**; all displayed quantities carry a unit (`V`, `mA`, `µA`, `Ω`, `kΩ`).
- No CDN, no external fonts/images/JS — the page must render fully offline.
- Palette: navy `#103658`, blue `#1d638b`, teal `#0c8078`, paper `#f5f8fc`, ink `#17344b`, line `#d3e0ec`, warning orange `#b85c2c` / `#fff4e9`, success green `#178875` / `#e9f6f2`.
- **The agent never runs `git commit` or `git push`.** The student commits in GitHub Desktop. Steps marked *STUDENT* are handoffs, not agent actions.
- Shell prerequisite: the OpenCode server predates the Python/Git install, so every `shell` call must start with
  `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`
- Call the interpreter as `.venv\Scripts\python.exe` (never `Activate.ps1`, which execution policy may block).

## Review Focus

Inputs and conditions the spec implies but no requirement spell out; each gets a test in the task that owns the code.

1. **A form field missing entirely from the POST body** — a browser always sends all fields, but a truncated request or a future form edit must produce a readable error, not a `KeyError` traceback.
2. **Non-numeric or Thai text typed into a numeric field** (`r1=หนึ่งร้อย`) — must show the field error, never a 500.
3. **Whitespace and thousands separators** (` 100k `, `1,000`) — surrounding spaces must be tolerated; commas must be rejected with a clear message rather than silently misparsed.
4. **Absurdly long input string** (10 000 characters) — must not hang or 500.
5. **`VTH` exactly equal to `VBE`** — the boundary between cutoff and forward-active must be decided deterministically (cutoff), and a test must pin it.

---

## Task 1: Project skeleton, virtual environment, and repository

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `tests/` (empty directory kept by the first test file in Task 2)

**Interfaces:**
- Consumes: nothing.
- Produces: an importable working directory where `.venv\Scripts\python.exe` can import `flask`, and a git repository root at `transistor-simulator\`.

- [ ] **Step 1: Create the directory structure**

```powershell
cd "C:\Users\B6829780\Documents\Default Project\transistor-simulator"
New-Item -ItemType Directory -Force -Path "templates","static","tests","docs" | Out-Null
```

- [ ] **Step 2: Create `requirements.txt`**

```
Flask==3.1.2
```

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
Thumbs.db
desktop.ini
```

- [ ] **Step 4: Create the virtual environment and install Flask**

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- [ ] **Step 5: Verify Flask imports in the venv**

Run: `.venv\Scripts\python.exe -c "import flask; print(flask.__version__)"`
Expected: `3.1.2`

- [ ] **Step 6: Initialise the git repository (no commit)**

```powershell
git init
git status
```

Expected: `Initialized empty Git repository`, and `git status` lists `requirements.txt`, `.gitignore` as untracked, with `.venv/` **not** listed.

- [ ] **Step 7: *STUDENT* — first commit in GitHub Desktop**

Open GitHub Desktop → **File → Add Local Repository** → select `transistor-simulator` → Commit message `chore: project skeleton with venv and requirements` → **Commit to main**. (Publish later, after Task 6.)

---

## Task 2: Input parsing and validation in `dc_bias.py`

**Files:**
- Create: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class ValidationError(Exception)` with attribute `errors: dict[str, str]` mapping form field name → Thai message.
  - `@dataclass(frozen=True) class BiasInput` with float fields `vcc, r1, r2, rc, re, beta, vbe` (resistances already in ohms).
  - `def parse_resistance(text: str) -> float` — raises `ValueError` on unusable text.
  - `def parse_inputs(raw: Mapping[str, str]) -> BiasInput` — raises `ValidationError`.
  - Module constants `VCE_SAT = 0.3`, `SAMPLE_VALUES: dict[str, str]`.

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from dc_bias import ValidationError, parse_inputs, parse_resistance

VALID = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
         "re": "1k", "beta": "100", "vbe": "0.7"}


class ParseResistanceTests(unittest.TestCase):
    def test_kilo_suffix(self):
        self.assertEqual(parse_resistance("100k"), 100_000.0)
        self.assertEqual(parse_resistance("2.2K"), 2_200.0)
        self.assertEqual(parse_resistance("22kΩ"), 22_000.0)

    def test_mega_suffix(self):
        self.assertEqual(parse_resistance("1M"), 1_000_000.0)
        self.assertEqual(parse_resistance("1meg"), 1_000_000.0)

    def test_bare_number_is_ohms(self):
        self.assertEqual(parse_resistance("2200"), 2_200.0)
        self.assertEqual(parse_resistance(" 2200 "), 2_200.0)

    def test_ohm_symbol_is_stripped(self):
        self.assertEqual(parse_resistance("2200Ω"), 2_200.0)

    def test_lowercase_m_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_resistance("5m")

    def test_thousands_separator_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_resistance("1,000")

    def test_thai_text_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_resistance("หนึ่งร้อย")


class ParseInputsTests(unittest.TestCase):
    def test_sample_values_parse_to_ohms(self):
        inp = parse_inputs(VALID)
        self.assertEqual(inp.r1, 100_000.0)
        self.assertEqual(inp.rc, 2_200.0)
        self.assertEqual(inp.beta, 100.0)
        self.assertEqual(inp.vbe, 0.7)

    def test_missing_field_is_collected(self):
        raw = dict(VALID)
        del raw["r2"]
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(raw)
        self.assertIn("r2", ctx.exception.errors)

    def test_zero_and_negative_resistance_are_collected(self):
        raw = dict(VALID, r1="0", re="-1")
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(raw)
        self.assertIn("r1", ctx.exception.errors)
        self.assertIn("re", ctx.exception.errors)

    def test_negative_beta_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, beta="-5"))
        self.assertIn("beta", ctx.exception.errors)

    def test_non_positive_vcc_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, vcc="0"))
        self.assertIn("vcc", ctx.exception.errors)

    def test_vbe_out_of_range_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, vbe="2.5"))
        self.assertIn("vbe", ctx.exception.errors)

    def test_non_finite_value_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, r1="inf"))
        self.assertIn("r1", ctx.exception.errors)

    def test_out_of_band_value_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, r1="1e13"))
        self.assertIn("r1", ctx.exception.errors)

    def test_thai_text_in_field_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, r1="หนึ่งร้อย"))
        self.assertIn("r1", ctx.exception.errors)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: Implement the parsing half of `dc_bias.py`**

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

VCE_SAT = 0.3            # typical silicon VCE(sat); a model threshold, not a device value
MAX_VCC = 1e4            # V
MAX_RESISTANCE = 1e12    # ohm
MAX_BETA = 1e5

SAMPLE_VALUES = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                 "re": "1k", "beta": "100", "vbe": "0.7"}

RESISTANCE_FIELDS = ("r1", "r2", "rc", "re")


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(f"{len(errors)} invalid field(s)")


@dataclass(frozen=True)
class BiasInput:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


def parse_resistance(text: str) -> float:
    """'100k' -> 100000.0, '2.2k' -> 2200.0, '1M' -> 1e6, '2200' -> 2200.0.

    Raises ValueError for anything else, including a lowercase 'm' (milli vs mega
    is ambiguous) and thousands separators.
    """
```

Implementation note for the body: strip whitespace, strip a trailing `Ω`, `ohm`, or `Ohm`
(case-insensitive), then a trailing `meg`, `k`/`K`, `M`, or `m` decides the multiplier;
bare numbers are ohms. A trailing lowercase `m` raises `ValueError("ไม่รองรับหน่วย m ...")`.
Wrap `float()` in `try/except ValueError` and re-raise `ValueError("กรุณากรอกตัวเลข")`.
Finiteness is **not** checked here — `parse_inputs` owns that rule, so `parse_resistance`
stays a pure text-to-number function.

- [ ] **Step 4: Implement `parse_inputs`**

Rules (each failing field is collected into `errors`, never raised one at a time):

| Field | Rule | Message |
|---|---|---|
| any | absent, or `parse_resistance`/`float` raises | `กรุณากรอกตัวเลข` |
| any | `not math.isfinite`, or outside its band | `ค่าตัวเลขไม่สมเหตุสมผล` || `vcc` | `<= 0` or `> MAX_VCC` | `VCC ต้องมากกว่า 0` |
| `r1/r2/rc/re` | `<= 0` or `> MAX_RESISTANCE` | `ค่าความต้านทานต้องมากกว่า 0` |
| `beta` | `<= 0` or `> MAX_BETA` | `β ต้องมากกว่า 0` |
| `vbe` | `<= 0` or `>= 2` | `VBE ต้องอยู่ระหว่าง 0 ถึง 2 V` |

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: PASS, 16 tests.

- [ ] **Step 6: *STUDENT* — commit in GitHub Desktop**

Message: `feat: input parsing and validation for DC bias`

---

## Task 3: DC operating point and region classification

**Files:**
- Modify: `dc_bias.py` (append)
- Test: `tests/test_dc_bias.py` (append a new class)

**Interfaces:**
- Consumes: `BiasInput`, `VCE_SAT` from Task 2.
- Produces: `@dataclass(frozen=True) class BiasResult` with float fields `vth, rth, ib, ic, ie, vb, ve, vc, vce`, `region: str` (`"active" | "cutoff" | "saturation"`), `warnings: list[str]`, `notes: list[str]`; and `def solve_dc_bias(inp: BiasInput) -> BiasResult`.

- [ ] **Step 1: Write the failing tests**

```python
from dc_bias import BiasInput, solve_dc_bias


class SolveTests(unittest.TestCase):
    def sample(self):
        return BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3,
                         re=1e3, beta=100.0, vbe=0.7)

    def test_reference_operating_point(self):
        r = solve_dc_bias(self.sample())
        self.assertAlmostEqual(r.vth, 2.16393, places=4)
        self.assertAlmostEqual(r.rth, 18_032.79, delta=0.05)
        self.assertAlmostEqual(r.ib * 1e6, 12.2986, places=3)
        self.assertAlmostEqual(r.ic * 1e3, 1.22986, places=4)
        self.assertAlmostEqual(r.ie * 1e3, 1.24216, places=4)
        self.assertAlmostEqual(r.ve, 1.24216, places=4)
        self.assertAlmostEqual(r.vb, 1.94216, places=4)
        self.assertAlmostEqual(r.vc, 9.29431, places=4)
        self.assertAlmostEqual(r.vce, 8.05216, places=4)
        self.assertEqual(r.region, "active")
        self.assertEqual(r.warnings, [])

    def test_kirchhoff_relations_hold(self):
        r = solve_dc_bias(self.sample())
        self.assertAlmostEqual(r.vb, r.ve + 0.7, places=6)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=6)
        self.assertAlmostEqual(r.ic, 100 * r.ib, places=9)
        self.assertAlmostEqual(r.ie, 101 * r.ib, places=9)

    def test_cutoff_when_vth_not_above_vbe(self):
        r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=1e3, rc=2.2e3,
                                    re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "cutoff")
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.ve, 0.0)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)
        self.assertTrue(r.warnings)

    def test_cutoff_at_exact_boundary(self):
        # r1 = r2 with vcc = 1.4 gives VTH = 0.7 exactly -> cutoff
        r = solve_dc_bias(BiasInput(vcc=1.4, r1=10e3, r2=10e3, rc=1e3,
                                    re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "cutoff")
        self.assertEqual(r.ic, 0.0)

    def test_saturation_warning_when_vce_low(self):
        r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=10e3,
                                    re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "saturation")
        self.assertTrue(r.warnings)
        self.assertLess(r.vce, 0.3)

    def test_unusual_vbe_goes_to_notes_not_warnings(self):
        r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3,
                                    re=1e3, beta=100.0, vbe=1.0))
        self.assertEqual(r.region, "active")
        self.assertEqual(r.warnings, [])
        self.assertTrue(r.notes)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: FAIL — `ImportError: cannot import name 'BiasResult'`

- [ ] **Step 3: Implement `BiasResult` and `solve_dc_bias`**

```python
@dataclass(frozen=True)
class BiasResult:
    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: list[str]
    notes: list[str]
```

Algorithm, in this order:

1. `vth = vcc * r2 / (r1 + r2)`; `rth = r1 * r2 / (r1 + r2)`.
2. If `vth <= vbe` → **cutoff**: `ib = ic = ie = 0`, `ve = 0`, `vb = vth`, `vc = vcc`, `vce = vcc`, `region = "cutoff"`, one warning saying the transistor is cut off and the forward-active model does not apply.
3. Else compute `ib = (vth - vbe) / (rth + (beta + 1) * re)`, `ic = beta * ib`, `ie = (beta + 1) * ib`, `ve = ie * re`, `vb = ve + vbe`, `vc = vcc - ic * rc`, `vce = vc - ve`.
4. Region: `"active"` if `vce > VCE_SAT`, otherwise `"saturation"` with a warning stating that `VCE` is below `VCE(sat) ≈ 0.2–0.3 V` and the shown numbers come from the forward-active model so they do not describe the real circuit.
5. `notes`: one entry when `vbe` is outside `0.5–0.9 V` (unusual for a silicon BJT), empty otherwise. `warnings` stays empty for an active operating point.
6. Guard: if any computed value is not `math.isfinite`, raise `ValidationError({"__all__": "ค่าที่คำนวณได้ไม่สมเหตุสมผล"})`.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_dc_bias.py" -v`
Expected: PASS, 22 tests.

- [ ] **Step 5: *STUDENT* — commit in GitHub Desktop**

Message: `feat: DC operating point solver with region classification`

---

## Task 4: Flask route and minimal template

**Files:**
- Create: `app.py`
- Create: `templates/index.html` (minimal version; Task 5 restyles it)
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `parse_inputs`, `solve_dc_bias`, `ValidationError`, `SAMPLE_VALUES` from Tasks 2–3.
- Produces: module-level `app` (a `Flask` instance) importable as `from app import app`; form field names `vcc, r1, r2, rc, re, beta, vbe`; a Jinja context with `values` (dict of raw strings), `result` (`BiasResult | None`), `errors` (dict), `sample` (`SAMPLE_VALUES`).

- [ ] **Step 1: Write the failing tests**

```python
import unittest
from app import app

SAMPLE_FORM = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
               "re": "1k", "beta": "100", "vbe": "0.7"}


class WebTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        for field in SAMPLE_FORM:
            self.assertIn(f'name="{field}"', html)
        self.assertIn("Calculate DC Bias", html)

    def test_post_valid_shows_computed_values(self):
        resp = self.client.post("/", data=SAMPLE_FORM)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        for value in ("1.942", "1.242", "9.294", "8.052", "1.230"):
            self.assertIn(value, html)

    def test_post_zero_resistance_shows_error(self):
        resp = self.client.post("/", data=dict(SAMPLE_FORM, r1="0"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ต้องมากกว่า 0", resp.get_data(as_text=True))

    def test_post_missing_field_shows_error(self):
        data = dict(SAMPLE_FORM)
        del data["beta"]
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("กรุณากรอกตัวเลข", resp.get_data(as_text=True))

    def test_post_thai_text_shows_error(self):
        resp = self.client.post("/", data=dict(SAMPLE_FORM, r1="หนึ่งร้อย"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("กรุณากรอกตัวเลข", resp.get_data(as_text=True))

    def test_post_thousands_separator_shows_error(self):
        resp = self.client.post("/", data=dict(SAMPLE_FORM, r1="1,000"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("กรุณากรอกตัวเลข", resp.get_data(as_text=True))

    def test_post_non_finite_shows_error(self):
        resp = self.client.post("/", data=dict(SAMPLE_FORM, r1="inf"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ไม่สมเหตุสมผล", resp.get_data(as_text=True))

    def test_post_very_long_input_does_not_crash(self):
        resp = self.client.post("/", data=dict(SAMPLE_FORM, r1="9" * 10_000))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ไม่สมเหตุสมผล", resp.get_data(as_text=True))
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Implement `app.py`**

```python
from flask import Flask, render_template, request
from dc_bias import SAMPLE_VALUES, ValidationError, parse_inputs, solve_dc_bias

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    ...
```

Body rules:
- `GET` → `render_template("index.html", values=SAMPLE_VALUES, result=None, errors={}, sample=SAMPLE_VALUES)`.
- `POST` → keep `values = dict(request.form)`; `try: result = solve_dc_bias(parse_inputs(request.form))` except `ValidationError as exc:` → `result = None`, `errors = exc.errors`.
- Always return HTTP 200, even on invalid input (A4 requires the page not to break).
- Formatting for display happens here or in Jinja; keep the math module free of presentation. Values: volts to 3 dp, mA to 3 dp, µA to 2 dp, `rth` in kΩ to 2 dp.

- [ ] **Step 4: Create the minimal `templates/index.html`**

A `<!doctype html>` page in Thai with a `<form method="post">` containing one labelled input per field name above, a submit button reading `Calculate DC Bias`, an error block that lists `errors` when non-empty, and a results table rendering `result` when it is not `None` with rows `VB, VE, VC, VCE, IC, IB, IE` and their units. No CSS link yet.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: PASS, 8 tests.

- [ ] **Step 6: Run the whole suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS, 30 tests.

- [ ] **Step 7: *STUDENT* — commit in GitHub Desktop**

Message: `feat: Flask route renders DC bias results from Python`

---

## Task 5: Full page layout, styling, and calculation-steps block

**Files:**
- Modify: `templates/index.html` (full version)
- Create: `static/style.css`
- Test: `tests/test_web.py` (append a class)

**Interfaces:**
- Consumes: the context from Task 4.
- Produces: CSS classes used by tests — `.warning-bar` (amber region warning), `.region-active` (green pill), `.error-panel`, `.steps` (calculation-steps block), `.results-table`.

- [ ] **Step 1: Write the failing tests**

```python
class PresentationTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_stylesheet_is_linked(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("/static/style.css", html)

    def test_active_region_shows_green_pill(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        self.assertIn("region-active", html)
        self.assertNotIn("warning-bar", html)

    def test_saturation_shows_warning_bar(self):
        html = self.client.post("/", data=dict(SAMPLE_FORM, rc="10k")).get_data(as_text=True)
        self.assertIn("warning-bar", html)
        self.assertNotIn("region-active", html)

    def test_cutoff_shows_warning_bar(self):
        html = self.client.post("/", data=dict(SAMPLE_FORM, r2="1k")).get_data(as_text=True)
        self.assertIn("warning-bar", html)

    def test_calculation_steps_are_shown(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        self.assertIn("ขั้นตอนคำนวณ", html)
        self.assertIn("VTH", html)
        self.assertIn("RTH", html)

    def test_results_table_has_units(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        for unit in ("V", "mA", "µA"):
            self.assertIn(unit, html)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: FAIL on `test_stylesheet_is_linked` (no `/static/style.css` link yet).

- [ ] **Step 3: Write `static/style.css`**

Use the palette from Global Constraints. Layout: `.card` wrapper with a navy header band, `.layout` grid `1fr 1fr` at `min-width: 860px` and single column below; `.results-table` with `td` aligned left / `td.num` right-aligned and `font-variant-numeric: tabular-nums`; `.warning-bar` amber background `#fff4e9` with a `4px` left border `#b85c2c`; `.region-active` green pill `#e9f6f2` / `#178875`; `.error-panel` light red; `.steps` monospace block on `#f0f5f9`. System font stack: `Tahoma, "Noto Sans Thai", "Leelawadee UI", Arial, sans-serif`. No `@import`, no external URLs.

- [ ] **Step 4: Rewrite `templates/index.html` as the full page**

Requirements:
- `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">`
- Navy header: `BJT DC Bias Calculator` + `Voltage-Divider Bias · NPN Common Emitter`.
- Inline SVG schematic of the voltage-divider circuit inside `<figure aria-hidden="true">`; keep every coordinate inside the `viewBox`.
- Form: one labelled input per field, `inputmode="decimal"`, hint text `ใส่ k ได้ เช่น 100k · ไม่ใส่หน่วย = Ω`, submit button `Calculate DC Bias`, and a link to `{{ url_for('index') }}` labelled `ใช้ค่าตัวอย่าง`.
- Raw submitted values are echoed back with `value="{{ values.r1 }}"` so a recalculation only needs one field changed.
- Results column renders `.results-table` with rows `VB, VE, VC, VCE, IC, IB, IE` (unit per row), then either `<div class="region-active">✅ Forward-Active</div>` or `<div class="warning-bar">` looping over `result.warnings`, plus a `.steps` block listing `VTH, RTH, IB, IE` with their formulas and formatted values, plus `result.notes` as a muted advisory list.
- Errors: `<div class="error-panel">` listing every message from `errors`.
- Assume-model line: `แบบจำลอง: β คงที่ · VBE คงที่ · Forward-Active`.

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web.py" -v`
Expected: PASS, 14 tests.

- [ ] **Step 6: Run the whole suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS, 36 tests.

- [ ] **Step 7: Look at the page in a browser**

Run: `.venv\Scripts\python.exe -m flask --app app run --debug` then open `http://127.0.0.1:5000/`
Expected: sample values prefilled; one click shows `VB 1.942 V … VCE 8.052 V` with a green pill; changing `RC` to `10k` swaps in the amber warning bar. Stop the server with `Ctrl+C`.

- [ ] **Step 8: *STUDENT* — commit in GitHub Desktop**

Message: `feat: styled two-column layout with calculation steps and region warnings`

---

## Task 6: Documentation, validation record, and GitHub handoff

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/design-note.md`
- Create: `docs/validation.md`
- Create: `docs/reflection.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the submission artefacts named in the lab handout.

- [ ] **Step 1: Write `README.md`** (Thai) with sections: what it is, requirements, install (`python -m venv .venv`, `.venv\Scripts\python.exe -m pip install -r requirements.txt`), run (`.venv\Scripts\python.exe -m flask --app app run --debug`, open `http://127.0.0.1:5000/`), test (`.venv\Scripts\python.exe -m unittest discover -s tests -v`), how units are typed, the model assumptions and its limits, and a short "why this is a web app, not an HTML file" paragraph that answers the four individual questions from the handout.

- [ ] **Step 2: Write `AGENTS.md`** with the conventions an AI assistant must follow: mathematics only in `dc_bias.py`; never hardcode results in the template; every displayed number carries a unit; new numeric inputs need a validation rule and a test; tests are `unittest`; never commit `.venv/`, `.env`, or credentials; agent does not run `git commit`/`git push`.

- [ ] **Step 3: Write `docs/design-note.md`** — a half-page summary of the approved design: scope, the one-route architecture, the module boundary, and the region thresholds.

- [ ] **Step 4: Write `docs/validation.md`** — the hand calculation from the spec §7.10 (VTH 2.1639 V, RTH 18.0328 kΩ, IB 12.2986 µA, IC 1.22986 mA, IE 1.24216 mA, VE 1.24216 V, VB 1.94216 V, VC 9.29431 V, VCE 8.05216 V), a table comparing it with the app output, an A1–A7 checklist with the evidence for each, and the captured test log.

- [ ] **Step 5: Write `docs/reflection.md`** — a Thai template with empty headings for the student to fill: what was built, what the student verified personally, one thing that surprised them, one thing they would do differently, and their answer to "ทำไมเปิด index.html ตรง ๆ จึงไม่เท่ากับการรัน Flask".

- [ ] **Step 6: Run the full suite one final time and capture the log**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS, 36 tests — copy the output into `docs/validation.md`.

- [ ] **Step 7: Verify no secrets or virtualenv are staged**

Run: `git status --short`
Expected: only source, templates, static, tests, docs and the three root files; no `.venv/`, no `__pycache__/`.

- [ ] **Step 8: *STUDENT* — publish and record the submission**

In GitHub Desktop: commit everything with `docs: README, AGENTS and validation records`, then **Publish repository** (public, name `transistor-simulator`). Copy the repository URL and the latest commit SHA into Moodle, attach a screenshot of the results page and the test log.

---

## Plan self-review

- **Spec coverage:** §7.1 files (Tasks 1–6), §7.2–7.4 API/parsing/validation (Task 2), §7.5–7.6 computation and regions (Task 3), §7.7 web layer (Task 4), §7.8 UI (Task 5), §7.9 tests (Tasks 2–5, 36 total), §7.10 reference values (Tasks 3 and 6), §10 git handoff (Tasks 1, 6). No gaps.
- **Review Focus:** the five risky inputs are pinned by `test_post_missing_field_shows_error`, `test_post_thai_text_shows_error`, `test_post_thousands_separator_shows_error`, `test_post_very_long_input_does_not_crash`, and `test_cutoff_at_exact_boundary`.
- **Type consistency:** `BiasResult` is defined once in Task 3 and referenced by name in Tasks 4–5; form field names are the same seven strings in every task; CSS class names used by Task 5's tests are the ones Step 3 creates.
- **Proportion:** the plan is roughly the length of the spec; code appears only where the signature and tests do not already determine it.

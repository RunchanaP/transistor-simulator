# Design — BJT Common-Emitter DC Bias Web App (ENG29 2121 · Lab 02)

- **Date:** 2026-11-10
- **Status:** Draft — awaiting approval
- **Owner:** RunchanaP (student)
- **Deliverable:** working Flask web app on `http://127.0.0.1:5000/` + tests + GitHub commit

---

## 1. Intent and why

Lab 02 requires a **real multi-file web application** (not a single HTML file) that
computes the DC operating point of an NPN BJT common-emitter amplifier with
voltage-divider bias. The point of the exercise is to see the separation between
frontend (form), backend (Flask routing), engineering logic (pure Python), and
automated tests — and to prove the numbers come from Python, not from hardcoded HTML.

Success for the student = pass every acceptance item A1–A7 in the lab handout and be
able to explain why opening `templates/index.html` directly is not the same as
running Flask.

### 1.1 Decisions taken in the brainstorm (student's answers)

| Question | Answer | Consequence for the build |
|---|---|---|
| Who opens the app, and when? | The student, alone, doing homework / real circuit calculations | Optimise for repeated personal use, not for a live demo |
| Where do component values come from? | Textbooks and lecture slides, written in **kΩ** | Typed suffixes (`100k`, `2.2k`) are the primary input; no kΩ→Ω conversion by hand |
| What happens to the results? | Copied into a notebook / lab report | Results must be easy to copy: clear labels, units in their own column, stable layout |
| How much detail is needed? | The **calculation steps** (intermediate values + formulas) | A "ขั้นตอนคำนวณ" block showing VTH, RTH, IB, IE with their formulas |
| What when outside forward-active? | **Show the numbers plus an orange warning bar** | Numbers stay visible; warning explains the model does not apply (A5) |
| Visual character | **Card style, two columns, lab handout palette** | Navy header `#103658`, blue/teal accents, green/orange status colours |
| Anything to avoid? | Nothing specified | No charts, no animation, no extra fields |

## 2. Goals

- G1 — `GET /` returns HTTP 200 with an input form prefilled with the lab sample values.
- G2 — `POST /` takes `VCC, R1, R2, RC, RE, β, VBE` and returns the computed
  `VTH, RTH, IB, IC, IE, VB, VE, VC, VCE` rendered in HTML, all values produced by Python.
- G3 — Every displayed quantity carries a unit (V, mA, µA).
- G4 — Invalid input produces a readable, field-specific error without crashing the page.
- G5 — Operating region is classified and warnings are shown when the forward-active
  assumption does not hold.
- G6 — At least 3 engineering unit tests and at least 1 Flask test-client test, all passing
  via `python -m unittest discover -s tests -v`.
- G7 — README lets a fresh clone install, run, and test the app.

## 3. Non-goals

- No AC small-signal analysis, gain, Bode plot, transient, or signal generator.
- No other bias topologies (fixed bias, emitter bias) — W3 material.
- No SPICE/ngspice, no DC load-line plot.
- No database, login, user accounts, or persistence.
- No JavaScript framework, no build step, no CDN dependencies.
- No circuit-diagram drawing library; schematic is a static inline SVG (decorative).

## 4. Anti-goals

- Computing values in JavaScript or hardcoding results in the template — would fail A2.
- Opening `index.html` via `file://` being presented as "the app running".
- Reporting cutoff/saturation numbers as trustworthy without a warning — fails A5.
- Adding scope that cannot be finished inside the 75-minute build window.

## 5. Constraints

| Constraint | Value |
|---|---|
| Runtime | Python 3.13.17, Flask in local `.venv` (never system site-packages) |
| Host | `127.0.0.1:5000`, Flask dev server, localhost only |
| Model | Forward-active approximation: β constant, VBE constant |
| Tests | `unittest` standard library only (`python -m unittest discover -s tests -v`) |
| Version control | Local git repo; **commits/push done by the student in GitHub Desktop**, not by the agent |
| Repository | `transistor-simulator\` inside `C:\Users\B6829780\Documents\Default Project\`, published **public** so the instructor can clone it (A7) |
| Device sample | VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V |
| Offline | UI must render fully without internet (no CDN fonts/CSS/JS) |

## 6. Approaches considered

**A. Server-side form POST + Jinja re-render — CHOSEN by the student.**
Plain `<form method="post">`, Flask computes, `render_template` returns a full page.
Cheapest path to A1–A6, degrades gracefully with JS disabled, trivially testable with
`app.test_client()`. Cost: full page refresh per calculation — acceptable for a
calculator.

**B. AJAX + JSON API.**
`fetch('/api/calculate')` returns JSON, JS patches the DOM. Smoother and a better base
for the W5–W7 AC/overlay work, but needs extra JS, a second test surface, and roughly
20–30 extra minutes we do not have inside the 75-minute build window.

**C. Client-side JavaScript only — REJECTED.**
Computing in the browser directly violates A2 ("Python backend must compute") and the
whole point of the lab.

## 7. Design

### 7.1 File layout

```
transistor-simulator/
├─ app.py                      # Flask app, route "/" (GET + POST), no math
├─ dc_bias.py                  # pure engineering logic + input parsing (no Flask, no HTML)
├─ templates/index.html        # Jinja: form, results, warnings, errors
├─ static/style.css            # layout/typography, no external assets
├─ tests/
│  ├─ test_dc_bias.py          # engineering + parsing tests
│  └─ test_web.py              # Flask test-client tests
├─ requirements.txt            # Flask
├─ README.md                   # install / run / test
├─ AGENTS.md                   # conventions for AI assistance
├─ .gitignore                  # .venv/, __pycache__/, .env
└─ docs/
   ├─ design-note.md           # short summary of this design
   ├─ validation.md            # independent calculation + acceptance evidence
   └─ reflection.md            # student's own reflection (template, filled by student)
```

Dependency direction: `app.py → dc_bias.py`. `dc_bias.py` imports nothing from Flask or
the template. Template contains no physics equations.

### 7.2 `dc_bias.py` public API

```python
class ValidationError(Exception):
    errors: dict[str, str]      # field name -> human-readable Thai message

@dataclass(frozen=True)
class BiasInput:
    vcc: float; r1: float; r2: float; rc: float; re: float
    beta: float; vbe: float      # all resistances already normalised to ohms

@dataclass(frozen=True)
class BiasResult:
    vth: float; rth: float
    ib: float                    # A
    ic: float                    # A
    ie: float                    # A
    vb: float; ve: float; vc: float; vce: float
    region: str                  # "active" | "cutoff" | "saturation"
    warnings: list[str]          # region/model warnings; empty when region == "active"
    notes: list[str]             # soft advisories, may be non-empty even when active

def parse_inputs(raw: Mapping[str, str]) -> BiasInput   # raises ValidationError
def solve_dc_bias(inp: BiasInput) -> BiasResult
```

`solve_dc_bias` is a pure function: same input → same output, no I/O, no globals.
Formatting for display happens in `app.py` (or Jinja filters), not in the math module.

### 7.3 Input parsing (kΩ → Ω)

Resistance fields accept an optional SI suffix, case-insensitive:

- `100k`, `100K`, `100kΩ` → 100 000 Ω
- `2.2k` → 2 200 Ω
- `1M`, `1meg` → 1 000 000 Ω
- `2200`, `2200Ω` → 2 200 Ω (bare number = ohms)

Lowercase `m` is **rejected** with an explicit message (cannot tell milli from mega).
Parsing lives in `dc_bias.py` so it is unit-testable without HTTP.

### 7.4 Validation rules

| Field | Rule | Message (Thai) |
|---|---|---|
| ทุกช่อง | ว่าง / แปลงเป็นตัวเลขไม่ได้ | `กรุณากรอกตัวเลข` |
| VCC | > 0 | `VCC ต้องมากกว่า 0` |
| R1, R2, RC, RE | > 0 | `ค่าความต้านทานต้องมากกว่า 0` |
| β | > 0 | `β ต้องมากกว่า 0` |
| VBE | 0 < VBE < 2 | `VBE ต้องอยู่ระหว่าง 0 ถึง 2 V` |

All failures are collected (not just the first) and rendered together. Invalid input
returns **HTTP 200** with the form repopulated and an error block, so the page never
breaks (A4). A soft advisory (goes to `BiasResult.notes`, **not** `warnings`) is added
when VBE is outside 0.5–0.9 V, because that is unusual for a silicon BJT even though the
operating point may still be valid. This keeps the invariant
"`warnings` is empty ⇔ region is active" true and independently testable.

**Non-finite guard (builder call).** Every numeric field must pass `math.isfinite()` and
stay inside a sanity band — VCC ≤ 1e4 V, each resistance ≤ 1e12 Ω, β ≤ 1e5 — otherwise
`ValidationError` reports `ค่าตัวเลขไม่สมเหตุสมผล`. After solving, any non-finite output
also raises `ValidationError`. Without this, `R1=inf` or `1e308` would pass validation and
produce `NaN`, which matches no region branch and would contradict A4.

**Source of requirements.** The authoritative list of graded items is the Lab 02
handout (`Lab02_BJT_Simulator_Brainstorm_2-2569 (2).html`, section 09, items A1–A7).
§9 of this document restates all seven; nothing is added or omitted.

### 7.5 Computation

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β+1)·RE)
IC  = β · IB
IE  = (β+1) · IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

### 7.6 Region classification and warnings

| Condition | Region | Behaviour |
|---|---|---|
| `VTH − VBE ≤ 0` | `cutoff` | Force `IB = IC = IE = 0`, `VE = 0`, `VB = VTH` (no current), `VC = VCC`, `VCE = VCC`. Warning: transistor อยู่ในช่วง Cutoff — แบบจำลอง Forward-Active ใช้ไม่ได้ |
| `VTH > VBE` and `VCE > 0.3 V` | `active` | Show results, no warning |
| `VTH > VBE` and `0 < VCE ≤ 0.3 V` | `saturation` | Show numbers but warn: VCE ใกล้/ต่ำกว่า VCE(sat) — ค่าที่ได้มาจากสมการ Forward-Active จึงไม่น่าเชื่อถือ |
| `VTH > VBE` and `VCE ≤ 0` | `saturation` | Same warning, stronger wording |

Threshold `VCE_SAT = 0.3 V` is a named constant with a comment explaining it is a
typical silicon value, not a device-specific number.

The result page always states the model assumptions:
"β คงที่, VBE คงที่, ทำงานใน Forward-Active" so the reader knows what was assumed.

### 7.7 Web layer (`app.py`)

- One route: `@app.route("/", methods=["GET", "POST"])` — satisfies both A1 and A2
  (`POST /`).
- `GET` → render form with the lab sample values as defaults, no results.
- `POST` → `parse_inputs(request.form)` → `solve_dc_bias()` → render the same template
  with `result` set. On `ValidationError` → render with `errors` and the raw input
  preserved.
- After a successful calculation the submitted values stay in the form (so the student
  can change one value and recalculate), and a **"ใช้ค่าตัวอย่าง"** link resets the form
  to `12 / 100k / 22k / 2.2k / 1k / 100 / 0.7` via `GET /`.
- `app.config["SECRET_KEY"]` is not needed (no sessions/flash). No CSRF token: local,
  single-user lab app, no state change — documented as a deliberate builder call.
- No calculations in `app.py` beyond formatting (V → 3 dp, mA → 3 dp, µA → 2 dp).

### 7.8 UI (Thai, single page, card style)

The student chose the card layout that matches the lab handout palette: navy header
`#103658`, light paper background, two columns on wide screens, status colours
(green active / orange warning / red error).

```
╔══════════════════════════════════════════════════════════════════╗
║  BJT DC Bias Calculator                                          ║  navy bar
║  Voltage-Divider Bias · NPN Common Emitter                       ║
╠═══════════════════════════╤══════════════════════════════════════╣
║ พารามิเตอร์วงจร            │ ผลการคำนวณ DC Bias                   ║
║  VCC  [ 12   ] V          │  VB    1.942 V                       ║
║  R1   [ 100k ] Ω          │  VE    1.242 V                       ║
║  R2   [ 22k  ] Ω          │  VC    9.294 V                       ║
║  RC   [ 2.2k ] Ω          │  VCE   8.052 V                       ║
║  RE   [ 1k   ] Ω          │  IC    1.230 mA                      ║
║  β    [ 100  ]            │  IB   12.30 µA                       ║
║  VBE  [ 0.70 ] V          │  IE    1.242 mA                      ║
║                           │  ┌────────────────────────────────┐  ║
║  [ Calculate DC Bias ]    │  │ ✅ Forward-Active              │  ║  green
║  ใช้ค่าตัวอย่าง            │  └────────────────────────────────┘  ║
║                           │                                      ║
║  ⓘ ใส่ k ได้ เช่น 100k     │  ขั้นตอนคำนวณ                        ║
║     ไม่ใส่ = Ω            │   VTH = VCC·R2/(R1+R2) = 2.164 V     ║
║                           │   RTH = R1∥R2        = 18.03 kΩ      ║
║                           │   IB  = (VTH−VBE)/…  = 12.30 µA      ║
║                           │   IE  = (β+1)·IB     = 1.242 mA      ║
╚═══════════════════════════╧══════════════════════════════════════╝
```

Warning state (saturation) replaces the green pill with an orange bar spanning the
results column:

```
┌──────────────────────────────────────────────────────────────┐
│ ⚠ VCE = 0.12 V ต่ำกว่า VCE(sat) ≈ 0.2–0.3 V                   │
│   ค่าที่แสดงมาจากสมการ Forward-Active จึงใช้ไม่ได้ในวงจรจริง    │
└──────────────────────────────────────────────────────────────┘
```

- Responsive: two columns ≥ 860 px, stacked below; the results column stays first on
  narrow screens after a POST so the answer is visible without scrolling.
- Inline SVG schematic of the voltage-divider circuit above the form (static, decorative,
  `aria-hidden="true"`).
- Warnings in an amber panel, errors in a red panel, active region in a green pill.
- Every result row is `label | value | unit` in a table so columns line up when copying.
- Semantic labels + `aria-describedby` for hint text; numeric inputs use `inputmode="decimal"`.
- No external fonts, CSS, JS, or images — must render fully offline.

### 7.9 Tests

`tests/test_dc_bias.py` (unittest):
1. `test_reference_operating_point` — sample values → VB, VE, VC, VCE, IC within 0.1 %
   of the independent hand calculation (see `docs/validation.md`).
2. `test_all_kirchhoff_relations` — VB = VE+VBE, VCE = VC−VE, IC = β·IB within tolerance.
3. `test_resistance_suffix_parsing` — `100k`, `2.2k`, `1M`, `2200` all normalise correctly.
4. `test_invalid_input_raises_collected_errors` — `R≤0`, `β≤0`, non-numeric → multiple
   field errors collected.
5. `test_cutoff_region_warning` — `VTH ≤ VBE` → region `cutoff`, zero currents, warning.
6. `test_saturation_region_warning` — `RC` large enough to drive `VCE ≤ 0.3 V` → warning.
7. `test_vbe_outside_typical_range_adds_note_not_warning` — VBE = 1.0 V with an otherwise
   active bias → `notes` non-empty, `warnings` empty, region still `active`.

`tests/test_web.py` (unittest, `app.test_client()`):
7. `test_get_index_returns_form` — status 200, contains `name="vcc"` and the submit label.
8. `test_post_valid_shows_computed_values` — POST sample → 200, body contains `1.942`,
   `9.294`, `8.052`, `1.230`, and **not** the raw template placeholder.
9. `test_post_invalid_shows_error_not_500` — POST `R1=0` → 200 + Thai error text.
10. `test_post_non_finite_input_is_rejected` — POST `R1=inf` → 200 + Thai error text.

Total: 10 tests (7 engineering, 3 HTTP client).

### 7.10 Reference values (independent hand calculation)

For the sample device values:

```
VTH = 2.1639 V      RTH = 18.0328 kΩ
IB  = 12.2986 µA    IC  = 1.22986 mA    IE = 1.24216 mA
VE  = 1.24216 V     VB  = 1.94216 V     VC = 9.29431 V    VCE = 8.05216 V
Region: Active
```

These are computed by hand from the equations in §7.5 and recorded in
`docs/validation.md` before the app is written, so the app is checked against an
independent source rather than against itself.

## 8. What is left to the builder

- Exact CSS values, spacing, and font stack (system fonts only, palette fixed as §7.8).
- Exact wording of Thai hints and warning sentences beyond the required meaning.
- Number of decimal places for `VTH/RTH` display (3 dp / engineering notation).
- Whether the schematic SVG shows the resistor labels or is purely decorative.
- Commit message wording (the student writes it in GitHub Desktop).

## 9. Verification plan (maps to acceptance items)

| Item | How it is demonstrated |
|---|---|
| A1 | `GET /` in browser → form, HTTP 200 (`test_get_index_returns_form`) |
| A2 | `POST /` with samples → numbers appear; code path goes through `dc_bias.solve_dc_bias` |
| A3 | Values match §7.10 hand calculation (`test_reference_operating_point`) |
| A4 | `R1=0`, `β=-5`, `R1=abc` → Thai error panel, page still 200 |
| A5 | `VTH ≤ VBE` → cutoff warning; large `RC` → saturation warning |
| A6 | 10 tests, `python -m unittest discover -s tests -v`, all pass; 7 engineering, 3 Flask client |
| A7 | Fresh clone → `python -m venv .venv` → pip install → run → tests, per README |

## 10. Git handoff (how the student commits)

The agent **never commits and never pushes**. The split is:

| Step | Who |
|---|---|
| `git init` in `transistor-simulator\`, `.gitignore` written | agent |
| Files created, tests run, browser demo shown | agent |
| Open GitHub Desktop → **File → Add Local Repository** → select `transistor-simulator` | student |
| Review the diff, write the commit message, click **Commit to main** | student |
| **Publish repository** (or push to an existing remote) → copy URL + commit SHA for Moodle | student |

Rationale: the lab grades git literacy (rubric item 5) and the student must be able to
explain what was committed. `git init` is done by the agent only so GitHub Desktop's
"Add Local Repository" accepts the folder immediately.

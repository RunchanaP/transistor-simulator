# AGENTS.md — conventions for AI assistants

## Architecture

- `dc_bias.py` owns every equation, every unit conversion, and every validation rule.
  It must not import Flask, Jinja, or anything HTTP.
- `app.py` owns routing and display formatting only. No physics arithmetic here.
- `spice_engine.py` owns SPICE configuration, input parsing, netlist construction,
  ngspice execution, output parsing, and server-side SVG chart rendering.
  It must not import Flask, Jinja, or anything HTTP.
- `templates/` owns presentation. It must never contain a physics equation or a
  fabricated SPICE number/trace.
- `static/style.css` owns appearance. No external fonts, CDNs, or JS.
- `dc_bias.py` solves three Lab 03 circuits with shared region logic:
  `solve_dc_bias()` (Thevenin, `IB = (VTH − VBE) / (RTH + (β+1)·RE)`),
  `solve_fixed()` (`IB = (VCC − VBE) / RB`), and
  `solve_emitter()` (`IB = (VCC − VBE) / (RB + (β+1)·RE)`).
  All return the same `BiasResult`. There are no approximate or
  base-current-neglected variants; the only mode switch is the circuit dropdown.

## Rules

1. Never hardcode a computed result in the template. Every number on screen must come
   from the selected solver (`solve_fixed()`, `solve_emitter()`, or `solve_dc_bias()`).
2. Every displayed quantity carries a unit (`V`, `mA`, `µA`, `Ω`, `kΩ`).
3. A new numeric input needs three things in the same change: a parsing rule,
   a validation rule with a Thai message, and a test.
4. Tests use the standard library `unittest` only. Run
   `python -m unittest discover -s tests -v`; it must be fully green before any claim
   of completion.
5. Invalid input returns HTTP 200 with a readable error panel — never a 500 and never a
   traceback shown to the user.
6. Anything outside the forward-active region must carry a warning. Do not present
   cutoff/saturation numbers as trustworthy.
7. Never commit `.venv/`, `.env`, API keys, or credentials. `.gitignore` already covers
   these.
8. **The agent does not run `git commit` or `git push`.** The student commits in GitHub
   Desktop so they can explain the history.
9. Region classification lives in the solver, not in the template, and applies to all
   three modes: `IB ≤ 0` → cutoff, otherwise `VCE ≤ 0.2 V` → saturation.
10. The steps block must show the formula that produced the number next to it, and
    every quantity in the results table must appear in the steps block.
11. An unknown or missing `mode` must raise a validation error — never silently default
    to Divider.
12. Reference/expected values come from the student's independent hand calculation,
    never from the program's output. This applies to Lab 04 acceptance B1–B8 as well:
    the agent records observations only and must not assign PASS/FAIL before the
    student supplies the expected values.
13. SPICE is limited to the Lab 04 voltage-divider CE amplifier reference circuit
    with real `.op`, `.ac`, and `.tran` runs. The three Lab 03 analytical modes stay
    unchanged and remain the default when `analysis` is absent; an explicit unknown
    `analysis` must raise a validation error.
14. Never fabricate a SPICE number, trace, plot, or model. Every displayed SPICE
    value and chart array must be parsed from actual ngspice output by `spice_engine.py`.
    B2–B6 stay `NOT RUN · รอโมเดลจากอาจารย์` while `NGSPICE_MODEL` is unset.
15. The BJT model must come from the Instructor Starter Kit via `NGSPICE_MODEL`.
    There is no default, guessed, or bundled model file; missing model is a readable
    Thai error, not a silent substitution.

## Scope

This app covers the three Lab 03 DC bias topologies (Fixed Bias, single-supply
Emitter Bias, and Voltage-Divider Bias) plus the explicit Lab 04 extension: ngspice
DC operating point, AC Bode, and transient simulation of the voltage-divider CE
amplifier with server-side SVG charts and provenance. Do not add AC analysis, Bode
plots, transient simulation, other bias topologies, or a SPICE solver beyond that
Lab 04 specification without a new explicit specification.

# AGENTS.md — conventions for AI assistants

## Architecture

- `dc_bias.py` owns every equation, every unit conversion, and every validation rule.
  It must not import Flask, Jinja, or anything HTTP.
- `app.py` owns routing and display formatting only. No physics arithmetic here.
- `templates/` owns presentation. It must never contain a physics equation.
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
    never from the program's output.

## Scope

This app covers the three Lab 03 DC bias topologies only: Fixed Bias, single-supply
Emitter Bias, and Voltage-Divider Bias. Do not add AC analysis, Bode plots,
transient simulation, other bias topologies, or a SPICE solver without an explicit
new specification.

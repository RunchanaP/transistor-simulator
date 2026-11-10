# AGENTS.md — conventions for AI assistants

## Architecture

- `dc_bias.py` owns every equation, every unit conversion, and every validation rule.
  It must not import Flask, Jinja, or anything HTTP.
- `app.py` owns routing and display formatting only. No physics arithmetic here.
- `templates/` owns presentation. It must never contain a physics equation.
- `static/style.css` owns appearance. No external fonts, CDNs, or JS.
- `dc_bias.py` solves one model only: the Thevenin equivalent with base current
  included (`IB = (VTH − VBE) / (RTH + (β+1)·RE)`). There is no approximate or
  base-current-neglected variant, and no method switch in the UI.

## Rules

1. Never hardcode a computed result in the template. Every number on screen must come
   from `solve_dc_bias()`.
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
9. Region classification lives in `solve_dc_bias()`, not in the template:
   `VTH ≤ VBE` → cutoff, otherwise `VCE ≤ 0.3` → saturation.
10. The steps block must show the formula that produced the number next to it, and
    every quantity in the results table must appear in the steps block.

## Scope

This app is DC bias only. Do not add AC analysis, Bode plots, transient simulation,
other bias topologies, or a SPICE solver without an explicit new specification.

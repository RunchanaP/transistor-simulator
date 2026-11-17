"""Flask entry point for the BJT DC bias calculator.

All electrical logic lives in dc_bias.py; this module only routes HTTP,
formats numbers for display, and picks the template.
"""

from flask import Flask, render_template, request

from dc_bias import (MODE_DIVIDER, MODE_EMITTER, MODE_FIXED, MODE_SAMPLES,
                     NUMERIC_FIELDS, ValidationError, normalize_mode,
                     parse_divider, parse_emitter, parse_fixed, solve_dc_bias,
                     solve_emitter, solve_fixed)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    mode = MODE_DIVIDER
    values = MODE_SAMPLES[mode]
    result = None
    errors: dict[str, str] = {}

    if request.method == "POST":
        values = {field: request.form.get(field, "")
                  for field in (*NUMERIC_FIELDS, "rb")}
        try:
            mode = normalize_mode(request.form.get("mode"))
            if mode == MODE_FIXED:
                result = solve_fixed(parse_fixed(request.form))
            elif mode == MODE_EMITTER:
                result = solve_emitter(parse_emitter(request.form))
            else:
                result = solve_dc_bias(parse_divider(request.form))
        except ValidationError as exc:
            result = None
            errors = exc.errors

    return render_template(
        "index.html",
        values=values,
        mode=mode,
        result=result,
        errors=errors,
        sample=MODE_SAMPLES.get(mode, MODE_SAMPLES[MODE_DIVIDER]),
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

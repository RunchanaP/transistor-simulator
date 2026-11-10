"""Flask entry point for the BJT DC bias calculator.

All electrical logic lives in dc_bias.py; this module only routes HTTP,
formats numbers for display, and picks the template.
"""

from flask import Flask, render_template, request

from dc_bias import (NUMERIC_FIELDS, SAMPLE_VALUES, ValidationError,
                     parse_inputs, solve_dc_bias)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        values = {field: request.form.get(field, "") for field in NUMERIC_FIELDS}
        try:
            result = solve_dc_bias(parse_inputs(request.form))
            errors: dict[str, str] = {}
        except ValidationError as exc:
            result = None
            errors = exc.errors
        return render_template("index.html", values=values, result=result,
                               errors=errors, sample=SAMPLE_VALUES)

    return render_template("index.html", values=SAMPLE_VALUES, result=None,
                           errors={}, sample=SAMPLE_VALUES)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

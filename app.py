"""Flask entry point for the BJT bias and CE amplifier web app.

All electrical logic lives in dc_bias.py (Lab 03) and spice_engine.py (Lab 04);
this module only routes HTTP, formats numbers for display, and picks templates.
"""

from flask import Flask, render_template, request

from dc_bias import (MODE_DIVIDER, MODE_EMITTER, MODE_FIXED, MODE_SAMPLES,
                     NUMERIC_FIELDS, ValidationError, normalize_mode,
                     parse_divider, parse_emitter, parse_fixed, solve_dc_bias,
                     solve_emitter, solve_fixed)
from spice_engine import (ANALYSIS_ANALYTICAL, SpiceError, normalize_analysis,
                          parse_spice_inputs, render_bode_svg, render_wave_svg,
                          resolve_config, run_analysis)

app = Flask(__name__)

SPICE_FIELDS = ("vcc", "r1", "r2", "rc", "re", "rl", "cin", "cout",
                "amplitude", "frequency")
SPICE_SAMPLE_VALUES = {
    "vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k", "re": "1k",
    "rl": "10k", "cin": "10", "cout": "10", "amplitude": "10",
    "frequency": "1",
}


@app.route("/", methods=["GET", "POST"])
def index():
    analysis = ANALYSIS_ANALYTICAL
    mode = MODE_DIVIDER
    values = MODE_SAMPLES[mode]
    spice_values = SPICE_SAMPLE_VALUES
    result = None
    spice_result = None
    bode_svg = ""
    wave_svg = ""
    errors: dict[str, str] = {}
    status = "idle"
    engine = {"version": "not run", "model": "not run", "analysis": analysis}

    if request.method == "POST":
        values = {field: request.form.get(field, "")
                  for field in (*NUMERIC_FIELDS, "rb")}
        spice_values = {field: request.form.get(field, SPICE_SAMPLE_VALUES[field])
                        for field in SPICE_FIELDS}
        try:
            analysis = normalize_analysis(request.form.get("analysis"))
            if analysis == ANALYSIS_ANALYTICAL:
                mode = normalize_mode(request.form.get("mode"))
                if mode == MODE_FIXED:
                    result = solve_fixed(parse_fixed(request.form))
                elif mode == MODE_EMITTER:
                    result = solve_emitter(parse_emitter(request.form))
                else:
                    result = solve_dc_bias(parse_divider(request.form))
                status = "success" if result else "error"
            else:
                mode = MODE_DIVIDER
                spice_form = {
                    field: request.form[field] if field in request.form
                    else SPICE_SAMPLE_VALUES[field]
                    for field in SPICE_FIELDS
                }
                inp = parse_spice_inputs(spice_form)
                cfg = resolve_config()
                spice_result = run_analysis(analysis, inp, cfg)
                engine = {
                    "version": spice_result.engine_version,
                    "model": spice_result.model_name,
                    "analysis": analysis,
                }
                bode_svg = (render_bode_svg(spice_result.ac, inp.frequency)
                            if spice_result.ac else "")
                wave_svg = (render_wave_svg(spice_result.tran)
                            if spice_result.tran else "")
                status = spice_result.status
        except (ValidationError, SpiceError) as exc:
            result = None
            spice_result = None
            bode_svg = ""
            wave_svg = ""
            status = "error"
            errors = (exc.errors if isinstance(exc, ValidationError)
                      else {"spice": str(exc)})

    return render_template(
        "index.html",
        analysis=analysis,
        mode=mode,
        values=values,
        spice_values=spice_values,
        sample=MODE_SAMPLES.get(mode, MODE_SAMPLES[MODE_DIVIDER]),
        result=result,
        spice_result=spice_result,
        bode_svg=bode_svg,
        wave_svg=wave_svg,
        errors=errors,
        status=status,
        engine=engine,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

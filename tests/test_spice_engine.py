"""Tests for the ngspice adapter (netlist, runner, parsers, charts)."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dc_bias import ValidationError
from spice_engine import (ANALYSIS_AC, ANALYSIS_ANALYTICAL, ANALYSIS_DC,
                          ANALYSIS_TRAN, AcSeries, SpiceConfig, SpiceError,
                          TranSeries, build_netlist, normalize_analysis, parse_ac,
                          parse_op, parse_spice_inputs, parse_tran,
                          render_bode_svg, render_wave_svg, resolve_config,
                          run_analysis)

# Adapter fixtures only. They are NOT instructor-model evidence.
OP_RAW = """Title: test
Plotname: Operating Point
Flags: real
No. Variables: 5
No. Points: 1
Variables:
\t0\tv(base)\tvoltage
\t1\tv(emitter)\tvoltage
\t2\tv(collector)\tvoltage
\t3\ti(vrc)\tcurrent
\t4\ti(vcc)\tcurrent
Values:
0\t\t1.942000000000000e+00
\t1.242000000000000e+00
\t9.294000000000000e+00
\t1.230000000000000e-03
\t-1.330600000000000e-03
"""

AC_RAW = """Title: test
Plotname: AC Analysis
Flags: complex
No. Variables: 3
No. Points: 3
Variables:
\t0\tfrequency\tfrequency\tgrid=3
\t1\tv(base)\tvoltage
\t2\tv(out)\tvoltage
Values:
0\t\t1.000000000000000e+00,0.000000000000000e+00
\t1.000000000000000e+00,0.000000000000000e+00
\t-1.000000000000000e+01,0.000000000000000e+00
1\t\t1.000000000000000e+03,0.000000000000000e+00
\t1.000000000000000e+00,0.000000000000000e+00
\t-1.000000000000000e+02,0.000000000000000e+00
2\t\t1.000000000000000e+06,0.000000000000000e+00
\t1.000000000000000e+00,0.000000000000000e+00
\t1.000000000000000e+00,0.000000000000000e+00
"""

TRAN_RAW = """Title: test
Plotname: Transient Analysis
Flags: real
No. Variables: 3
No. Points: 3
Variables:
\t0\ttime\ttime
\t1\tv(base)\tvoltage
\t2\tv(out)\tvoltage
Values:
0\t\t0.000000000000000e+00
\t1.000000000000000e-02
\t-1.000000000000000e-01
1\t\t1.000000000000000e-04
\t-1.000000000000000e-02
\t1.000000000000000e-01
2\t\t2.000000000000000e-04
\t1.000000000000000e-02
\t-1.000000000000000e-01
"""


class AnalysisAndInputTests(unittest.TestCase):
    def test_normalize_analysis_accepts_four_modes(self):
        self.assertEqual(normalize_analysis("dc"), ANALYSIS_DC)
        self.assertEqual(normalize_analysis("ac"), ANALYSIS_AC)
        self.assertEqual(normalize_analysis("tran"), ANALYSIS_TRAN)
        self.assertEqual(normalize_analysis(None), ANALYSIS_ANALYTICAL)

    def test_normalize_analysis_rejects_unknown(self):
        with self.assertRaises(ValidationError):
            normalize_analysis("bode")

    def test_parse_spice_inputs_converts_engineering_units(self):
        inp = parse_spice_inputs({
            "vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
            "re": "1k", "rl": "10k", "cin": "10", "cout": "10",
            "amplitude": "10", "frequency": "1",
        })
        self.assertAlmostEqual(inp.vcc, 12.0)
        self.assertAlmostEqual(inp.r1, 100_000.0)
        self.assertAlmostEqual(inp.rl, 10_000.0)
        self.assertAlmostEqual(inp.cin, 10e-6)
        self.assertAlmostEqual(inp.amplitude, 0.010)
        self.assertAlmostEqual(inp.frequency, 1000.0)

    def test_parse_spice_inputs_rejects_nonpositive_values(self):
        base = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                "re": "0", "rl": "10k", "cin": "10", "cout": "10",
                "amplitude": "10", "frequency": "1"}
        with self.assertRaises(ValidationError) as ctx:
            parse_spice_inputs(base)
        self.assertIn("re", ctx.exception.errors)

    def test_every_numeric_field_has_its_own_bound_error(self):
        invalid = {
            "vcc": "25", "r1": "50", "r2": "20m", "rc": "0", "re": "11M",
            "rl": "1", "cin": "0", "cout": "2000", "amplitude": "101",
            "frequency": "2000",
        }
        base = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                "re": "1k", "rl": "10k", "cin": "10", "cout": "10",
                "amplitude": "10", "frequency": "1"}
        for field, bad_value in invalid.items():
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    parse_spice_inputs({**base, field: bad_value})
                self.assertIn(field, ctx.exception.errors)


class ConfigTests(unittest.TestCase):
    def test_resolve_config_reads_env(self):
        cfg = resolve_config({
            "NGSPICE_EXECUTABLE": r"C:\fake\ngspice.exe",
            "NGSPICE_MODEL": r"C:\fake\q.lib",
            "NGSPICE_MODEL_NAME": "QPROBE",
            "NGSPICE_TIMEOUT": "45",
        })
        self.assertEqual(cfg.executable, r"C:\fake\ngspice.exe")
        self.assertEqual(cfg.model_path, r"C:\fake\q.lib")
        self.assertEqual(cfg.model_name, "QPROBE")
        self.assertEqual(cfg.timeout, 45)

    def test_resolve_config_reads_demo_flag(self):
        cfg = resolve_config({
            "NGSPICE_EXECUTABLE": "ngspice",
            "NGSPICE_MODEL": "q.lib",
            "NGSPICE_MODEL_IS_DEMO": "1",
        })
        self.assertTrue(cfg.demo)

    def test_resolve_config_rejects_unsafe_model_name(self):
        with self.assertRaises(SpiceError):
            resolve_config({"NGSPICE_EXECUTABLE": "ngspice",
                            "NGSPICE_MODEL_NAME": 'Q1\n.END\n"'})

    def test_resolve_config_missing_executable_raises(self):
        with self.assertRaises(SpiceError) as ctx:
            resolve_config({"PATH": ""})
        self.assertIn("ngspice", str(ctx.exception))


class NetlistTests(unittest.TestCase):
    def setUp(self):
        self.inp = parse_spice_inputs({
            "vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
            "re": "1k", "rl": "10k", "cin": "10", "cout": "10",
            "amplitude": "10", "frequency": "1",
        })

    def test_dc_netlist_has_op_and_reference_topology(self):
        net = build_netlist(ANALYSIS_DC, self.inp, r"C:\models\q.lib", "QPROBE")
        self.assertIn(".op", net)
        self.assertIn('.include "C:/models/q.lib"', net)
        self.assertIn("VCC vcc 0 DC 12", net)
        self.assertIn("R1 vcc base 100000", net)
        self.assertIn("R2 base 0 22000", net)
        self.assertIn("VRC vcc rcnode DC 0", net)
        self.assertIn("RC rcnode collector 2200", net)
        self.assertIn("RE emitter 0 1000", net)
        self.assertIn("Q1 collector base emitter QPROBE", net)
        self.assertNotIn("Q1 collector base emitter NPN", net)
        self.assertIn("Cin in base 1e-05", net)
        self.assertIn("Cout collector out 1e-05", net)
        self.assertIn("RL out 0 10000", net)
        self.assertIn("V1 in 0 SIN(0 0.01 1000) AC 0.01", net)

    def test_netlist_requires_an_explicit_model_name(self):
        with self.assertRaises(SpiceError):
            build_netlist(ANALYSIS_DC, self.inp, "q.lib", None)

    def test_ac_and_tran_directives_are_distinct(self):
        ac = build_netlist(ANALYSIS_AC, self.inp, r"C:\models\q.lib", "QPROBE")
        tran = build_netlist(ANALYSIS_TRAN, self.inp, r"C:\models\q.lib", "QPROBE")
        self.assertIn(".ac dec 20 1 1e6", ac)
        self.assertNotIn(".tran", ac)
        self.assertIn(".tran 10u 0.5 0.4 10u", tran)
        self.assertNotIn(".ac", tran)

    def test_unknown_mode_raises(self):
        with self.assertRaises(SpiceError):
            build_netlist("bode", self.inp, "q.lib", "QPROBE")


class ParserTests(unittest.TestCase):
    def test_parse_op_uses_collector_probe_not_supply_current(self):
        op = parse_op("Command: ngspice-47, Build Aug 11 2026", OP_RAW)
        self.assertAlmostEqual(op.vb, 1.942)
        self.assertAlmostEqual(op.ve, 1.242)
        self.assertAlmostEqual(op.vc, 9.294)
        self.assertAlmostEqual(op.vce, 9.294 - 1.242)
        self.assertAlmostEqual(op.ic, 0.001230)
        self.assertNotAlmostEqual(op.ic, 0.0013306)

    def test_parse_op_rejects_truncated_raw(self):
        truncated = OP_RAW.replace("No. Points: 1", "No. Points: 2")
        with self.assertRaises(SpiceError):
            parse_op("ngspice-47", truncated)

    def test_parse_op_marks_forward_active_without_warning(self):
        op = parse_op("ngspice-47", OP_RAW)
        self.assertEqual(op.region, "active")
        self.assertEqual(op.warnings, ())

    def test_parse_op_warns_when_vce_indicates_saturation(self):
        saturated = OP_RAW.replace("9.294000000000000e+00",
                                   "1.242000000000000e+00")
        op = parse_op("ngspice-47", saturated)
        self.assertEqual(op.region, "saturation")
        self.assertEqual(len(op.warnings), 1)
        self.assertIn("VCE = 0.000 V ≤ 0.2 V", op.warnings[0])
        self.assertIn("ไม่ควรใช้เทียบกับแบบจำลอง Forward-Active", op.warnings[0])

    def test_parse_op_warns_when_ic_indicates_cutoff(self):
        cut_off = OP_RAW.replace("1.230000000000000e-03",
                                 "-1.000000000000000e-04")
        op = parse_op("ngspice-47", cut_off)
        self.assertEqual(op.region, "cutoff")
        self.assertEqual(len(op.warnings), 1)
        self.assertIn("IC = -0.100 mA ≤ 0", op.warnings[0])

    def test_parse_ac_uses_base_node_after_cin(self):
        ac = parse_ac(AC_RAW)
        self.assertEqual(ac.frequency, [1.0, 1000.0, 1e6])
        self.assertAlmostEqual(ac.gain_db[0], 20.0)
        self.assertAlmostEqual(ac.gain_db[1], 40.0)
        self.assertAlmostEqual(ac.gain_db[2], 0.0)
        self.assertAlmostEqual(ac.phase_deg[1], 180.0, places=5)
        self.assertIsNotNone(ac.f_low)
        self.assertIsNotNone(ac.f_high)
        self.assertLess(ac.f_low, 1000.0)
        self.assertGreater(ac.f_high, 1000.0)

    def test_parse_ac_rejects_source_side_measurement(self):
        source_side = AC_RAW.replace("v(base)", "v(in)")
        with self.assertRaises(SpiceError):
            parse_ac(source_side)

    def test_parse_tran_marks_inverted(self):
        tran = parse_tran(TRAN_RAW)
        self.assertEqual(len(tran.time), 3)
        self.assertTrue(tran.inverted)
        self.assertAlmostEqual(tran.vin[0], 0.01)
        self.assertAlmostEqual(tran.vout[0], -0.1)

    def test_parse_tran_rejects_source_side_measurement(self):
        source_side = TRAN_RAW.replace("v(base)", "v(in)")
        with self.assertRaises(SpiceError):
            parse_tran(source_side)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.model = Path(self.tmp.name) / "toy.lib"
        self.model.write_text(".model QPROBE NPN(IS=1E-14 BF=100)\n",
                              encoding="utf-8")
        self.inp = parse_spice_inputs({
            "vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
            "re": "1k", "rl": "10k", "cin": "10", "cout": "10",
            "amplitude": "10", "frequency": "1",
        })
        self.cfg = SpiceConfig("ngspice", str(self.model), 30, None)

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_run(self, args, **kwargs):
        out = Path(kwargs["cwd"])
        (out / "run.log").write_text(
            "Command: ngspice-47, Build Aug 11 2026\n", encoding="utf-8")
        (out / "run.raw").write_text(OP_RAW, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_parses_real_output_shape(self, mock_run):
        mock_run.side_effect = self._fake_run
        result = run_analysis(ANALYSIS_DC, self.inp, self.cfg)
        self.assertEqual(result.status, "success")
        self.assertAlmostEqual(result.op.ic, 0.001230)
        self.assertEqual(result.engine_version, "ngspice-47")
        self.assertEqual(result.model_name, "QPROBE")

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_honours_model_name_override(self, mock_run):
        written = {}

        def capture(args, **kwargs):
            written["netlist"] = (Path(kwargs["cwd"]) / "circuit.cir").read_text(
                encoding="utf-8")
            return self._fake_run(args, **kwargs)

        mock_run.side_effect = capture
        cfg = SpiceConfig("ngspice", str(self.model), 30, "QPROBE2")
        result = run_analysis(ANALYSIS_DC, self.inp, cfg)
        self.assertEqual(result.model_name, "QPROBE2")
        self.assertIn("Q1 collector base emitter QPROBE2", written["netlist"])

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_rejects_ambiguous_model_file(self, mock_run):
        self.model.write_text(
            ".model QA NPN(IS=1E-14)\n.model QB NPN(IS=1E-14)\n",
            encoding="utf-8")
        with self.assertRaises(SpiceError) as ctx:
            run_analysis(ANALYSIS_DC, self.inp, self.cfg)
        self.assertIn("NGSPICE_MODEL_NAME", str(ctx.exception))
        mock_run.assert_not_called()

    @patch("spice_engine.subprocess.run")
    def test_relative_model_path_is_absolute_in_netlist(self, mock_run):
        captured = {}

        def capture(args, **kwargs):
            source = Path(kwargs["cwd"]) / "circuit.cir"
            captured["netlist"] = source.read_text(encoding="utf-8")
            return self._fake_run(args, **kwargs)

        mock_run.side_effect = capture
        relative = os.path.relpath(self.model, Path.cwd())
        cfg = SpiceConfig("ngspice", relative, 30, None)
        result = run_analysis(ANALYSIS_DC, self.inp, cfg)
        self.assertEqual(result.status, "success")
        self.assertIn(f'.include "{self.model.resolve().as_posix()}"',
                      captured["netlist"])

    def test_run_analysis_without_model_raises(self):
        with self.assertRaises(SpiceError) as ctx:
            run_analysis(ANALYSIS_DC, self.inp,
                         SpiceConfig("ngspice", None, 30, None))
        self.assertIn("model", str(ctx.exception).lower())

    def test_missing_model_error_tells_how_to_set_it(self):
        with self.assertRaises(SpiceError) as ctx:
            run_analysis(ANALYSIS_DC, self.inp,
                         SpiceConfig("ngspice", None, 30, None))
        message = str(ctx.exception)
        self.assertIn("$env:NGSPICE_MODEL", message)
        self.assertIn("restart Flask", message)

    def test_run_analysis_rejects_nonexistent_model_file(self):
        cfg = SpiceConfig("ngspice", str(Path(self.tmp.name) / "missing.lib"),
                          30, None)
        with self.assertRaises(SpiceError) as ctx:
            run_analysis(ANALYSIS_DC, self.inp, cfg)
        self.assertIn(" Starter Kit", str(ctx.exception))

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_empty_raw_raises(self, mock_run):
        def empty(args, **kwargs):
            (Path(kwargs["cwd"]) / "run.log").write_text("", encoding="utf-8")
            (Path(kwargs["cwd"]) / "run.raw").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, "", "")
        mock_run.side_effect = empty
        with self.assertRaises(SpiceError):
            run_analysis(ANALYSIS_DC, self.inp, self.cfg)

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_missing_output_files_raises_spice_error(self, mock_run):
        mock_run.side_effect = lambda args, **kwargs: subprocess.CompletedProcess(
            args, 0, "", "")
        with self.assertRaises(SpiceError):
            run_analysis(ANALYSIS_DC, self.inp, self.cfg)

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_malformed_numbers_raise_spice_error(self, mock_run):
        def malformed(args, **kwargs):
            out = Path(kwargs["cwd"])
            (out / "run.log").write_text("ngspice-47\n", encoding="utf-8")
            (out / "run.raw").write_text(
                OP_RAW.replace("1.942000000000000e+00", "not-a-number"),
                encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, "", "")
        mock_run.side_effect = malformed
        with self.assertRaises(SpiceError):
            run_analysis(ANALYSIS_DC, self.inp, self.cfg)

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_reports_engine_failure(self, mock_run):
        def failed(args, **kwargs):
            out = Path(kwargs["cwd"])
            (out / "run.log").write_text("error", encoding="utf-8")
            (out / "run.raw").write_text("error", encoding="utf-8")
            return subprocess.CompletedProcess(args, 1, "", "boom")
        mock_run.side_effect = failed
        with self.assertRaises(SpiceError):
            run_analysis(ANALYSIS_DC, self.inp, self.cfg)

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_reports_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("ngspice", 30)
        with self.assertRaises(SpiceError):
            run_analysis(ANALYSIS_DC, self.inp, self.cfg)


class SvgTests(unittest.TestCase):
    def test_bode_svg_has_units_and_data_points(self):
        ac = AcSeries([1.0, 1000.0, 1e6], [20.0, 40.0, 0.0], [180.0] * 3,
                       3.16, 3.16e5)
        svg = render_bode_svg(ac)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("Hz", svg)
        self.assertIn("dB", svg)
        self.assertIn("°", svg)
        self.assertIn("<polyline", svg)

    def test_bode_svg_draws_frequency_marker(self):
        ac = AcSeries([1.0, 1000.0, 1e6], [20.0, 40.0, 0.0], [180.0] * 3,
                       3.16, 3.16e5)
        svg = render_bode_svg(ac, marker_hz=1000.0)
        self.assertIn("marker", svg)
        self.assertIn("1e+03 Hz", svg)

    def test_corner_without_crossing_has_no_unit_after_text(self):
        ac = AcSeries([1.0, 1000.0], [20.0, 40.0], [180.0] * 2, None, None)
        svg = render_bode_svg(ac)
        self.assertIn("not determined in sweep range | fH not determined in sweep range",
                      svg)
        self.assertNotIn("not determined in sweep range Hz", svg)

    def test_wave_svg_changes_with_data(self):
        a = render_wave_svg(TranSeries([0.0, 0.001], [1.0, -1.0], [-1.0, 1.0], True))
        b = render_wave_svg(TranSeries([0.0, 0.001], [2.0, -2.0], [-2.0, 2.0], True))
        self.assertNotEqual(a, b)
        self.assertIn("ms", a)
        self.assertIn("V", a)


if __name__ == "__main__":
    unittest.main()

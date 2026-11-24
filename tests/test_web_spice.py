"""Flask test-client tests for the Analytical/SPICE dispatch."""

import unittest
from unittest.mock import patch

from app import app
from spice_engine import (ANALYSIS_AC, ANALYSIS_DC, ANALYSIS_TRAN, AcSeries,
                          OpPoint, SpiceConfig, SpiceError, SpiceResult,
                          TranSeries)


class SpiceDispatchTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.form = {"analysis": "dc", "vcc": "12", "r1": "100k", "r2": "22k",
                     "rc": "2.2k", "re": "1k", "rl": "10k", "cin": "10",
                     "cout": "10", "amplitude": "10", "frequency": "1",
                     "mode": "divider"}

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_valid_spice_post_shows_status_and_no_analytical_table(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30, "QPROBE")
        run.return_value = SpiceResult(
            ANALYSIS_DC, OpPoint(1.94, 1.24, 9.29, 8.05, 0.00123),
            None, None, "ngspice-47", "q.lib", "success")
        r = self.client.post("/", data=self.form)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"ngspice", r.data)
        self.assertIn(b"success", r.data)
        self.assertNotIn(b"results-table", r.data)

    def test_unknown_analysis_shows_error_not_default(self):
        r = self.client.post("/", data={**self.form, "analysis": "bode"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"error-panel", r.data)

    @patch("app.resolve_config")
    def test_first_spice_submit_uses_sample_fields_when_form_has_none(self, cfg):
        cfg.return_value = SpiceConfig("ngspice", None, 30, None)
        r = self.client.post("/", data={"analysis": "dc"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("ไม่พบ BJT model".encode("utf-8"), r.data)
        self.assertNotIn("กรุณากรอกตัวเลข".encode("utf-8"), r.data)

    def test_spice_invalid_shows_error_panel(self):
        r = self.client.post("/", data={**self.form, "re": "0"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"error-panel", r.data)
        self.assertNotIn(b"results-table", r.data)

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_spice_failure_clears_previous_results(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30, "QPROBE")
        run.side_effect = SpiceError("รัน ngspice ไม่สำเร็จ")
        r = self.client.post("/", data=self.form)
        self.assertIn(b"error-panel", r.data)
        self.assertNotIn(b"results-table", r.data)


class SpiceUiTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.form = {"analysis": "dc", "vcc": "12", "r1": "100k", "r2": "22k",
                     "rc": "2.2k", "re": "1k", "rl": "10k", "cin": "10",
                     "cout": "10", "amplitude": "10", "frequency": "1"}

    def test_get_has_four_analysis_options_and_analytical_default(self):
        html = self.client.get("/").get_data(as_text=True)
        for value in ("analytical", "dc", "ac", "tran"):
            self.assertIn(f'value="{value}"', html)
        self.assertIn('name="beta"', html)
        self.assertIn('name="vbe"', html)
        self.assertNotIn('name="rl"', html)

    def test_spice_mode_hides_beta_and_shows_source_fields(self):
        html = self.client.post("/", data={
            "analysis": "ac", "vcc": "12", "r1": "100k", "r2": "22k",
            "rc": "2.2k", "re": "1k", "rl": "10k", "cin": "10",
            "cout": "10", "amplitude": "10", "frequency": "1",
        }).get_data(as_text=True)
        self.assertNotIn('name="beta"', html)
        self.assertIn('name="rl"', html)
        self.assertIn("Amplitude", html)
        self.assertIn("Frequency", html)

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_dc_result_panel_uses_parsed_values_and_provenance(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30, "QPROBE")
        run.return_value = SpiceResult(
            ANALYSIS_DC, OpPoint(1.942, 1.242, 9.294, 8.052, 0.001230),
            None, None, "ngspice-47", "q.lib", "success")
        html = self.client.post("/", data={**self.form, "analysis": "dc"}).get_data(as_text=True)
        self.assertIn("ผลการจำลอง SPICE", html)
        self.assertIn("spice-table", html)
        for value in ("9.294", "8.052", "1.230"):
            self.assertIn(value, html)
        self.assertIn("ngspice-47", html)
        self.assertIn("q.lib", html)
        self.assertNotIn("results-table", html)

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_demo_model_shows_banner_and_is_not_lab_evidence(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30, "QPROBE", True)
        run.return_value = SpiceResult(
            ANALYSIS_DC, OpPoint(1.942, 1.242, 9.294, 8.052, 0.001230),
            None, None, "ngspice-47", "QPROBE", "success", True)
        html = self.client.post("/", data={**self.form, "analysis": "dc"}).get_data(as_text=True)
        self.assertIn("โมเดลเดโมชั่วคราว", html)
        self.assertIn("ห้ามใช้ผลนี้เป็นหลักฐาน B2–B6", html)
        self.assertIn("spice-table", html)

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_out_of_region_spice_op_shows_warning(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30, "QPROBE")
        run.return_value = SpiceResult(
            ANALYSIS_DC,
            OpPoint(1.242, 1.242, 1.242, 0.0, 0.001230, "saturation",
                    ("VCE = 0.000 V ≤ 0.2 V — ทรานซิสเตอร์อยู่ในช่วง Saturation — "
                     "ค่าจาก ngspice ไม่ควรใช้เทียบกับแบบจำลอง Forward-Active",)),
            None, None, "ngspice-47", "q.lib", "success")
        html = self.client.post("/", data={**self.form, "analysis": "dc"}).get_data(as_text=True)
        self.assertIn("ทรานซิสเตอร์อยู่ในช่วง Saturation", html)
        self.assertIn("ไม่ควรใช้เทียบกับแบบจำลอง Forward-Active", html)
        self.assertIn("spice-table", html)

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_ac_and_tran_results_render_only_real_svg(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30, "QPROBE")
        ac = AcSeries([100.0, 1000.0], [20.0, 40.0], [-180.0, -180.0],
                      100.0, 10000.0)
        run.return_value = SpiceResult(
            ANALYSIS_AC, None, ac, None, "ngspice-47", "q.lib", "success")
        html = self.client.post("/", data={**self.form, "analysis": "ac"}).get_data(as_text=True)
        self.assertIn("<svg", html)
        self.assertIn("Bode plot from ngspice AC data", html)
        self.assertNotIn("Waveform from ngspice transient data", html)

        run.return_value = SpiceResult(
            ANALYSIS_TRAN, None, None, TranSeries([0.0, 0.001], [0.01, -0.01],
                                                  [-0.1, 0.1], True),
            "ngspice-47", "q.lib", "success")
        html = self.client.post("/", data={**self.form, "analysis": "tran"}).get_data(as_text=True)
        self.assertIn("Waveform from ngspice transient data", html)
        self.assertNotIn("Bode plot from ngspice AC data", html)


if __name__ == "__main__":
    unittest.main()

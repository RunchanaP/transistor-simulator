"""Flask test-client tests for the DC bias web app."""

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
        for value in ("1.942", "1.242", "9.294", "8.052", "12.30"):
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
        self.assertIn("RTH =", html)

    def test_steps_compute_vc_before_vce(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        block = self.steps_block(html)
        self.assertIn("VC  = VCC − IC · RC", block)
        self.assertIn("9.294", block)

    def test_no_method_picker_on_page(self):
        for html in (self.client.get("/").get_data(as_text=True),
                     self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)):
            self.assertNotIn('name="method"', html)
            self.assertNotIn("วิธีประมาณ", html)
            self.assertNotIn("method-picker", html)

    def test_results_table_has_units(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        for unit in ("V", "mA", "µA"):
            self.assertIn(unit, html)

    def test_result_layout_marker_after_post(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        self.assertIn("layout--result", html)

    def test_no_result_layout_marker_on_get(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("layout--result", html)

    # --- steps block must never print a formula that disagrees with its own value ---
    #
    # In cutoff the junction is off: IB is zero because VTH <= VBE, not because
    # the forward-active expression happens to evaluate to zero. Printing
    # "(VTH - VBE) / (RTH + (beta+1)RE) = 0.00 uA" next to VTH = 0.119 V and
    # VBE = 0.70 V tells the reader the formula gives 0.00 when it gives -5.70.
    FORWARD_ACTIVE_IB = "RTH + (β+1)·RE"

    def steps_block(self, html):
        start = html.index('<div class="steps">')
        return html[start:html.index("</div>", start)]

    def test_cutoff_steps_do_not_apply_the_forward_active_formula(self):
        html = self.client.post("/", data=dict(SAMPLE_FORM, r2="1k")).get_data(as_text=True)
        self.assertNotIn(self.FORWARD_ACTIVE_IB, self.steps_block(html))

    def test_cutoff_steps_state_the_reason_and_the_zero_current(self):
        html = self.client.post("/", data=dict(SAMPLE_FORM, r2="1k")).get_data(as_text=True)
        block = self.steps_block(html)
        self.assertIn("Cutoff", block)
        self.assertIn("VTH ≤ VBE", block)
        self.assertIn("0.00 µA", block)

    def test_cutoff_steps_still_report_vth(self):
        html = self.client.post("/", data=dict(SAMPLE_FORM, r2="1k")).get_data(as_text=True)
        block = self.steps_block(html)
        self.assertIn("VTH", block)
        self.assertIn("0.119", block)          # VTH for R2 = 1k

    def test_active_steps_keep_the_forward_active_formula(self):
        html = self.client.post("/", data=SAMPLE_FORM).get_data(as_text=True)
        self.assertIn(self.FORWARD_ACTIVE_IB, self.steps_block(html))

    def test_saturation_steps_keep_the_forward_active_formula(self):
        html = self.client.post("/", data=dict(SAMPLE_FORM, rc="10k")).get_data(as_text=True)
        self.assertIn(self.FORWARD_ACTIVE_IB, self.steps_block(html))


if __name__ == "__main__":
    unittest.main()

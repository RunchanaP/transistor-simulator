"""Tests for the pure engineering module dc_bias.py (no Flask, no HTML)."""

import unittest

from dc_bias import BiasInput, ValidationError, parse_inputs, parse_resistance, solve_dc_bias

VALID = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
         "re": "1k", "beta": "100", "vbe": "0.7"}


class ParseResistanceTests(unittest.TestCase):
    def test_kilo_suffix(self):
        self.assertEqual(parse_resistance("100k"), 100_000.0)
        self.assertEqual(parse_resistance("2.2K"), 2_200.0)
        self.assertEqual(parse_resistance("22kΩ"), 22_000.0)

    def test_mega_suffix(self):
        self.assertEqual(parse_resistance("1M"), 1_000_000.0)
        self.assertEqual(parse_resistance("1meg"), 1_000_000.0)

    def test_bare_number_is_ohms(self):
        self.assertEqual(parse_resistance("2200"), 2_200.0)
        self.assertEqual(parse_resistance(" 2200 "), 2_200.0)

    def test_ohm_symbol_is_stripped(self):
        self.assertEqual(parse_resistance("2200Ω"), 2_200.0)

    def test_lowercase_m_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_resistance("5m")

    def test_thousands_separator_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_resistance("1,000")

    def test_thai_text_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_resistance("หนึ่งร้อย")


class ParseInputsTests(unittest.TestCase):
    def test_sample_values_parse_to_ohms(self):
        inp = parse_inputs(VALID)
        self.assertEqual(inp.r1, 100_000.0)
        self.assertEqual(inp.rc, 2_200.0)
        self.assertEqual(inp.beta, 100.0)
        self.assertEqual(inp.vbe, 0.7)

    def test_missing_field_is_collected(self):
        raw = dict(VALID)
        del raw["r2"]
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(raw)
        self.assertIn("r2", ctx.exception.errors)

    def test_zero_and_negative_resistance_are_collected(self):
        raw = dict(VALID, r1="0", re="-1")
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(raw)
        self.assertIn("r1", ctx.exception.errors)
        self.assertIn("re", ctx.exception.errors)

    def test_negative_beta_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, beta="-5"))
        self.assertIn("beta", ctx.exception.errors)

    def test_non_positive_vcc_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, vcc="0"))
        self.assertIn("vcc", ctx.exception.errors)

    def test_vbe_out_of_range_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, vbe="2.5"))
        self.assertIn("vbe", ctx.exception.errors)

    def test_non_finite_value_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, r1="inf"))
        self.assertIn("r1", ctx.exception.errors)

    def test_out_of_band_value_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, r1="1e13"))
        self.assertEqual(ctx.exception.errors["r1"], "ค่าตัวเลขไม่สมเหตุสมผล")

    def test_out_of_band_vcc_and_beta_are_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, vcc="20000", beta="1e6"))
        self.assertEqual(ctx.exception.errors["vcc"], "ค่าตัวเลขไม่สมเหตุสมผล")
        self.assertEqual(ctx.exception.errors["beta"], "ค่าตัวเลขไม่สมเหตุสมผล")

    def test_thai_text_in_field_is_collected(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_inputs(dict(VALID, r1="หนึ่งร้อย"))
        self.assertIn("r1", ctx.exception.errors)


class SolveTests(unittest.TestCase):
    def sample(self):
        return BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3,
                         re=1e3, beta=100.0, vbe=0.7)

    def test_reference_operating_point(self):
        r = solve_dc_bias(self.sample())
        self.assertAlmostEqual(r.vth, 2.16393, places=4)
        self.assertAlmostEqual(r.rth, 18_032.79, delta=0.05)
        self.assertAlmostEqual(r.ib * 1e6, 12.2986, places=3)
        self.assertAlmostEqual(r.ic * 1e3, 1.22986, places=4)
        self.assertAlmostEqual(r.ie * 1e3, 1.24216, places=4)
        self.assertAlmostEqual(r.ve, 1.24216, places=4)
        self.assertAlmostEqual(r.vb, 1.94216, places=4)
        self.assertAlmostEqual(r.vc, 9.29431, places=4)
        self.assertAlmostEqual(r.vce, 8.05216, places=4)
        self.assertEqual(r.region, "active")
        self.assertEqual(r.warnings, [])

    def test_kirchhoff_relations_hold(self):
        r = solve_dc_bias(self.sample())
        self.assertAlmostEqual(r.vb, r.ve + 0.7, places=6)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=6)
        self.assertAlmostEqual(r.ic, 100 * r.ib, places=9)
        self.assertAlmostEqual(r.ie, 101 * r.ib, places=9)

    def test_cutoff_when_vth_not_above_vbe(self):
        r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=1e3, rc=2.2e3,
                                    re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "cutoff")
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.ve, 0.0)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)
        self.assertTrue(r.warnings)

    def test_cutoff_at_exact_boundary(self):
        # r1 = r2 with vcc = 1.4 gives VTH = 0.7 exactly -> cutoff
        r = solve_dc_bias(BiasInput(vcc=1.4, r1=10e3, r2=10e3, rc=1e3,
                                    re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "cutoff")
        self.assertEqual(r.ic, 0.0)

    def test_saturation_warning_when_vce_low(self):
        r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=10e3,
                                    re=1e3, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "saturation")
        self.assertTrue(r.warnings)
        self.assertLess(r.vce, 0.3)

    def test_unusual_vbe_goes_to_notes_not_warnings(self):
        r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3,
                                    re=1e3, beta=100.0, vbe=1.0))
        self.assertEqual(r.region, "active")
        self.assertEqual(r.warnings, [])
        self.assertTrue(r.notes)


if __name__ == "__main__":
    unittest.main()

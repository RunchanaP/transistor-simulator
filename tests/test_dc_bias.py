"""Tests for the pure engineering module dc_bias.py (no Flask, no HTML)."""

import unittest

from dc_bias import (MODE_SAMPLES, BiasInput, EmitterInput, FixedInput,
                     ValidationError, normalize_mode, parse_emitter, parse_fixed,
                     parse_inputs, parse_resistance, solve_dc_bias, solve_emitter,
                     solve_fixed)

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


COMMON = {"vcc": "12", "rc": "2.2k", "beta": "100", "vbe": "0.7"}
A2 = dict(COMMON, rb="1M")
A3 = dict(A2, re="1k")


class ModeParsingTests(unittest.TestCase):
    def test_normalize_mode_accepts_all_three(self):
        self.assertEqual(normalize_mode("fixed"), "fixed")
        self.assertEqual(normalize_mode(" EMITTER "), "emitter")
        self.assertEqual(normalize_mode("divider"), "divider")

    def test_normalize_mode_rejects_unknown(self):
        for raw in ("bogus", "", None):
            with self.assertRaises(ValidationError) as ctx:
                normalize_mode(raw)
            self.assertIn("mode", ctx.exception.errors)

    def test_parse_fixed_ignores_unrelated_fields(self):
        inp = parse_fixed(dict(A2, r1="junk", r2="junk", re="junk"))
        self.assertEqual(inp.rb, 1_000_000.0)
        self.assertEqual(inp.rc, 2200.0)

    def test_parse_emitter_ignores_unrelated_fields(self):
        inp = parse_emitter(dict(A3, r1="junk", r2="junk"))
        self.assertEqual(inp.rb, 1_000_000.0)
        self.assertEqual(inp.re, 1000.0)

    def test_parse_fixed_rejects_zero_rb(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_fixed(dict(A2, rb="0"))
        self.assertEqual(ctx.exception.errors["rb"], "ค่าความต้านทานต้องมากกว่า 0")

    def test_parse_fixed_rejects_non_numeric_rb(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_fixed(dict(A2, rb="abc"))
        self.assertEqual(ctx.exception.errors["rb"], "กรุณากรอกตัวเลข")

    def test_mode_samples_match_worksheet(self):
        self.assertEqual(MODE_SAMPLES["fixed"]["rb"], "1M")
        self.assertEqual(MODE_SAMPLES["emitter"]["re"], "1k")
        self.assertEqual(MODE_SAMPLES["divider"], {
            "vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
            "re": "1k", "beta": "100", "vbe": "0.7",
        })


class ThreeModeSolverTests(unittest.TestCase):
    def sample(self):
        return BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3,
                         re=1e3, beta=100.0, vbe=0.7)

    def test_divider_reference_unchanged(self):
        r = solve_dc_bias(self.sample())
        for attr, expected in (("vb", 1.94216), ("ve", 1.24216), ("vc", 9.29431),
                               ("vce", 8.05216)):
            self.assertAlmostEqual(getattr(r, attr), expected, places=4)
        self.assertAlmostEqual(r.ic * 1e3, 1.22986, places=4)
        self.assertAlmostEqual(r.ib * 1e6, 12.2986, places=3)
        self.assertEqual(r.mode, "divider")

    def test_fixed_a2_reference(self):
        r = solve_fixed(FixedInput(vcc=12.0, rb=1e6, rc=2200.0, beta=100.0, vbe=0.7))
        self.assertAlmostEqual(r.ib * 1e6, 11.30, places=2)
        self.assertAlmostEqual(r.ic * 1e3, 1.130, places=3)
        self.assertAlmostEqual(r.ve, 0.0, places=6)
        self.assertAlmostEqual(r.vb, 0.700, places=3)
        self.assertAlmostEqual(r.vc, 9.514, places=3)
        self.assertAlmostEqual(r.vce, 9.514, places=3)
        self.assertEqual(r.region, "active")
        self.assertEqual(r.mode, "fixed")

    def test_emitter_a3_reference(self):
        r = solve_emitter(EmitterInput(vcc=12.0, rb=1e6, rc=2200.0,
                                       re=1000.0, beta=100.0, vbe=0.7))
        self.assertAlmostEqual(r.ic * 1e3, 1.026, places=3)
        self.assertAlmostEqual(r.ie * 1e3, 1.037, places=3)
        self.assertAlmostEqual(r.ve, 1.037, places=3)
        self.assertAlmostEqual(r.vb, 1.737, places=3)
        self.assertAlmostEqual(r.vc, 9.742, places=3)
        self.assertAlmostEqual(r.vce, 8.705, places=3)
        self.assertEqual(r.mode, "emitter")

    def test_emitter_a4_re_more_means_less_ic(self):
        a3 = solve_emitter(EmitterInput(12.0, 1e6, 2200.0, 1000.0, 100.0, 0.7))
        a4 = solve_emitter(EmitterInput(12.0, 1e6, 2200.0, 2000.0, 100.0, 0.7))
        self.assertLess(a4.ic, a3.ic)
        self.assertAlmostEqual(a4.ic * 1e3, 0.940, places=3)
        self.assertAlmostEqual(a4.vce, 8.033, places=3)

    def test_ib_nonpositive_is_cutoff(self):
        r = solve_fixed(FixedInput(vcc=0.5, rb=1e6, rc=2200.0, beta=100.0, vbe=0.7))
        self.assertEqual(r.region, "cutoff")
        self.assertEqual((r.ib, r.ic, r.ie, r.ve), (0.0, 0.0, 0.0, 0.0))
        self.assertEqual(r.vc, 0.5)
        self.assertTrue(r.warnings)

    def test_vce_between_020_and_030_is_active(self):
        r = solve_dc_bias(BiasInput(vcc=12.0, r1=100e3, r2=22e3, rc=8544.0,
                                    re=1e3, beta=100.0, vbe=0.7))
        self.assertGreater(r.vce, 0.2)
        self.assertLess(r.vce, 0.3)
        self.assertEqual(r.region, "active")


if __name__ == "__main__":
    unittest.main()

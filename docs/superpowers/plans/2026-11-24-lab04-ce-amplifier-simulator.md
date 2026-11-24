# Lab 04 CE Amplifier Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ต่อยอด Flask DC Bias app เดิมให้รัน ngspice จริงสำหรับ CE Voltage Divider อ้างอิงและแสดง DC/AC/Transient พร้อมกราฟที่มีหน่วย โดยไม่ทำให้ Lab 03 เสีย

**Architecture:** คง `dc_bias.py` และ 70 tests เดิมไว้; เพิ่ม `spice_engine.py` เป็น adapter ที่สร้าง netlist, เรียก `ngspice.exe` ด้วย `subprocess.run` แบบไม่ใช้ shell, parse ASCII raw/log เป็น array; `app.py` dispatch ระหว่าง Analytical กับ SPICE; Jinja แสดงกราฟ SVG ที่สร้างจากข้อมูลจริงฝั่งเซิร์ฟเวอร์ (ไม่เพิ่ม dependency/JS)

**Tech Stack:** Python 3.13.17, Flask 3.1.2, `unittest` (stdlib), ngspice 47 (external binary), SVG server-side

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-ce-amplifier-simulator-design.md`

## Global Constraints

- **ไม่เพิ่ม dependency**: `requirements.txt` คง `Flask==3.1.2` เท่านั้น; ห้าม CDN/ฟอนต์/JS ภายนอก (`AGENTS.md`)
- **ไม่แตะสมการ Lab 03**: `dc_bias.py` คง `solve_fixed/solve_emitter/solve_dc_bias`, `BiasResult`, A1–A5, 70 tests เดิมผ่าน
- **แยกความรับผิดชอบ**: `dc_bias.py` = สมการ/validation; `spice_engine.py` = netlist/run/parse; `app.py` = routing/format; template ไม่มีสมการฟิสิกส์; CSS เฉพาะ appearance
- **หน่วยฟอร์ม**: resistance `k/M` เหมือนเดิม; `Amplitude (mV)` → V (×1e-3), `Frequency (kHz)` → Hz (×1e3), `Cin/Cout (µF)` → F (×1e-6)
- **ช่วง validation**: `0 < amplitude ≤ 100 mV`, `1 Hz ≤ frequency ≤ 1 MHz`, `1 nF ≤ C ≤ 1000 µF`, `100 Ω ≤ R ≤ 10 MΩ`, `1 V ≤ VCC ≤ 24 V`
- **Sweep/tran**: `.ac dec 20 1 1e6`; -3 dB เทียบ gain สูงสุดใน sweep; `.tran 10u 0.5 0.4 10u`; ถ้าไม่มี crossoff ให้ข้อความ "not determined in sweep range"
- **Engine**: `NGSPICE_EXECUTABLE` → `shutil.which("ngspice")`; `NGSPICE_MODEL` ต้องชี้ไฟล์โมเดลจากอาจารย์; `NGSPICE_TIMEOUT` default 30 s; ติดตั้งแล้วที่ `C:\Users\B6829780\AppData\Local\ngspice-47\Spice64\bin\ngspice.exe`
- **โมเดล**: ต้องเป็นของ Instructor Starter Kit — ห้ามใช้ `pebjt.lib` หรือเดาค่า; ถ้าไม่มี → B2–B6 = `NOT RUN`
- **Error**: invalid input/run fail/empty output/timeout ต้อง HTTP 200 พร้อม error panel ภาษาไทย, `result=None`, ไม่มีกราฟ/ผลเก่าค้าง
- **Region warning**: กฎ `AGENTS.md` ข้อ 9 ใช้กับ Analytical เท่านั้น; SPICE รายงานค่าจริง/status
- **Commit**: agent ไม่รัน `git commit`/`git push` (`AGENTS.md` ข้อ 8) — ผู้ใช้ commit เอง
- **ทดสอบ**: `.venv\Scripts\python.exe -m unittest discover -s tests` ต้องเขียวทุกตัว including 70 เดิม

## Review Focus

| ความเสี่ยงที่ tests ใน task อาจยังไม่ครอบ | พฤติกรรมที่ควรเห็น | Task ที่ pin ไว้ |
|---|---|---|
| `ngspice.exe` หาย / PATH ค้าง | แจ้ง "ไม่พบ ngspice" เป็น error ไม่ใช่ success | Task 1 `test_resolve_config_missing_executable_raises`; Task 3 `test_run_analysis_reports_engine_failure` |
| `NGSPICE_MODEL` ไม่ชี้ไฟล์จริง | แจ้ง "ไม่พบ BJT model" และไม่รัน/ไม่โชว์ผล | Task 3 `test_run_analysis_without_model_raises` |
| เปลี่ยน amplitude/frequency แล้วกราฟไม่เปลี่ยน | ต้องเห็น waveform/Bode เปลี่ยนจาก run ใหม่ (ไม่ใช่ mock) | Task 7 B6 browser before/after soak comparison |
| ngspice exit ≠ 0 หรือ raw ว่าง | status Error, ไม่มี SVG/ผลเก่า แม้รอบก่อน success | Task 3 `test_run_analysis_empty_raw_raises`; Task 5 `test_spice_failure_clears_previous_results` |
| ใส่ `RE = 0` หรือค่าติดลบในฟอร์ม SPICE | error ภาษาไทยช่องนั้น, HTTP 200, ไม่มี results-table | Task 1 `test_parse_spice_inputs_rejects_nonpositive_values`; Task 5 `test_spice_invalid_shows_error_panel` |

---

### Task 1: Analysis mode, config, และ input parsing

**Files:**
- Create: `spice_engine.py` (part 1)
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `ValidationError` จาก `dc_bias.py`
- Produces: `ANALYSIS_ANALYTICAL`, `ANALYSIS_DC`, `ANALYSIS_AC`, `ANALYSIS_TRAN`, `ANALYSIS_MODES`, `SPICE_MODES`; `normalize_analysis(raw: str | None) -> str`; `SpiceError(Exception)`; `SpiceConfig(executable: str, model_path: str | None, timeout: int)`; `resolve_config(env: Mapping[str, str] | None = None) -> SpiceConfig`; `SpiceInput(vcc: float, r1: float, r2: float, rc: float, re: float, rl: float, cin: float, cout: float, amplitude: float, frequency: float)`; `parse_spice_inputs(form: Mapping[str, str]) -> SpiceInput`

- [ ] **Step 1: เขียน failing test สำหรับ analysis mode และ input conversion**

```python
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
```

- [ ] **Step 2: รัน test ให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL — `ModuleNotFoundError` / `ImportError` สำหรับ `spice_engine`

- [ ] **Step 3: เพิ่ม config resolution และ error tests**

```python
class ConfigTests(unittest.TestCase):
    def test_resolve_config_reads_env(self):
        cfg = resolve_config({
            "NGSPICE_EXECUTABLE": r"C:\fake\ngspice.exe",
            "NGSPICE_MODEL": r"C:\fake\q.lib",
            "NGSPICE_TIMEOUT": "45",
        })
        self.assertEqual(cfg.executable, r"C:\fake\ngspice.exe")
        self.assertEqual(cfg.model_path, r"C:\fake\q.lib")
        self.assertEqual(cfg.timeout, 45)

    def test_resolve_config_missing_executable_raises(self):
        with self.assertRaises(SpiceError) as ctx:
            resolve_config({"PATH": ""})
        self.assertIn("ngspice", str(ctx.exception))
```

รันซ้ำExpected: FAIL

- [ ] **Step 4: implement ใน `spice_engine.py`**

เขียน `SpiceError`, constants, `normalize_analysis`, `SpiceConfig`, `resolve_config`,
`SpiceInput`, `parse_spice_inputs` โดย reuse `parse_resistance` จาก `dc_bias.py`
สำหรับ `r1/r2/rc/re/rl`; แปลง `cin/cout/amplitude/frequency` จากหน่วยที่ป้ายไว้;
ตรวจ bounds ตาม Global Constraints แล้ว raise `ValidationError({field: Thai message})`
ห้าม import Flask

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: PASS ทุกตัว

- [ ] **Step 6: Commit (ผู้ใช้ตาม `AGENTS.md` ข้อ 8)**

ข้อความแนะนำ: `feat: add ngspice analysis config and input parsing`

---

### Task 2: Netlist builder สำหรับ `.op/.ac/.tran`

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `SPICE_MODES`, `SpiceInput`, `SpiceError` จาก Task 1
- Produces: `build_netlist(mode: str, inp: SpiceInput, model_path: str | None) -> str`

- [ ] **Step 1: เขียน failing test**

```python
class NetlistTests(unittest.TestCase):
    def setUp(self):
        self.inp = parse_spice_inputs({
            "vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
            "re": "1k", "rl": "10k", "cin": "10", "cout": "10",
            "amplitude": "10", "frequency": "1",
        })

    def test_dc_netlist_has_op_and_reference_topology(self):
        net = build_netlist(ANALYSIS_DC, self.inp, r"C:\models\q.lib")
        self.assertIn(".op", net)
        self.assertIn('.include "C:/models/q.lib"', net)
        self.assertIn("VCC vcc 0 DC 12", net)
        self.assertIn("R1 vcc base 100000", net)
        self.assertIn("R2 base 0 22000", net)
        self.assertIn("RC vcc collector 2200", net)
        self.assertIn("RE emitter 0 1000", net)
        self.assertIn("Q1 collector base emitter NPN", net)
        self.assertIn("Cin in base 1e-05", net)
        self.assertIn("Cout collector out 1e-05", net)
        self.assertIn("RL out 0 10000", net)
        self.assertIn("V1 in 0 SIN(0 0.01 1000) AC 0.01", net)

    def test_ac_and_tran_directives_are_distinct(self):
        ac = build_netlist(ANALYSIS_AC, self.inp, r"C:\models\q.lib")
        tran = build_netlist(ANALYSIS_TRAN, self.inp, r"C:\models\q.lib")
        self.assertIn(".ac dec 20 1 1e6", ac)
        self.assertNotIn(".tran", ac)
        self.assertIn(".tran 10u 0.5 0.4 10u", tran)
        self.assertNotIn(".ac", tran)

    def test_unknown_mode_raises(self):
        with self.assertRaises(SpiceError):
            build_netlist("bode", self.inp, None)
```

- [ ] **Step 2: รัน test ให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL with `name 'build_netlist' is not defined`

- [ ] **Step 3: implement `build_netlist`**

สร้าง string ด้วย topology เดียวกันทุก analysis (ตาม test), ใส่ `.include` เฉพาะเมื่อ
`model_path` ไม่ใช่ `None`; ใช้ `Path(model_path).as_posix()` ใส่ในเครื่องหมายคำพูด;
ห้ามใช้ `.control ... .endc` ร่วมกับ batch `-b -o -r`

- [ ] **Step 4: รัน test ให้ผ่าน**

- [ ] **Step 5: Commit (ผู้ใช้)** — `feat: generate CE voltage-divider ngspice netlist`

---

### Task 3: Runner และ ASCII raw/log parser

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `build_netlist`, `SpiceConfig`, `SpiceInput` จาก Task 1–2
- Produces: `OpPoint(vb: float, ve: float, vc: float, vce: float, ic: float)`;
  `AcSeries(frequency: list[float], gain_db: list[float], phase_deg: list[float], f_low: float | None, f_high: float | None)`;
  `TranSeries(time: list[float], vin: list[float], vout: list[float], inverted: bool)`;
  `SpiceResult(analysis: str, op: OpPoint | None, ac: AcSeries | None, tran: TranSeries | None, engine_version: str, model_name: str, status: str)`;
  `parse_op(log: str, raw: str) -> OpPoint`; `parse_ac(raw: str) -> AcSeries`;
  `parse_tran(raw: str) -> TranSeries`; `run_analysis(mode: str, inp: SpiceInput, cfg: SpiceConfig) -> SpiceResult`

รูป raw จริงที่ตรวจแล้ว: `Plotname: Operating Point|AC Analysis|Transient Analysis`,
`Flags: real|complex`, `Variables:\n\t<idx>\t<name>\t<type>`, `Values:` ตามด้วย
`<idx>\t<real>[,<imag>]` แล้ว `<real>[,<imag>]` ต่อตัวแปรที่เหลือ; `v(base)`, `v(emitter)`,
`v(collector)`, `i(vcc)`, `v(in)`, `v(out)`, `frequency`, `time` เป็นชื่อที่ใช้

- [ ] **Step 1: เขียน failing test สำหรับ parser ด้วย raw fixture สั้น ๆ**

```python
OP_RAW = """Title: test
Plotname: Operating Point
Flags: real
No. Variables: 4
No. Points: 1
Variables:
\t0\tv(base)\tvoltage
\t1\tv(emitter)\tvoltage
\t2\tv(collector)\tvoltage
\t3\ti(vcc)\tcurrent
Values:
0\t\t1.942000000000000e+00
\t1.242000000000000e+00
\t9.294000000000000e+00
\t-1.230000000000000e-03
"""

class ParserTests(unittest.TestCase):
    def test_parse_op_computes_vce_and_ic_direction(self):
        op = parse_op("Command: ngspice-47, Build Aug 11 2026", OP_RAW)
        self.assertAlmostEqual(op.vb, 1.942)
        self.assertAlmostEqual(op.ve, 1.242)
        self.assertAlmostEqual(op.vc, 9.294)
        self.assertAlmostEqual(op.vce, 9.294 - 1.242)
        self.assertAlmostEqual(op.ic, 0.001230)
```

เพิ่ม `test_parse_ac_uses_complex_pairs_and_finds_3db` (3 จุด gain 20/40/0 dB, phase ≈180°
→ `f_low < 1000 < f_high`) และ `test_parse_tran_marks_inverted` (vin/vout คนละเครื่องหมาย)

- [ ] **Step 2: รัน test ให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL with `name 'parse_op' is not defined`

- [ ] **Step 3: implement parser**

แยก section ด้วย `Plotname:`; อ่าน `Variables:` และ `Values:` ตามลำดับ; แปลง complex
`real,imag` เป็น magnitude/phase สำหรับ `v(out)/v(in)`; `gain_db = 20*log10(mag_ratio)`,
`phase_deg = degrees(phase_out − phase_in)`; `vce = vc − ve`, `ic = −i(vcc)`;
หา -3 dB จาก `max(gain_db) − 3` ด้วยการหาจุดครอสซิ่ง; ถ้าไม่มีให้ `None`
(UI จะแปลเป็นข้อความ "not determined in sweep range")

- [ ] **Step 4: เขียน runner test ด้วย stub subprocess**

```python
class RunnerTests(unittest.TestCase):
    def _fake_run(self, args, **kwargs):
        out = Path(kwargs["cwd"])
        (out / "run.log").write_text("Command: ngspice-47, Build Aug 11 2026\n", encoding="utf-8")
        (out / "run.raw").write_text(OP_RAW, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_parses_real_output_shape(self, mock_run):
        mock_run.side_effect = self._fake_run
        result = run_analysis(ANALYSIS_DC, self.inp,
                              SpiceConfig("ngspice", r"C:\q.lib", 30))
        self.assertEqual(result.status, "success")
        self.assertAlmostEqual(result.op.ic, 0.001230)
        self.assertEqual(result.engine_version, "ngspice-47")
        self.assertTrue(result.model_name.endswith("q.lib"))

    @patch("spice_engine.subprocess.run")
    def test_run_analysis_empty_raw_raises(self, mock_run):
        def empty(args, **kwargs):
            (Path(kwargs["cwd"]) / "run.log").write_text("", encoding="utf-8")
            (Path(kwargs["cwd"]) / "run.raw").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, "", "")
        mock_run.side_effect = empty
        with self.assertRaises(SpiceError):
            run_analysis(ANALYSIS_DC, self.inp, SpiceConfig("ngspice", "q.lib", 30))

    def test_run_analysis_without_model_raises(self):
        with self.assertRaises(SpiceError) as ctx:
            run_analysis(ANALYSIS_DC, self.inp, SpiceConfig("ngspice", None, 30))
        self.assertIn("model", str(ctx.exception).lower())
```

เพิ่ม `test_run_analysis_reports_engine_failure` (returncode 1 → `SpiceError`) และ
timeout test (`side_effect=subprocess.TimeoutExpired` → `SpiceError`)

- [ ] **Step 5: implement `run_analysis`**

ใช้ `tempfile.TemporaryDirectory()` ต่อรอบ; สร้างไฟล์ `circuit.cir`; เรียก
`subprocess.run([cfg.executable, "-b", "-o", log, "-r", raw, cir], timeout=cfg.timeout,
capture_output=True, text=True, cwd=tmp, shell=False)`; อ่าน log/raw; เรียก parser ตาม
`mode`; เก็บ `engine_version` จากบรรทัด `Command:` ใน raw; raise `SpiceError` ภาษาไทย
สำหรับ model หาย, returncode ≠ 0, timeout, log/raw ว่าง, parse ไม่ได้

- [ ] **Step 6: รัน test ให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: PASS

- [ ] **Step 7: Commit (ผู้ใช้)** — `feat: run ngspice batch and parse op/ac/tran output`

---

### Task 4: SVG chart rendering จากข้อมูลจริง

**Files:**
- Modify: `spice_engine.py`
- Test: `tests/test_spice_engine.py`

**Interfaces:**
- Consumes: `AcSeries`, `TranSeries` จาก Task 3
- Produces: `render_bode_svg(ac: AcSeries) -> str`; `render_wave_svg(tran: TranSeries) -> str`

- [ ] **Step 1: เขียน failing test**

```python
class SvgTests(unittest.TestCase):
    def test_bode_svg_has_units_and_data_points(self):
        ac = AcSeries([1.0, 1000.0, 1e6], [20.0, 40.0, 0.0], [180.0]*3, 3.16, 3.16e5)
        svg = render_bode_svg(ac)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("Hz", svg)
        self.assertIn("dB", svg)
        self.assertIn("°", svg)
        self.assertIn("<polyline", svg)

    def test_wave_svg_changes_with_data(self):
        a = render_wave_svg(TranSeries([0.0, 0.001], [1.0, -1.0], [-1.0, 1.0], True))
        b = render_wave_svg(TranSeries([0.0, 0.001], [2.0, -2.0], [-2.0, 2.0], True))
        self.assertNotEqual(a, b)
        self.assertIn("ms", a)
        self.assertIn("V", a)
```

- [ ] **Step 2: รัน test ให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_spice_engine.py" -v`
Expected: FAIL ด้วยชื่อฟังก์ชันที่ยังไม่มี

- [ ] **Step 3: implement renderer**

สร้าง SVG string จาก array จริง (ไม่ hard-code เส้น); แกนมี label/unit; downsample ≤2000 จุด;
escape ข้อความ; ถ้า `ac.f_low`/`f_high` เป็น `None` ให้ render ข้อความ
"not determined in sweep range" ใน SVG แทนเลข

- [ ] **Step 4: รัน test ให้ผ่าน**

- [ ] **Step 5: Commit (ผู้ใช้)** — `feat: render Bode and waveform SVG from ngspice data`

---

### Task 5: Flask dispatch ระหว่าง Analytical และ SPICE

**Files:**
- Modify: `app.py`
- Test: `tests/test_web_spice.py`

**Interfaces:**
- Consumes: `normalize_analysis`, `parse_spice_inputs`, `resolve_config`, `run_analysis`,
  `SpiceError`, `ValidationError`, `ANALYSIS_*` จาก Task 1–3; `render_bode_svg`,
  `render_wave_svg` จาก Task 4; `render_template` เดิม
- Produces: context `analysis`, `mode`, `values`, `spice_values`, `sample`, `result`,
  `spice_result`, `bode_svg`, `wave_svg`, `errors`, `status`, `engine`

- [ ] **Step 1: เขียน failing test**

```python
class SpiceDispatchTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.form = {"analysis": "dc", "vcc": "12", "r1": "100k", "r2": "22k",
                     "rc": "2.2k", "re": "1k", "rl": "10k", "cin": "10",
                     "cout": "10", "amplitude": "10", "frequency": "1",
                     "mode": "divider"}

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_valid_spice_post_shows_status_and_no_analytical_table(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30)
        run.return_value = SpiceResult(ANALYSIS_DC, OpPoint(1.94, 1.24, 9.29, 8.05, 0.00123),
                                       None, None, "ngspice-47", "q.lib", "success")
        r = self.client.post("/", data=self.form)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"ngspice", r.data)
        self.assertIn(b"success", r.data)
        self.assertNotIn(b"results-table", r.data)

    def test_unknown_analysis_shows_error_not_default(self):
        r = self.client.post("/", data={**self.form, "analysis": "bode"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"error", r.data.lower())  # error panel class

    def test_spice_invalid_shows_error_panel(self):
        r = self.client.post("/", data={**self.form, "re": "0"})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"error-panel", r.data)
        self.assertNotIn(b"results-table", r.data)

    @patch("app.run_analysis")
    @patch("app.resolve_config")
    def test_spice_failure_clears_previous_results(self, cfg, run):
        cfg.return_value = SpiceConfig("ngspice", "q.lib", 30)
        run.side_effect = SpiceError("รัน ngspice ไม่สำเร็จ")
        r = self.client.post("/", data=self.form)
        self.assertIn(b"error-panel", r.data)
        self.assertNotIn(b"results-table", r.data)
```

- [ ] **Step 2: รัน test ให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web_spice.py" -v`
Expected: FAIL ด้วย context/status ที่ยังไม่มี

- [ ] **Step 3: implement dispatch ใน `app.py`**

อ่าน `analysis = normalize_analysis(request.form.get("analysis"))` ก่อนเสมอ;
ถ้า `ANALYSIS_ANALYTICAL` ให้เดินเส้นทาง Lab 03 เดิมเป๊ะ (A1 regression);
ถ้า SPICE ให้ `parse_spice_inputs` → `resolve_config` → `run_analysis` →
`render_*_svg` → render context ด้านบน; catch `ValidationError`/`SpiceError` ตั้ง
`errors`, `status="error"`, `result=None`, `spice_result=None`, `svg=""`; ไม่ใส่ physics
ใน app.py; error ทุกกรณีคืน HTTP 200

- [ ] **Step 4: รัน test ให้ผ่าน including 70 เดิม**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests`
Expected: `Ran 70+N tests ... OK`

- [ ] **Step 5: Commit (ผู้ใช้)** — `feat: dispatch analytical and SPICE analysis in Flask`

---

### Task 6: UI mode-aware form และ provenance

**Files:**
- Modify: `templates/index.html`, `static/style.css`
- Test: `tests/test_web_spice.py`

**Interfaces:**
- Consumes: context ทั้งหมดจาก Task 5
- Produces: หน้าเว็บที่มี analysis dropdown 4 ค่า, field groups ตามโหมด, status pill,
  ป้าย `ngspice`, result section แยก Analytical/SPICE, SVG พร้อมแกน/หน่วย

- [ ] **Step 1: เขียน failing test**

```python
class SpiceUiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_has_four_analysis_options_and_analytical_default(self):
        html = self.client.get("/").get_data(as_text=True)
        for value in ("analytical", "dc", "ac", "tran"):
            self.assertIn(f'value="{value}"', html)
        self.assertIn('name="beta"', html)
        self.assertIn('name="vbe"', html)
        self.assertNotIn('name="rl"', html)

    def test_spice_mode_hides_beta_and_shows_source_fields(self):
        html = self.client.post("/", data={"analysis": "ac", "vcc": "12", "r1": "100k",
            "r2": "22k", "rc": "2.2k", "re": "1k", "rl": "10k", "cin": "10",
            "cout": "10", "amplitude": "10", "frequency": "1"}).get_data(as_text=True)
        self.assertNotIn('name="beta"', html)
        self.assertIn('name="rl"', html)
        self.assertIn("Amplitude", html)
        self.assertIn("Frequency", html)
```

- [ ] **Step 2: รัน test ให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_web_spice.py" -v`
Expected: FAIL ด้วย field/option ที่ยังไม่มี

- [ ] **Step 3: แก้ template/CSS**

เพิ่ม `<select name="analysis">` เหนือ bias dropdown; `analytical` → หน้าเดิมทุกประการ;
SPICE → ซ่อน `mode/beta/vbe`, โชว์ `rl/cin/cout/amplitude/frequency` พร้อม unit label;
result section แยกหัวข้อ; status pill + engine/model badge; ใส่ `{{ bode_svg|safe }}`
และ `{{ wave_svg|safe }}` เฉพาะที่มีข้อมูลจริง; CSS responsive ไม่ตัดกราฟ/ปุ่ม;
ห้ามใส่ JS หรือสมการฟิสิกส์ใน template

- [ ] **Step 4: รัน test + browser check desktop/mobile**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests`
Expected: PASS ทั้งหมด
Browser: เปิด `http://127.0.0.1:5000/` ด้วย OpenCode Browser, screenshot ~1280px และ ~390px,
สลับ analysis mode, ตรวจไม่มีเนื้อหาสำคัญถูกตัด (นี่คือหลักฐาน B8)

- [ ] **Step 5: Commit (ผู้ใช้)** — `feat: add analysis selector and SPICE result panels`

---

### Task 7: เอกสาร version/validation และ browser acceptance

**Files:**
- Modify: `AGENTS.md` (ขอบเขต Lab 04), `README.md`, `docs/validation.md`
- Test: full suite + browser B1/B7/B8; B2–B6 placeholders

**Interfaces:**
- Consumes: ทุก task ก่อนหน้า
- Produces: README ที่รันซ้ำได้, validation table B1–B8, browser evidence, git state พร้อม commit

- [ ] **Step 1: อัปเดต `AGENTS.md`**

เปลี่ยนข้อ 12 จาก "ห้ามเพิ่ม AC/transient/SPICE" เป็นขอบเขต Lab 04:
รองรับ SPICE เฉพาะ CE Voltage Divider อ้างอิง, analytical 3 โหมดยังอยู่,
ห้าม fabricate, โมเดลจากอาจารย์เท่านั้น

- [ ] **Step 2: อัปเดต `README.md`**

เพิ่มคำสั่งตั้งค่า:
`$env:NGSPICE_EXECUTABLE = "C:\Users\B6829780\AppData\Local\ngspice-47\Spice64\bin\ngspice.exe"`
`$env:NGSPICE_MODEL = "<path from instructor>"`; อธิบาย analysis modes, หน่วย,
version ngspice 47 (official package), วิธีรัน/ทดสอบ, ว่าต้อง restart terminal เพื่อ PATH

- [ ] **Step 3: เติม `docs/validation.md` section Lab 04**

ตาราง B1–B8 with columns Method/Input/Expected/Observed/Evidence/Status;
ใส่ method จริง `OpenCode Browser (tools.browser.*)`;
B1/B7/B8 ใส่ผลที่รันจริง; B2–B6 ใส่ `NOT RUN · รอโมเดลจากอาจารย์` จนกว่า
`NGSPICE_MODEL` จะชี้ไฟล์จริง; ระบุ SHA256 ของ package และ limitation (ไม่มี Playwright MCP/Impeccable)

- [ ] **Step 4: browser acceptance จริง**

B1: เปิด Fixed/Emitter/Divider ใส่ค่าจาก Lab 3 → ผลตรง A1–A4 ที่ record ไว้
B7: ใส่ `RE=0` ใน SPICE form → error ภาษาไทย, ไม่มีผลสำเร็จ
B8: desktop/mobile screenshot ตาม Task 6
B2–B6: ถ้าได้โมเดลจากอาจารย์แล้วให้รันจริงและอัปเดต status; ถ้ายังไม่ได้ปล่อย NOT RUN

- [ ] **Step 5: verification สุดท้าย**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests`
Expected: `OK`, exit 0
Run: `git status --short`
Expected: เฉพาะไฟล์ที่วางแผนไว้ (ไม่มี `.venv/`, `.env`, ไฟล์ run ชั่วคราว)

- [ ] **Step 6: Commit/Push (ผู้ใช้ตาม `AGENTS.md` ข้อ 8)**

ข้อความแนะนำ: `docs: add Lab 04 ngspice integration and browser validation`

---

## Self-review notes

- Spec §1–§3 ครอบ Task 1–7; §4 tool decisions อยู่ใน Global Constraints; §5 fixture อยู่ใน Task 1–2;
  §6 approaches อยู่ใน header; §7 architecture อยู่ใน Task 1–6; §8 validation อยู่ใน Task 7;
  §9 tests อยู่ในทุก task; §10 open items อยู่ใน Global Constraints/Task 7
- ทุก Review Focus มี test เจ้าของ (ดูตารางด้านบน)
- ประเภท/ชื่อสอดคล้องกัน: `normalize_analysis`, `SpiceInput`, `SpiceConfig`, `build_netlist`,
  `run_analysis`, `OpPoint/AcSeries/TranSeries/SpiceResult`, `render_*_svg`,
  context `analysis/spice_result/bode_svg/...`
- ยังไม่มี task ที่เขียนค่า gain/frequency สำเร็จรูป; ทุกเส้นกราฟมาจาก array ที่ parse ได้

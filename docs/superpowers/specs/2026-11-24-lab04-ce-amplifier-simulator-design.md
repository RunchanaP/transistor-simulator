# Design — Lab 04: BJT CE Amplifier Simulator v1 (ngspice)

**วันที่:** 2026-11-24
**ที่มา:** ใบงาน `Lab04_BJT_Amplifier_Simulator_2-2569.html` (ไฟล์ที่นักศึกษาส่งมา)
**ต่อจาก:** `2026-11-17-lab03-three-bias-circuits-design.md` (HEAD `869da0f`)
**สถานะ:** รออนุมัติก่อนเขียน implementation plan และแตะโค้ด

---

## 1. Intent / ทำไมต้องทำ

Lab 03 ส่ง Flask web app ที่คำนวณ DC bias แบบประมาณด้วย Python 3 โหมด
(Fixed / Emitter / Voltage Divider) และมี 70 tests ผ่าน ใบงาน Lab 04 ให้ใช้แอปนั้น
เป็นฐานเดียวกัน เพิ่ม **Common-Emitter Amplifier Simulator v1** ที่รัน **ngspice จริง**
สำหรับวงจรอ้างอิงแบบ Voltage Divider เพียง 1 วงจร แล้วแสดงผล `.op` / `.ac` / `.tran`
พร้อมกราฟที่มีแกนและหน่วย โดย **ต้องไม่ทำให้ DC Bias ทั้ง 3 แบบของ Lab 03 เสีย**

เหตุผลที่ต่อยอดแทนสร้างใหม่: ใบงานระบุชัดว่า "อย่าสร้างใหม่ อย่าเขียนทับงานเดิม",
"ใช้ starter files ถ้ามี และตรวจก่อนแก้" และให้คะแนนความต่อเนื่องจาก Lab 03 1 คะแนน

## 2. เป้าหมาย

1. คง `dc_bias.py`, 3 solver เดิม, 70 tests เดิม และผล Divider กับค่าตัวอย่างเดิมทุกประการ
2. เพิ่ม `spice_engine.py`: สร้าง netlist, เรียก `ngspice.exe` ด้วย `subprocess.run([...])`
   (ไม่ใช้ `shell=True`, มี `timeout`, แยก working directory ต่อรอบ), parse ผลจริงจาก
   log/raw พร้อมหน่วย
3. `app.py` แยกเส้นทาง **Analytical** (Lab 03) กับ **SPICE** (Lab 04) อย่างชัดเจน
   และแสดง provenance/status ว่า results มาจากแหล่งไหน
4. ฟอร์มเลือก Analysis Mode (`analytical` / `dc` / `ac` / `tran`) แบบ POST reload ไม่เพิ่ม JS
5. กราฟ Bode และ waveform สร้างเป็น SVG จากข้อมูลที่ parse ได้จริง ไม่ hard-code
6. บันทึก B1–B8 ใน `docs/validation.md` ด้วย tool ที่ใช้จริง ค่า/หน่วย/statuss
   และ version ngspice + ชื่อโมเดลที่ใช้จริง

## 3. ไม่ทำ / Anti-goals

- ไม่สร้างโปรเจกต์ใหม่, ไม่ย้ายสมการฟิสิกส์เข้า HTML, ไม่เพิ่ม JavaScript/CDN
- ไม่ทำ drag-drop editor, วงจรอิสระ, AC ของทุก bias mode, FET, bypass capacitor
  (`CE`), animated overlay, SPICE solver เขียนเอง, หรือ deploy สาธารณะ
- **ห้ามแต่งค่าหรือกราฟ**: ถ้า engine/model/run ไม่พร้อม ต้องแจ้ง error หรือ
  บันทึก `NOT RUN` ตามความจริง ห้ามโชว์กราฟเก่าพร้อมสถานะ Success
- **ห้ามเดา BJT model** — ต้องใช้โมเดลที่ Instructor Starter Kit ระบุชื่อ/พารามิเตอร์
- AI ไม่สร้างค่าคาดหมาย A1–A5 (ยังค้างอยู่) และไม่ตัดสิน PASS/FAIL กว่าจะได้ค่าจากนักศึกษา
- agent ไม่รัน `git commit` / `git push` ตาม `AGENTS.md` ข้อ 8 (เว้นแต่ผู้ใช้สั่งตรง ๆ)

## 4. ข้อกำหนดที่ตกลงแล้ว / สิ่งที่ agent ตัดสิน

| เรื่อง | ผล | เหตุผล |
|---|---|---|
| แหล่ง BJT model | **ตามใบงาน: รอโมเดลจาก Instructor Starter Kit** (ผู้ใช้เลือก "เอาตามที่ไฟล์ส่งไป") | ใบงานห้ามเดาค่าเฉพาะรุ่น; โมเดลตัวอย่างใน ngspice เป็น numerical NBJT ไม่เหมาะเทียบกับสมการ Lab 03 |
| ngspice | ติดตั้งแล้ว: official `ngspice-47_64.7z` จาก SourceForge extraction ที่ `C:\Users\B6829780\AppData\Local\ngspice-47\Spice64\bin\ngspice.exe` SHA256 `59225971BD68CDD1199443649AA4615A9E6D684933F205AB49006A3942518F5A`; ทดสอบ batch `.op` สำเร็จ | ผู้ใช้เลือกข้อ 3 (ให้ช่วยหา/ติดตั้ง) |
| PATH | เพิ่ม bin ลง User PATH แล้ว แต่ shell ปัจจุบันยัง inherit ค่าเก่า → adapter ต้องอ่าน env var `NGSPICE_EXECUTABLE` ก่อน fallback `shutil.which("ngspice")` | ต้องรันซ้ำได้แม้ยังไม่ restart OpenCode |
| สถาปัตยกรรม | ขยายแอปเดิม: `app.py` dispatch + `spice_engine.py` adapter; ไม่แยก route ใหม่ | ใบงานกำหนด reuse before rebuild; ฟอร์มเดียวอ่านง่ายกว่า |
| กราฟ | สร้าง SVG บนเซิร์ฟเวอร์จาก array ที่ parse ได้; ไม่เพิ่ม matplotlib/Plotly | `requirements.txt` มีแค่ Flask; `AGENTS.md` ห้าม JS/CDN |
| เครื่องมือตรวจ B1–B8 | **OpenCode Browser** (ใช้จริงใน Lab 03) ไม่ใช่ Playwright MCP (ไม่มี tool/MCP configured) | จะบันทึกชื่อ tool ตามความจริงใน validation |
| Impeccable | ไม่มี skill และไม่มี node/npx → ใช้ browser critique แบบ desktop/mobile แทน และระบุ limitation ตรง ๆ | อย่าอ้างว่าใช้ skill ที่ไม่ได้รัน |
| Commit | ผู้ใช้/commit ผ่าน GitHub Desktop เอง | `AGENTS.md` ข้อ 8 |

## 5. วงจรอ้างอิงและ input fixture (input เท่านั้น ไม่ใช่ผลที่ยืนยันแล้ว)

| พารามิเตอร์ | ค่าตั้งต้น |
|---|---|
| VCC / R1 / R2 | 12 V / 100 kΩ / 22 kΩ |
| RC / RE / RL | 2.2 kΩ / 1 kΩ / 10 kΩ |
| Cin / Cout | 10 µF / 10 µF |
| Source | 10 mV peak / 1 kHz (SIN) |
| BJT | ตามโมเดลที่อาจารย์ระบุ (ยังไม่ได้รับ) |
| Emitter bypass | ไม่มีใน baseline |

Vin วัดที่ **base node หลัง `Cin`**, Vout วัดที่ **collector หลัง `Cout` บน `RL`**
ต้องระบุจุดวัดนี้ในหน้าเว็บและ validation เพื่อไม่ให้ gain มาจากคนละตำแหน่ง

## 6. Approaches ที่พิจารณา

| ทางเลือก | สรุป | ทำไมไม่เลือก / เลือก |
|---|---|---|
| A | ขยายแอปเดิม + `spice_engine.py`, ฟอร์ม POST reload, SVG server-side | **เลือก** — ตรงใบงาน, ไม่เพิ่ม dependency, ยังไม่กระทบ 70 tests |
| B | เพิ่ม `static/app.js` + Plotly/CDN สำหรับกราฟโต้ตอบ | ขัด `AGENTS.md` (no JS/external) และต้อง增设 dependency โดยไม่จำเป็น |
| C | แยก route `/simulate` และฟอร์มใหม่ต่างหาก | ซ้ำฟอร์ม/สับสนผู้ใช้ และใบงานต้องการหน้าเดียวที่เลือก Analysis Mode ได้ |

## 7. โครงสร้างที่เลือก

### 7.1 ไฟล์ที่ใช้ซ้ำ (ห้ามเขียนทับโดยไม่จำเป็น)

- `dc_bias.py` — คงสมการ/parser/validation ของ Lab 03 ทุกบรรทัดที่เกี่ยวข้องกับ A1–A5
- `app.py` — เพิ่ม dispatch ตาม `analysis`; เก็บ helper format เดิมไว้
- `templates/index.html` — เพิ่ม analysis dropdown, field groups ตามโหมด, results/provenance
- `static/style.css` — ปรับเฉพาะ appearance (status pill, chart blocks, responsive)
- `tests/test_dc_bias.py`, `tests/test_web.py` — ห้ามลบ/แก้จน tests เดิม 70 ตัวเปลี่ยนความหมาย
- `README.md`, `docs/validation.md`, `AGENTS.md` — อัปเดตขอบเขต/วิธีรัน/หลักฐาน

### 7.2 ไฟล์ใหม่

- `spice_engine.py` — adapter เดียวสำหรับ `.op`, `.ac`, `.tran`
  - `SpiceConfig(executable, model_path, timeout)` + `resolve_config()` อ่าน
    `NGSPICE_EXECUTABLE`, `NGSPICE_MODEL`, `NGSPICE_TIMEOUT`
  - `parse_spice_inputs(form)` → dataclass `SpiceInput` (ตัวเลขที่ตรวจแล้วเท่านั้น)
  - `build_netlist(mode, inp, model)` → string; topology เดียวกันทุก analysis
  - `run_analysis(mode, inp, cfg)` → `SpiceResult` หรือ raise `SpiceError(Thai message)`
  - `parse_op(log, raw)`, `parse_ac(raw)`, `parse_tran(raw)` → array + หน่วย
  - `render_bode_svg(result)`, `render_wave_svg(result)` → SVG string จากข้อมูลจริง
- `tests/test_spice_engine.py` — netlist/parser/error paths ด้วย stub subprocess
  (ไม่ต้องพึ่ง ngspice จริงใน unit test)
- `tests/test_web_spice.py` — dispatch, status, field visibility, ไม่โชว์ผลเก่าตอน error

### 7.3 `spice_engine.py` รายละเอียด

- ใช้ `tempfile.TemporaryDirectory()` ต่อการรัน: เขียน `circuit.cir`, เรียก
  `subprocess.run([exe, "-b", "-o", log, "-r", raw, cir], timeout=cfg.timeout,
  capture_output=True, text=True, cwd=tmp, shell=False)`; ไม่ผสม `.control ... .endc`
  เข้ากับ batch mode ที่ใช้ `-b -o -r` (ตามคำเตือนในใบงาน)
- Netlist: ใช้ `.include <model_path>` ถ้ามี; ถ้าไม่มี → `SpiceError` ทันที
  ("ไม่พบ BJT model จาก Starter Kit — กรุณาตั้ง NGSPICE_MODEL") และ B2–B6 = NOT RUN
- `ValidationError`/`SpiceError` ภาษาไทยสำหรับ: engine หาย, model หาย, input ไม่ใช่ตัวเลข,
  ค่าติดลบ/ศูนย์, frequency/amplitude เกินช่วง, timeout, exit code ไม่เป็นศูนย์,
  log/raw ว่างหรือ parse ไม่ได้
- `.ac`: sweep ครอบคลุม low/high; หา -3 dB เทียบ midband; ถ้าไม่มีจุดตัดให้ข้อความ
  "not determined in sweep range" — ห้ามสร้างตัวเลขเอง
- DL configuration: `SpiceResult` มี `source="ngspice"`, `analysis`, `engine_version`,
  `model_name`, `status`, `units`, `samples` เพื่อให้ app แสดง provenance ได้

### 7.4 `app.py` dispatch

```
analysis = normalize_analysis(form.get("analysis"))  # analytical|dc|ac|tran
if analysis == "analytical":  ใช้ mode + parse_*/solve_* เดิม (B1 regression)
else:  mode ถูกล็อกเป็น CE divider reference; parse_spice_inputs();
       run_analysis(); render SPICE section; ผล Analytical อาจโชว์เป็น "reference"
       เฉพาะ DC พร้อมคำอธิบายสมมติฐานที่ต่างกัน
```

- unknown/missing `analysis` → error panel (ไม่ default เป็น SPICE หรือ analytical แบบเงียบ)
- error ทุกกรณี: `result=None`, `status="error"`, HTTP 200, ไม่มี results-table/graph ค้าง
- ปุ่ม/ฟอร์มใช้ POST reload เหมือน Lab 03; ตอน error ยังเห็นค่าที่กรอกเพื่อแก้ไข

### 7.5 UI

- Analysis dropdown อยู่เหนือ circuit dropdown; default `analytical` → หน้าเหมือน Lab 03 ทุกประการ
- SPICE mode: ซ่อน `β`, `VBE`, bias dropdown; โชว์ `VCC, R1, R2, RC, RE, RL, Cin, Cout,
  Amplitude, Frequency` (เฉพาะช่องที่ analysis นั้นใช้) + ป้าย `ngspice` + engine status
- ผลแยกหัวข้อชัด: "Analytical (Lab 03)" กับ "SPICE (ngspice)" และระบุหน่วยทุกตัวเลข
- กราฟมีแกน/หน่วย: Bode = Frequency (Hz) / Gain (dB) / Phase (°);
  Waveform = Time (ms) / Vin, Vout (V)
- Responsive ตรวจที่ ~1280 px และ ~390 px ด้วย browser จริง

### 7.6 ค่าที่ agent ตัดสินหลัง builder check (ผู้ใช้ตรวจได้ตอนอ่าน doc)

| เรื่อง | การตัดสิน | เหตุผล |
|---|---|---|
| หน่วยในฟอร์ม | กรอกเป็นหน่วยวิศวกรรมที่ป้ายกำกับไว้ (`mV`, `kHz`, `µF`, `kΩ`) แล้ว `parse_spice_inputs` แปลงเป็น SI (V, Hz, F, Ω) ก่อนสร้าง netlist | ตรงตามใบงานที่ให้ "ฟอร์มแสดงหน่วยชัด"; ป้องกันผิด 10³–10⁶ |
| ขอบเขต validation | `0 < amplitude ≤ 100 mV`, `1 Hz ≤ frequency ≤ 1 MHz`, `1 nF ≤ C ≤ 1000 µF`, `100 Ω ≤ R ≤ 10 MΩ`, `1 V ≤ VCC ≤ 24 V`; นอกช่วง → error ภาษาไทย | ครอบคลุม fixture และกัน netlist แปลก ๆ |
| `.ac` sweep | `.ac dec 20 1 1e6` (1 Hz–1 MHz, 20 points/decade); ช่อง `Frequency` เป็นจุด marker บนกราฟ ไม่ได้ขับ sweep | ใบงานต้องการช่วงครอบคลุมพอและจุดอ้างอิง -3 dB; การใช้ freq เดียวขับ sweep จะทำให้หา fL/fH ไม่ได้ |
| จุดอ้างอิง -3 dB | ใช้ gain สูงสุดใน sweep เป็น midband proxy; หา crossing ที่ `|gain| = peak_gain − 3 dB`; ถ้าไม่มีให้ข้อความ "not determined in sweep range" | กันการสร้างตัวเลขขึ้นเองตามใบงาน |
| `.tran` | `.tran 10u 0.5 0.4 10u` (รัน 0.5 s, บันทึกตั้งแต่ 0.4 s, timestep/smax 10 µs) → ข้อมูล 0.1 s สุดท้าย ≈ 100 รอบที่ 1 kHz; SVG downsample ≤ 2000 จุด | `Cout·RL ≈ 0.1 s` ถ้าเริ่มอ่านตั้งแต่ t=0 จะเห็น charging ไม่ใช่สัญญาณคงตัว; การตัดช่วงต้นทำให้ B5/B6 เทียบเฟส/ amplit ูได้ |
| Region warning | กฎ `AGENTS.md` ข้อ 9 ใช้กับ **Analytical เท่านั้น**; SPICE แสดง operating point จริง + status; ถ้าค่าจาก SPICE ชี้ cutoff/saturation ให้ข้อความข้อสังเกตตามข้อมูลจริง ไม่เอาคำเตือนของสมการประมาณมาใส่ | ใบงานระบุว่าการทำฟิสิกส์ cutoff/sat ด้วยสมการประมาณแทน SPICE อยู่นอกขอบเขต |

## 8. Validation / หลักฐาน (B1–B8)

| Case | เงื่อนไขก่อนรัน | วิธีตรวจจริง |
|---|---|---|
| B1 | พร้อมแล้ว | เปิด 3 bias mode ใส่ค่าจาก Lab 3 ตรงผลเดิม, สลับโหมดได้ |
| B2 | ต้องมี model | `.op` → VB/VE/VC/VCE/IC จาก log/raw + model/status |
| B3 | ต้องมี model | เปลี่ยน RE เดียวแล้ว run ซ้ำ → ผลเปลี่ยนจริง |
| B4 | ต้องมี model | `.ac` → axis/gain/phase จาก run จริง + engine output |
| B5 | ต้องมี model | `.tran` ที่ 10 mV/1 kHz → Vin/Vout vs time + ทิศกลับเฟส |
| B6 | ต้องมี model | เปลี่ยน amplitude/frequency → waveform เปลี่ยนจริง |
| B7 | พร้อมแล้ว (analytical) | ใส่ RE=0 → error ภาษาไทย, ไม่มีผลสำเร็จปลอม |
| B8 | พร้อมแล้ว | browser screenshot desktop/mobile + เปลี่ยนโหมด |

- บันทึก method/expected/observed/units/status/evidence ลง `docs/validation.md`
- ถ้าไม่ได้รันจริงให้เขียน `NOT RUN · รอโมเดลจากอาจารย์` พร้อมเหตุผล
- ต้องระบุ version ngspice (official package 47) และชื่อ/พารามิเตอร์ model ที่ใช้จริง

## 9. กลยุทธ์ทดสอบ

- รัน `.venv\Scripts\python.exe -m unittest discover -s tests` ต้องได้ **70 เดิม + ใหม่ ผ่านหมด**
- Unit test ของ adapter ใช้ stub subprocess/log/raw ตัวอย่างที่สร้างขึ้นในเทสต์
  (ไม่ถือว่าเป็นหลักฐานว่าค่าฟิสิกส์ถูกต้อง — ต้องรัน engine จริงใน B2–B6)
- ใช้ `verification-before-completion` ก่อนclaims ใด ๆ ว่า PASS/เสร็จ

## 10. สิ่งที่เหลือให้ผู้ใช้/ภายนอกตัดสิน

- **BJT model จากอาจารย์**: ต้องได้ชื่อรุ่น + ไฟล์ `.lib/.mod` หรือพารามิเตอร์ และ path
  ตั้ง `NGSPICE_MODEL` — ก่อนหน้านั้น B2–B6 ต้องเป็น NOT RUN
- Restart OpenCode/terminal เพื่อให้ `ngspice` ถูกพบผ่าน PATH (หรือตั้ง `NGSPICE_EXECUTABLE`)
- ค่าคาดหมาย A1–A5 ของ Lab 03 ยังค้างอยู่ (ห้ามเติมจากโปรแกรม)
- ติดตั้ง Impeccable skill หากต้องการให้ขั้นตอน UI critique ตรงตามใบงาน (ตอนนี้ทำไม่ได้)
- ผู้ใช้เป็นคน commit/push ตาม `AGENTS.md` ข้อ 8

---

**Approval:** ยังไม่获得อนุมัติ — หลังอนุมัติจึงเรียก `writing-plans` เพื่อเขียน implementation plan

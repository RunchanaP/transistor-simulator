# BJT CE Amplifier Simulator — ENG29 2121 Lab 04

Flask web app for **Lab 03 BJT DC bias** (Fixed / Emitter / Voltage-Divider) plus the
**Lab 04 CE amplifier SPICE extension**: real ngspice `.op`, `.ac`, and `.tran`
runs for the voltage-divider common-emitter reference circuit, with server-side SVG
charts and provenance. No JavaScript, no CDN, no external fonts.

Lab 03 + Lab 04 · Computer Programming for Electrical Engineers · 2/2569

---

## สิ่งที่แอปทำ

- **Analytical (Lab 03)** — เลือกวงจรได้ 3 โหมด (`fixed`, `emitter`, `divider`)
  ฟอร์มแสดงเฉพาะช่องที่ใช้ และคำนวณใน `dc_bias.py` ด้วยสมการ Forward-Active
  (`IB = (VTH − VBE)/(RTH + (β+1)RE)` สำหรับ Divider, ฯลฯ) พร้อมบล็อกขั้นตอน
  และเตือน Cutoff/Saturation (`IB ≤ 0`, `VCE ≤ 0.2 V`)
- **SPICE · DC (`.op`)** — อ่าน VB, VE, VC, VCE, IC จาก ngspice จริง
- **SPICE · AC Bode (`.ac dec 20 1 1e6`)** — พล็อต Gain (dB) และ Phase (°)
  จากข้อมูลที่ ngspice คืนมา พร้อม fL/fH (เทียบกับ gain สูงสุดในช่วงสวีป;
  ถ้าไม่มีจุดตัด -3 dB จะแสดง `not determined in sweep range`)
- **SPICE · Transient (`.tran 10u 0.5 0.4 10u`)** — พล็อต Vin/Vout จากข้อมูลจริง
  และตรวจว่าสัญญาณกลับเฟส 180° หรือไม่
- แสดง provenance ทุกครั้ง: engine version, BJT model ที่ใช้, analysis ที่รัน
- ทุกค่าที่แสดงมาจาก solver/ngspice เท่านั้น — ไม่มีการ hardcode ผลลัพธ์ลง template
- ข้อมูลเข้าผิด → HTTP 200 พร้อม error panel ภาษาไทย (ไม่ใช่ 500/traceback)
- ถ้าไม่ได้ตั้ง `NGSPICE_MODEL` → แจ้งว่าไม่พบโมเดลจาก Starter Kit และไม่สร้างโมเดลขึ้นเอง

## ความต้องการของระบบ

- Python 3.13 (ทดสอบกับ 3.13.17), Flask 3.1.2 (`requirements.txt`)
- ngspice 47 64-bit (official package `ngspice-47_64.7z`)
  - SHA256 ของ package ที่ติดตั้ง: `59225971BD68CDD1199443649AA4615A9E6D684933F205AB49006A3942518F5A`
  - ตัวอย่าง SHA256 ของ `ngspice.exe` ที่ตรวจภายหลัง: `FA4F083058C1799D9F6DA7AE2A99E3034B7BB92D056095DE7D2DF59E6F627D49`
- BJT model **จาก Instructor Starter Kit เท่านั้น** (ห้ามเดา/ใช้ `pebjt.lib` หรือโมเดลอื่น)
- ไม่ต้องใช้อินเทอร์เน็ตตอนรัน

## การติดตั้ง

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## การตั้งค่า ngspice

```powershell
$env:NGSPICE_EXECUTABLE = "C:\Users\B6829780\AppData\Local\ngspice-47\Spice64\bin\ngspice.exe"
$env:NGSPICE_MODEL = "<path from instructor>"
$env:NGSPICE_MODEL_NAME = "<ชื่อ .model ในไฟล์ — ถ้าฟิล์มีชื่อเดียวไม่ต้องตั้ง>"
```

หรือใส่ executable ลง `PATH` แล้ว **restart terminal** ก่อนรัน Flask (PATH ที่แก้ใหม่
จะไม่มีผลกับ terminal ที่เปิดอยู่แล้ว). ถ้าไม่ตั้ง `NGSPICE_EXECUTABLE` โปรแกรมจะหา
`ngspice` จาก PATH; ถ้าไม่ตั้ง `NGSPICE_MODEL` หรือ path ไม่ชี้ไฟล์จริง จะรันโหมด SPICE
ไม่ได้และแจ้ง error ในหน้าเว็บตามที่ออกแบบ (B2–B6 ยังเป็น `NOT RUN · รอโมเดลจากอาจารย์`)

ชื่อโมเดลอ่านจากบรรทัด `.model <name> NPN|PNP ...` ในไฟล์ที่อาจารย์ให้ ถ้าไฟล์มี
ชื่อเดียวโปรแกรมใช้ชื่อนั้น; ถ้ามีหลายชื่อหรือไม่มีเลยต้องตั้ง `NGSPICE_MODEL_NAME`
(ห้ามเดาชื่อเอง) ชื่อที่ใช้จริงแสดงใน provenance ทุกครั้ง

## การรัน

```powershell
.venv\Scripts\python.exe -m flask --app app run --debug
```

แล้วเปิด <http://127.0.0.1:5000/>

## การทดสอบ

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ต้องได้ **119 tests ... OK** (70 เดิมของ Lab 03 + 49 ใหม่สำหรับ SPICE: 38 adapter
tests ใน `test_spice_engine.py` และ 11 dispatch/UI tests ใน `test_web_spice.py`)

## การกรอกค่า

| Analysis | ช่องที่ใช้ | หน่วย |
|---|---|---|
| `analytical` | `mode, VCC, RB/R1/R2, RC, RE, β, VBE` | Ω (รับ `k`/`M` ได้), V, เท่า |
| `dc`, `ac`, `tran` | `VCC, R1, R2, RC, RE, RL, Cin, Cout, Amplitude, Frequency` | V, Ω, µF, mV, kHz |

- จุดวัดที่ใช้ตรงตาม design: `Vin = base หลัง Cin`, `Vout = collector หลัง Cout บน RL`,
  `IC = กระแสผ่าน RC` (วัดด้วย zero-volt probe `VRC` ไม่ใช่ `-i(vcc)` ที่รวมกระแสตัวหาร)
- ช่อง `Frequency` ในโหมด AC เป็น marker บนกราฟ Bode (sweep คงที่ `1 Hz–1 MHz`)
- ความต้านทานพิมพ์ `100k`, `2.2k`, `1M` หรือตัวเลขล้วน (Ω) ได้; `5m` ปฏิเสธ
- ถ้าเลือก SPICE จากฟอร์ม Analytical แล้วกด Run ทันที ระบบจะใช้ค่าตัวอย่าง
  (VCC 12 V, R1 100k, R2 22k, RC 2.2k, RE 1k, RL 10k, Cin/Cout 10 µF,
  Amplitude 10 mV, Frequency 1 kHz) — ช่องที่ผู้ใช้ล้างว่างไว้ยัง error ตามปกติ
- ทุกช่องมี parsing + validation ภาษาไทย + test

## โครงสร้างไฟล์

```
app.py                Flask routes, Analytical/SPICE dispatch (ไม่มี physics arithmetic)
dc_bias.py            สมการ 3 โหมด Lab 03 + parsing + validation (ไม่รู้จัก Flask/HTML)
spice_engine.py       config, input parsing, netlist, ngspice runner, parsers, SVG
templates/index.html  ฟอร์มตาม analysis + ผลลัพธ์ + steps + provenance (Jinja)
static/style.css      หน้าตา, responsive
tests/                unittest: engineering + HTTP + SPICE adapter
docs/validation.md    บันทึกตรวจรับ Lab 02/03/04 และหลักฐานเบราว์เซอร์
docs/evidence/        ภาพจาก OpenCode Browser และ headless Chrome
```

## หมายเหตุการตรวจรับ

ตาราง A1–A5 (Lab 03) และ B1–B8 (Lab 04) อยู่ใน `docs/validation.md`.
ค่าคาดหมายต้องมาจากการคำนวณมือของนักศึกษาเอง เอเจนต์บันทึกแต่สิ่งที่เห็นจริง
(OBSERVED) และยังไม่ตัดสิน PASS/FAIL จนกว่าจะได้รับค่าคาดหมาย

การ commit/push ทำโดยนักศึกษาใน GitHub Desktop ตาม `AGENTS.md` ข้อ 8 —
เอเจนต์ไม่รัน `git commit` หรือ `git push`

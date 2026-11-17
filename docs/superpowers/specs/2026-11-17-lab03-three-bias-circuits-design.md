# Design — Lab 03: สามวงจรไบอัสในเว็บ Flask เดิม

**วันที่:** 2026-11-17
**ที่มา:** ใบงาน `ENG29_2121_Lab03_BJT_Bias_Web_App.html` (ฉบับร่างสำหรับผู้สอนตรวจ)
**ต่อจาก:** `2026-11-10-bjt-dc-bias-exact-only-design.md`
**สถานะ:** รออนุมัติจากผู้ใช้ก่อนเขียน plan และแก้โค้ด

---

## 1. Intent / ทำไมต้องทำ

Lab 02 ส่งเว็บ Flask ที่คำนวณ **Voltage Divider Bias** ด้วยวิธี Thevenin อย่างเดียว
(commit `9ba86dc`) Lab 03 ให้ใช้เว็บนั้นเป็นจุดเริ่มต้น เพิ่ม **Fixed Bias** และ
**Emitter Bias แบบแหล่งจ่ายเดียว** โดยให้ผู้ใช้เลือกโหมดได้ และตรวจผลผ่านเบราว์เซอร์
ด้วยตาราง A1–A5

เหตุผลที่ต้องต่อยอดแทนสร้างใหม่: ใบงานระบุชัดว่า "ใช้โค้ดและฟอร์ม Lab 2 เป็นจุดเริ่มต้น
ไม่ต้องทำเว็บใหม่" และ "วงจรเดิมยังต้องให้ผลเดิมเมื่อกรอกค่าเดิม" (A1)

## 2. เป้าหมาย

1. `dc_bias.py` มีตัวแก้สมการแยกตามวงจร 3 ตัว คืน `BiasResult` รูปแบบเดียวกัน
2. `app.py` เลือกตัวแก้สมการด้วย `if/elif` จากค่าที่ส่งมา; โหมดไม่รู้จักต้อง error
   ห้ามเดาเป็น Divider
3. ฟอร์มเลือกโหมดได้ แสดงเฉพาะช่องที่โหมดนั้นใช้ และไม่แสดงผลเก่าตอนกรอกผิด
4. เกณฑ์นอกช่วง Active ใช้ตาม Lab 03 ทุกโหมด: `IB ≤ 0` → Cutoff, `VCE ≤ 0.2 V` → Saturation
5. 46 tests เดิมยังเขียว และมี test ใหม่สำหรับอินพุต `RB` ตามกฎ `AGENTS.md` ข้อ 3
6. เอกสาร (README, validation, AGENTS) ตรงกับแอปสามโหมด

## 3. ไม่ทำ / Anti-goals

- ไม่สร้างโปรเจกต์ใหม่ ไม่ย้ายสมการไปไว้ใน HTML ไม่เพิ่ม JavaScript
- ไม่ทำ SPICE, DC Load Line, AC, transient, bypass capacitor
- ไม่เขียนสคริปต์ Playwright หรือติดตั้ง dependency ใหม่ใน `requirements.txt`
- **AI ไม่สร้างค่าอ้างอิง A1–A5 เอง** — ค่าคาดหมายต้องมาจากการคำนวณมือของนักศึกษา
  agent ได้แต่ช่วยตรวจและรัน browser เพื่อเก็บ "ผลที่เห็นจริง"
- agent ไม่รัน `git commit` / `git push` (กฎ `AGENTS.md` ข้อ 8) เว้นแต่ผู้ใช้สั่งตรง ๆ

## 4. ข้อกำหนดที่ตกลงแล้วในระหว่าง brainstorming

| เรื่อง | ที่มาของการตัดสิน | ผล |
|---|---|---|
| เกณฑ์ Cutoff / Saturation | ผู้ใช้เลือกข้อ 2 | `IB ≤ 0` → cutoff, `VCE ≤ 0.2` → saturation ทั้ง 3 โหมด; สำหรับ Divider สมมูลกับ `VTH ≤ VBE` เดิม เพราะตัวหารเป็นบวก → A1 ไม่เปลี่ยน |
| โครงสร้างโค้ด | ผู้ใช้เลือกข้อ B | 3 input dataclass + 3 solver function ใน `dc_bias.py`, `BiasResult` รูปเดียว, `app.py` dispatch ด้วย `if/elif` |
| ฟอร์ม | agent ตัดสินและแจ้งแล้ว | dropdown + POST reload, ไม่ใช้ JS, แสดงเฉพาะช่องที่ใช้ |
| เครื่องมือตรวจ A1–A5 | agent ตัดสินและแจ้งแล้ว | ใช้ OpenCode Browser ที่มีอยู่แล้ว (ใบงานให้คะแนนเท่ากัน); ยังไม่เพิ่ม `opencode.json`/Playwright MCP |
| Test | agent ตัดสินและแจ้งแล้ว | คง 46 tests เดิม + เพิ่ม test เฉพาะ `RB` และโหมดใหม่ ตามกฎ repo ข้อ 3 (ตีความว่ใบงาน "ไม่ต้องเขียนใหม่" หมายถึงไม่บังคับ ไม่ได้ห้าม) |
| Commit | กฎ repo | agent ไม่ commit; ผู้ใช้ commit ใน GitHub Desktop เอง |

## 4.1 กรณี A1–A5 และค่าตัวอย่าง (จากใบงาน)

**ค่าร่วมทุกกรณี:** `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`

| กรณี | โหมด / ค่าที่กรอก | สิ่งที่ต้องตรวจ / บันทึก |
|---|---|---|
| A1 · โหมดเดิม | Divider · `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RE = 1 kΩ` | ผลตรงกับ Lab 2 ก่อนแก้; บันทึก `IC ___ mA`, `VCE ___ V` |
| A2 · Fixed | Fixed · `RB = 1 MΩ` | คำนวณได้โดยไม่ต้องกรอก `RE`; บันทึก `IC ___ mA`, `VCE ___ V` |
| A3 · Emitter | Emitter · `RB = 1 MΩ`, `RE = 1 kΩ` | มีช่องและใช้ค่า `RE`; บันทึก `IC ___ mA`, `VCE ___ V` |
| A4 · เปลี่ยนค่าเดียว | Emitter · เหมือน A3 แต่เปลี่ยน `RE = 2 kΩ` | ทำนายก่อนรันว่า `IC` เพิ่มหรือลดจาก A3 พร้อมเหตุผลสั้น ๆ แล้วเก็บผลจริง |
| A5 · อินพุตผิด | Fixed · `RB = 0` | มีข้อความให้แก้ `RB`, หน้าไม่ล่ม, ไม่โชว์ผลรอบก่อนเป็นผลรอบนี้ |

**`MODE_SAMPLES` ที่จะใส่ในโค้ด:**

```python
MODE_SAMPLES = {
    "divider": {"vcc": "12", "r1": "100k", "r2": "22k",
                "rc": "2.2k", "re": "1k", "beta": "100", "vbe": "0.7"},
    "fixed":   {"vcc": "12", "rb": "1M", "rc": "2.2k",
                "beta": "100", "vbe": "0.7"},
    "emitter": {"vcc": "12", "rb": "1M", "rc": "2.2k", "re": "1k",
                "beta": "100", "vbe": "0.7"},
}
```

ค่าคาดหมาย (`___`) เป็นของนักศึกษาต้องคำนวณมือ — agent ห้ามเติมเอง

## 5. Approaches ที่พิจารณา

| ทางเลือก | สรุป | ทำไมไม่เลือก / เลือก |
|---|---|---|
| A | `BiasInput` เดียวมี `rb, r1, r2, re` เป็น optional + `solve_dc_bias(inp, mode)` แยก branch ข้างใน | แก้ไฟล์น้อยสุด แต่สมการสามชุดปนกัน และ validation ตามโหมดยุ่งเหยิง |
| **B** | 3 input dataclass + 3 ฟังก์ชัน `solve_fixed / solve_emitter / solve_divider`; `app.py` dispatch; ใช้ `BiasResult` ร่วม | **เลือก** — ตรงกับใบงานว่า "แยกฟังก์ชัน Fixed และ Emitter, เลือกตามโหมด", Divider แตะน้อย, test แยกง่าย |
| C | แยก `fixed_bias.py`, `emitter_bias.py` อีกสองไฟล์ | ผิดกฎ `AGENTS.md` ที่ให้ `dc_bias.py` เป็นเจ้าของสมการ/validation ทั้งหมด |

## 6. โครงสร้างที่เลือก

### 6.1 `dc_bias.py`

- คงชื่อ `BiasInput` และ `solve_dc_bias(inp)` ไว้ **เหมือนเดิมเป๊ะ** สำหรับ Divider
  → 23 engineering tests เดิมไม่ต้องเปลี่ยน
- เพิ่ม:
  - `FixedInput(vcc, rb, rc, beta, vbe)`
  - `EmitterInput(vcc, rb, rc, re, beta, vbe)`
  - `solve_fixed(inp) -> BiasResult`
  - `solve_emitter(inp) -> BiasResult`
- ตัวแปรร่วมที่ใช้ได้ทุกโหมด:
  - `MODE_FIXED = "fixed"`, `MODE_EMITTER = "emitter"`, `MODE_DIVIDER = "divider"`
  - `MODES = (...)`
  - `normalize_mode(raw)` — คืนโหมดที่รองรับ; ค่าหาย/ไม่รู้จัก → `ValidationError({"mode": "โหมดวงจรไม่ถูกต้อง"})`
    (**ไม่ default เป็น Divider** ตามใบงาน)
  - `parse_fixed(raw)`, `parse_emitter(raw)`, `parse_divider(raw)` — เรียก helper ร่วม
    `parse_fields(raw, required)` ที่ใช้ `parse_resistance` / `_parse_plain` และ validation
    เดิม (finite, บวก, MAX_*, VBE 0–2) เฉพาะช่องที่โหมดต้องการ
- `SAMPLE_VALUES` คงอยู่สำหรับ Divider (ใช้ค่าเดิม `12 / 100k / 22k / 2.2k / 1k / 100 / 0.7`
  เพื่อรักษา A1); เพิ่ม `MODE_SAMPLES` ตามตารางข้อ 4.1 — Fixed ใช้ `rb=1M`,
  Emitter ใช้ `rb=1M, re=1k`, common `vcc=12, rc=2.2k, beta=100, vbe=0.7`
- `BiasResult` เพิ่มฟิลด์ `mode: str` (ไม่ลบฟิลด์เดิม)
  - ฟิลด์ `vth`, `rth` ยังเป็น `float` เสมอ: Divider ค่าเดิม; Fixed/Emitter ตั้งเป็น
    `vth = VCC`, `rth = RB` (เป็น Thevenin equivalent ของ networks จริง) — เป็น call ของ agent
    เพื่อไม่ต้องเปลี่ยน type และไม่กระทบ tests เดิม; template จะไม่โชว์ `VTH/RTH` ในโหมดเหล่านี้
- Region กลาง: คำนวณ `ib` ตามโหมด → ถ้า `ib <= 0` ให้ศูนย์ทุกกระแสและ `vc = vcc`
  → วาง `region = "cutoff"` พร้อม warning ภาษาไทย; ไม่งั้นคำนวณ `ic, ie, ve, vb, vc, vce`
  แล้ววาง `region = "active"` ถ้า `vce > VCE_SAT` มิฉะนั้น `"saturation"`
- `VCE_SAT` เปลี่ยนจาก `0.3` เป็น `0.2` และข้อความ warning อ้าง `0.2 V`
- ตรวจ `math.isfinite` ของค่าที่คำนวณเหมือนเดิม; หมายเหตุ VBE นอก 0.5–0.9 คงอยู่

### 6.2 `app.py`

- อ่าน `mode = normalize_mode(request.form.get("mode"))` ก่อนอย่างอื่น
- เลือกคู่ parser/solver ด้วย `if mode == ...: ... elif ...` (ห้าม dict dispatch ที่ซ่อน error)
- ส่ง `values=...` (รักษาสิ่งที่ผู้ใช้กรอก), `mode=mode`, `result=result`, `errors=errors`,
  `sample=MODE_SAMPLES[mode]` ให้ template
- ตอน error `result=None` เสมอ → ไม่มีผลเก่าค้าง
- ไม่มี physics arithmetic ในนี้

### 6.3 `templates/index.html` + `static/style.css`

- `<select name="mode">` มี 3 ตัวเลือก; <label for="mode"> ชัดเจน; ปุ่ม Calculate เดิมใช้ส่งโหมดด้วย
- แสดงช่องตามโหมดด้วย `{% if mode == ... %}`:
  - common: `vcc, rc, beta, vbe`
  - fixed: `rb`
  - emitter: `rb, re`
  - divider: `r1, r2, re`
- ภาพวงจร: 3 SVG แบบคงที่ สลับด้วย `{% if %}` (ภาพไม่ใช่สมการ → ไม่ผิดกฎข้อ 8)
- หัวข้อ/คำอธิบายเปลี่ยนตามโหมด
- บล็อก `steps` แยกตามโหมด แสดงสูตรที่ให้ค่าจริง:
  - Fixed: `IB=(VCC−VBE)/RB`, `IC=β·IB`, `IE=(β+1)·IB`, `VE=0`, `VB=VBE`,
    `VC=VCC−IC·RC`, `VCE=VC`
  - Emitter: `IB=(VCC−VBE)/(RB+(β+1)·RE)` แล้วเหมือน Fixed ตั้งแต่ `IC`
  - Divider: ชุด `VTH/RTH` เดิม (คงข้อความเดิมให้ A1 ตรง)
  - กรณี cutoff ทุกโหมด: แสดงเหตุผล `IB ≤ 0 → Cutoff` และ `IB=0` แทนสูตร active;
    สำหรับ Divider ยังคงบรรทัด `VTH ≤ VBE (...) → Cutoff` ไว้ด้วย เพื่อไม่ให้ regression
    test เดิม (`test_cutoff_steps_state_the_reason_and_the_zero_current`) เสีย — สองบรรทัดนี้สมมูลกัน
- ทุกปริมาณในตารางผล (`VB VE VC VCE IC IB IE`) ต้องโผล่ใน steps ตามกฎข้อ 10
- CSS: เพิ่ม styling ให้ select + form groups เท่านั้น; ไม่เพิ่ม CDN/JS

### 6.4 Tests และเอกสาร

- `tests/test_dc_bias.py`: คง 23 เดิม + เพิ่มกลุ่มสำหรับ `parse_fixed/parse_emitter`,
  `solve_fixed/solve_emitter`, `normalize_mode` (unknown → error), ค่าตัวอย่าง A2/A3
  จากตารางข้อ 4.1 (`RB=1M`, Emitter `RE=1k`) — ค่าที่ได้จากโปรแกรมใช้เป็น regression
  test ได้ แต่ **ห้ามใช้เป็นค่าอ้างอิงใน validation.md**
- `tests/test_web.py`: คง 23 เดิม + เพิ่ม mode routing, unknown mode error,
  ช่องที่ไม่ใช้ไม่โผล่, error ไม่โชว์ผลเก่า
- `README.md`: อธิบาย 3 โหมด, วิธีรัน, ตารางตัวอย่างที่มีช่อง `___` ให้นักศึกษาเติมค่ามือ
- `docs/validation.md`: ตาราง A1–A5 ตามใบงาน พร้อมคอลัมน์ วิธีตรวจ/หลักฐาน; ค่าคาดหมายเว้นว่าง
  ให้นักศึกษากรอก; ผลที่เห็นจริง agent เป็นคนเก็บจาก browser
- `AGENTS.md`: แก้ข้อ 10–12 และ Scope ให้พูดถึง 3 solver/3 โหมด, แก้ข้อ 9 เป็นเกณฑ์ `IB ≤ 0 / VCE ≤ 0.2`,
  เพิ่มกฎ "โหมดไม่รู้จักต้อง error" และ "ค่าอ้างอิงต้องมาจากนักศึกษา"

## 7. สิ่งที่เหลือให้ builder ตัดสินเอง

- รายละเอียด SVG แต่ละวงจร และชื่อ class ใน CSS
- ข้อความ warning ภาษาไทยที่แน่นอน (ต้องสื่อ `IB ≤ 0` / `VCE ≤ 0.2`)
- จำนวน test ที่เพิ่ม และชื่อ test method
- ลำดับการแก้ไฟล์ตาม TDD (เขียน test ของโหมดใหม่ก่อน solver → RED → GREEN)

## 8. เกณฑ์ยอมรับ

1. `python -m unittest discover -s tests` เขียวทั้งหมด (46 เดิม + เทสต์ใหม่)
2. `GET /` เห็น dropdown 3 ตัวเลือก; เปลี่ยนโหมดแล้วช่องที่ใช้เปลี่ยนตาม
3. `POST` โหมด fixed/exmitter ให้ค่าตรงกับสมการใบงาน; Divider ได้ `1.942/1.242/9.294/8.052/1.230/12.30/1.242` เหมือนเดิม
4. `POST mode=bogus` ได้ HTTP 200 พร้อม error เรื่อง mode ไม่ล้ม และไม่แสดงผล
5. ทุก results row มีหน่วย และมีบรรทัดใน steps ที่อธิบายค่านั้น
6. A5 (`fixed, RB=0`) แสดง error `RB` ไม่โชว์ผลรอบก่อน
7. `docs/validation.md` มีตาราง A1–A5 ที่ค่าคาดหมายเว้นว่างให้ผู้ใช้กรอก
8. ไม่มีการ commit จาก agent

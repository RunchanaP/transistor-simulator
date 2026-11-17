# Validation Record — BJT DC Bias Web App

การตรวจสอบผลลัพธ์เทียบกับ **การคำนวณมือที่เป็นอิสระจากตัวโปรแกรม**
(คำนวณก่อนเขียนโค้ด จากสมการใน design doc §7.5)

**Lab 02:** แบบจำลองเดียว — วิธี Thevenin (คิดกระแสเบสผ่าน `RTH`)
**Lab 03:** เพิ่ม Fixed Bias และ Emitter Bias — ดูข้อ 7 สำหรับตาราง A1–A5

## 1. ค่าอุปกรณ์ตัวอย่าง

```
VCC = 12 V   R1 = 100 kΩ   R2 = 22 kΩ   RC = 2.2 kΩ   RE = 1 kΩ
β   = 100    VBE = 0.70 V
```

## 2. การคำนวณมือ

```
VTH = 12 × 22k / (100k + 22k)      = 264 / 122        = 2.163934 V
RTH = 100k × 22k / (100k + 22k)    = 2200 / 122       = 18.032787 kΩ
IB  = (2.163934 − 0.70) / (18032.787 + 101×1000)
    = 1.463934 / 119032.787                            = 12.29858 µA
IC  = 100 × 12.29858 µA                                = 1.229858 mA
IE  = 101 × 12.29858 µA                                = 1.242157 mA
VE  = 1.242157 mA × 1 kΩ                               = 1.242157 V
VB  = 1.242157 + 0.70                                  = 1.942157 V
VC  = 12 − (1.229858 mA × 2.2 kΩ) = 12 − 2.705688      = 9.294312 V
VCE = 9.294312 − 1.242157                              = 8.052155 V
```

**Region:** `VCE = 8.052 V > 0.2 V` และ `VTH = 2.164 V > VBE = 0.70 V` → **Forward-Active**
(ข้อ 2–6 เป็นบันทึก Lab 02 — ตอนนั้นใช้เกณฑ์ `VCE ≤ 0.3 V`; Lab 03 ใช้ `0.2 V` ตาม `AGENTS.md` ข้อ 9)

## 3. เปรียบเทียบกับการแสดงผลของแอป

| ปริมาณ | คำนวณมือ | แอปแสดง | ต่างกัน |
|---|---|---|---|
| VB | 1.942157 V | 1.942 V | < 0.001 V |
| VE | 1.242157 V | 1.242 V | < 0.001 V |
| VC | 9.294312 V | 9.294 V | < 0.001 V |
| VCE | 8.052155 V | 8.052 V | < 0.001 V |
| IC | 1.229858 mA | 1.230 mA | < 0.001 mA |
| IB | 12.29858 µA | 12.30 µA | < 0.01 µA |
| IE | 1.242157 mA | 1.242 mA | < 0.001 mA |
| VTH | 2.163934 V | 2.164 V | < 0.001 V |
| RTH | 18.032787 kΩ | 18.03 kΩ | < 0.01 kΩ |
| Region | Active | ✅ Forward-Active | ตรงกัน |

ผลต่างทั้งหมดอยู่ในระดับการปัดเศษที่ตั้งใจ (ทศนิยม 3 ตำแหน่ง) ไม่ใช่ความคลาดเคลื่อนของสมการ

## 4. Lab 02 acceptance — เกณฑ์ตรวจรับ A1–A7 (บันทึกเก่า)

| # | เกณฑ์ | หลักฐาน |
|---|---|---|
| A1 | `GET /` เห็นฟอร์ม, HTTP 200 | `test_get_index_returns_form` + เปิดเบราว์เซอร์ที่ `127.0.0.1:5000` |
| A2 | `POST /` ให้ Python คำนวณ (ไม่ hardcode) | `test_post_valid_shows_computed_values`; เส้นทาง `app.index → solve_dc_bias()` |
| A3 | ค่าตรงกับการคำนวณอิสระ | ตารางข้อ 3 + `test_reference_operating_point` |
| A4 | `R≤0`, `β≤0`, ค่าที่ไม่ใช่ตัวเลข → error ชัดเจน หน้าไม่ล้ม | `test_post_zero_resistance_shows_error`, `test_post_thai_text_shows_error`, `test_post_missing_field_shows_error` — ทั้งหมดได้ HTTP 200 |
| A5 | เตือน Cutoff / Saturation | `test_cutoff_shows_warning_bar`, `test_saturation_shows_warning_bar`, `test_cutoff_at_exact_boundary` |
| A6 | ≥3 engineering tests + ≥1 Flask client test | 23 tests ใน `test_dc_bias.py` (engineering) + 23 tests ใน `test_web.py` (HTTP) |
| A7 | clone แล้วรันได้ตาม README | หัวข้อติดตั้ง/รัน/ทดสอบใน `README.md` ใช้คำสั่งเดียวกับที่รันจริง |

## 5. Test log ของ Lab 02 (รันจริงตอนนั้น — ไม่ใช่จำนวนปัจจุบัน)

```
$ .venv\Scripts\python.exe -m unittest discover -s tests -v

test_missing_field_is_collected ... ok
test_negative_beta_is_collected ... ok
test_non_finite_value_is_collected ... ok
test_non_positive_vcc_is_collected ... ok
test_out_of_band_value_is_collected ... ok
test_out_of_band_vcc_and_beta_are_collected ... ok
test_sample_values_parse_to_ohms ... ok
test_thai_text_in_field_is_collected ... ok
test_vbe_out_of_range_is_collected ... ok
test_zero_and_negative_resistance_are_collected ... ok
test_bare_number_is_ohms ... ok
test_kilo_suffix ... ok
test_lowercase_m_is_rejected ... ok
test_mega_suffix ... ok
test_ohm_symbol_is_stripped ... ok
test_thai_text_is_rejected ... ok
test_thousands_separator_is_rejected ... ok
test_cutoff_at_exact_boundary ... ok
test_cutoff_when_vth_not_above_vbe ... ok
test_kirchhoff_relations_hold ... ok
test_reference_operating_point ... ok
test_saturation_warning_when_vce_low ... ok
test_unusual_vbe_goes_to_notes_not_warnings ... ok
test_active_region_shows_green_pill ... ok
test_active_steps_keep_the_forward_active_formula ... ok
test_calculation_steps_are_shown ... ok
test_cutoff_shows_warning_bar ... ok
test_cutoff_steps_do_not_apply_the_forward_active_formula ... ok
test_cutoff_steps_state_the_reason_and_the_zero_current ... ok
test_cutoff_steps_still_report_vth ... ok
test_no_method_picker_on_page ... ok
test_no_result_layout_marker_on_get ... ok
test_result_layout_marker_after_post ... ok
test_results_table_has_units ... ok
test_saturation_shows_warning_bar ... ok
test_saturation_steps_keep_the_forward_active_formula ... ok
test_steps_compute_vc_before_vce ... ok
test_stylesheet_is_linked ... ok
test_get_index_returns_form ... ok
test_post_missing_field_shows_error ... ok
test_post_non_finite_shows_error ... ok
test_post_thai_text_shows_error ... ok
test_post_thousands_separator_shows_error ... ok
test_post_valid_shows_computed_values ... ok
test_post_very_long_input_does_not_crash ... ok
test_post_zero_resistance_shows_error ... ok

----------------------------------------------------------------------
Ran 46 tests in 0.046s

OK
```

**จำนวนปัจจุบัน (Lab 03):** 70 tests — 36 engineering tests ใน `test_dc_bias.py` +
34 HTTP tests ใน `test_web.py` (46 เดิม + 24 เพิ่มสำหรับสามโหมด)
รันจริงวันที่ 2026-11-17 ด้วย `.venv\Scripts\python.exe -m unittest discover -s tests` ได้ `OK`

## 6. เคสที่ทดสอบด้วยมือในเบราว์เซอร์ (Lab 02 — บันทึกเก่า)

| กรอก | ผลที่เห็น |
|---|---|
| ค่าตัวอย่าง (12 / 100k / 22k / 2.2k / 1k / 100 / 0.7) | VB 1.942 V · VE 1.242 V · VCE 8.052 V · IC 1.230 mA · ✅ Forward-Active; บล็อกขั้นตอนคำนวณมี `RTH`, `VC = VCC − IC·RC` |
| `RC = 10k` | ตัวเลขยังแสดง แต่มีแถบเตือนสีส้มเรื่อง VCE ต่ำกว่า VCE(sat) |
| `R2 = 1k` | แถบเตือน Cutoff (VTH ≤ VBE) — บล็อกขั้นตอนคำนวณระบุ `VTH ≤ VBE → Cutoff` และ `IB = 0` แทนสูตร Forward-Active |
| `R1 = 0` | กล่อง error แดง "ค่าความต้านทานต้องมากกว่า 0" หน้าไม่ล้ม |
| `R1 = หนึ่งร้อย` | กล่อง error "กรุณากรอกตัวเลข" |

---

## 7. Lab 03 — ตรวจรับ A1–A5 ในเบราว์เซอร์

ค่าในคอลัมน์ **คาดหมาย (นักศึกษา)** ต้องมาจากการคำนวณมือที่เป็นอิสระจากโปรแกรม
ของนักศึกษาเอง ห้ามเติมจากผลที่แอปแสดง — ช่องที่ยังไม่ได้คำนวณให้เขียน `___`
ห้ามตัดสิน PASS/FAIL ก่อนได้รับค่าคาดหมายจากนักศึกษา

ค่า common ทุกกรณี: `VCC = 12 V`, `RC = 2.2 kΩ`, `β = 100`, `VBE = 0.70 V`
(A1 ใช้ `R1/R2/RE` ตามต้นฉบับ Lab 02; A2 ไม่มี `RE`; A3/A4 ใช้ `RB` แทน `R1/R2`)

| กรณี | โหมดและค่า | คาดหมาย (นักศึกษา) | เห็นจริง | วิธีตรวจ | สถานะ | หลักฐาน |
|---|---|---|---|---|---|---|
| A1 · โหมดเดิม | Divider · `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RE = 1 kΩ` | `IC ___ mA`, `VCE ___ V` | IC 1.230 mA · VCE 8.052 V (VB 1.942, VE 1.242, VC 9.294, IB 12.30 µA, IE 1.242 · ✅ Forward-Active) | OpenCode Browser | OBSERVED · รอคาดหมาย | `docs/evidence/lab03-a1.png` |
| A2 · Fixed | Fixed · `RB = 1 MΩ` | `IC ___ mA`, `VCE ___ V` | IC 1.130 mA · VCE 9.514 V (IB 11.30 µA, IE 1.141 mA, VE 0.000, VB 0.700 · ✅ Forward-Active) | OpenCode Browser | OBSERVED · รอคาดหมาย | `docs/evidence/lab03-a2.png` |
| A3 · Emitter | Emitter · `RB = 1 MΩ`, `RE = 1 kΩ` | `IC ___ mA`, `VCE ___ V` | IC 1.026 mA · VCE 8.705 V (IB 10.26 µA, IE 1.037 mA, VE 1.037, VB 1.737 · ✅ Forward-Active) | OpenCode Browser | OBSERVED · รอคาดหมาย | `docs/evidence/lab03-a3.png` |
| A4 · เปลี่ยนค่าเดียว | Emitter · เหมือน A3 แต่เปลี่ยน `RE = 2 kΩ` | ทำนาย `IC` เพิ่ม/ลดจาก A3 พร้อมเหตุผลสั้น ๆ: ___; `IC ___ mA`, `VCE ___ V` | IC 0.940 mA · VCE 8.033 V (IB 9.40 µA, IE 0.950 mA, VE 1.899) — สังเกตว่า `IC` **ลด**จาก A3 เมื่อ `RE` เพิ่ม | OpenCode Browser | OBSERVED · รอคาดหมาย | `docs/evidence/lab03-a4.png` |
| A5 · อินพุตผิด | Fixed · `RB = 0` | error ที่ช่อง `RB`, หน้าไม่ล่ม, ไม่โชว์ผลรอบก่อน | error "ค่าความต้านทานต้องมากกว่า 0 (rb)" · ไม่มี results-table/steps · ไม่มีค่า 1.130 ค้างจากรอบก่อน · HTTP 200 | OpenCode Browser | OBSERVED · รอคาดหมาย | `docs/evidence/lab03-a5.png` |

**วิธีตรวจที่ใช้ (exact tools):** OpenCode Browser — `tools.browser.tabs.open` ที่
`http://127.0.0.1:5000/`, `tools.browser.snapshot` เพื่อหา ref, `tools.browser.select`
เลือกโหมด, `tools.browser.fill` ใส่ค่า, `tools.browser.click` กด Calculate,
`tools.browser.wait` รอข้อความ, `tools.browser.evaluate` อ่านตารางผล/ขั้นตอน/ช่องฟอร์ม,
`tools.browser.screenshot` เก็บภาพ (copy ไป `docs/evidence/lab03-a*.png`)
และ `tools.browser.network.list/get` ตรวจ POST body ตอนดีบัก A2

**ผลที่สังเกตได้จริง (ยังไม่ตัดสิน PASS/FAIL — รอคาดหมายจากนักศึกษา):**

- รันวันที่ 2026-11-17 หลัง restart Flask server ให้ serve template ใหม่ (server เก่าค้าง template Lab 02)
- A1 ตรงกับค่าที่บันทึกไว้ในข้อ 2–3 ของ Lab 02 ทุกประการ
- เพราะฟอร์มไม่มี JavaScript A2–A5 จึงต้องกด Calculate ครั้งแรกเพื่อให้ฟอร์มสลับช่องตามโหมด
  (ครั้งแรกขึ้น error ช่องที่ยังไม่ได้กรอก) แล้วกรอกค่าและกดอีกรอบ — ผลรอบที่สองเป็นผลที่บันทึกข้างบน
- A4: เมื่อ `RE` เพิ่ม 1 kΩ → 2 kΩ ค่า `IC` ที่เห็นจริงลด 1.026 → 0.940 mA (ยังรอทำนายจากนักศึกษา)
- A5: เริ่มจากหน้าที่มีผล A2 อยู่แล้ว แล้วเปลี่ยน `RB = 0` — ผลเก่าหายไปทั้งตาราง ไม่หลงเหลือ
- สถานะจะเปลี่ยนเป็น PASS/FAIL ได้ก็ต่อเมื่อนักศึกษาส่งค่าคำนวณมือและทิศทาง A4 มาเทียบ

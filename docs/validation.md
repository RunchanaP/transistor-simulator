# Validation Record — BJT DC Bias Web App

การตรวจสอบผลลัพธ์เทียบกับ **การคำนวณมือที่เป็นอิสระจากตัวโปรแกรม**
(คำนวณก่อนเขียนโค้ด จากสมการใน design doc §7.5)

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

**Region:** `VCE = 8.052 V > 0.3 V` และ `VTH = 2.164 V > VBE = 0.70 V` → **Forward-Active**

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

## 4. เกณฑ์ตรวจรับ A1–A7

| # | เกณฑ์ | หลักฐาน |
|---|---|---|
| A1 | `GET /` เห็นฟอร์ม, HTTP 200 | `test_get_index_returns_form` + เปิดเบราว์เซอร์ที่ `127.0.0.1:5000` |
| A2 | `POST /` ให้ Python คำนวณ (ไม่ hardcode) | `test_post_valid_shows_computed_values`; เส้นทาง `app.index → solve_dc_bias()` |
| A3 | ค่าตรงกับการคำนวณอิสระ | ตารางข้อ 3 + `test_reference_operating_point` |
| A4 | `R≤0`, `β≤0`, ค่าที่ไม่ใช่ตัวเลข → error ชัดเจน หน้าไม่ล้ม | `test_post_zero_resistance_shows_error`, `test_post_thai_text_shows_error`, `test_post_missing_field_shows_error` — ทั้งหมดได้ HTTP 200 |
| A5 | เตือน Cutoff / Saturation | `test_cutoff_shows_warning_bar`, `test_saturation_shows_warning_bar`, `test_cutoff_at_exact_boundary` |
| A6 | ≥3 engineering tests + ≥1 Flask client test | 23 tests ใน `test_dc_bias.py` (engineering) + 16 tests ใน `test_web.py` (HTTP) |
| A7 | clone แล้วรันได้ตาม README | หัวข้อติดตั้ง/รัน/ทดสอบใน `README.md` ใช้คำสั่งเดียวกับที่รันจริง |

## 5. Test log (รันจริง)

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
test_calculation_steps_are_shown ... ok
test_cutoff_shows_warning_bar ... ok
test_no_result_layout_marker_on_get ... ok
test_result_layout_marker_after_post ... ok
test_results_table_has_units ... ok
test_saturation_shows_warning_bar ... ok
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
Ran 39 tests in 0.070s

OK
```

## 6. เคสที่ทดสอบด้วยมือในเบราว์เซอร์

| กรอก | ผลที่เห็น |
|---|---|
| ค่าตัวอย่าง (12 / 100k / 22k / 2.2k / 1k / 100 / 0.7) | VB 1.942 V · VCE 8.052 V · ✅ Forward-Active |
| `RC = 10k` | ตัวเลขยังแสดง แต่มีแถบเตือนสีส้มเรื่อง VCE ต่ำกว่า VCE(sat) |
| `R2 = 1k` | แถบเตือน Cutoff (VTH ≤ VBE) |
| `R1 = 0` | กล่อง error แดง "ค่าความต้านทานต้องมากกว่า 0" หน้าไม่ล้ม |
| `R1 = หนึ่งร้อย` | กล่อง error "กรุณากรอกตัวเลข" |

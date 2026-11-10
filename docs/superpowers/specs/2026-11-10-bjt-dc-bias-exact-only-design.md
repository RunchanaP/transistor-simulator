# Design — เหลือวิธีคำนวณเดียว (Exact / Thevenin)

**วันที่:** 2026-11-10 · **ต่อจาก:** `2026-11-10-bjt-dc-bias-method-selector-design.md`
**สาเหตุ:** ผู้ใช้เปลี่ยนใจ — ต้องการให้แอปใช้ **วิธีแม่นยำ (Thevenin)** วิธีเดียว
ไม่ต้องมีปุ่มเลือกวิธีและไม่ต้องมีสมการแบบประมาณอยู่ในโค้ดเลย

## ผลที่ตามมา (ยอมรับแล้ว)

หน้าเว็บจะแสดงค่าของวิธีแม่นยำเสมอ:

| ปริมาณ | ค่าที่จะแสดง |
|---|---|
| VB | 1.942 V |
| VE | 1.242 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| IC | 1.230 mA |
| IB | 12.30 µA |
| IE | 1.242 mA |

เลขชุดนี้**ไม่ตรง**กับ 2.20 / 1.46 / 1.46 / 7.32 ในเฉลย (ชุดนั้นคือวิธีประมาณ)
ผู้ใช้รับทราบและเลือกทางนี้แล้ว

## ทางเลือกที่พิจารณา

| ทางเลือก | ผล | คำตัดสิน |
|---|---|---|
| A. ลบวิธีประมาณออกจากแอปทั้งหมด | โค้ด/เทสต์/เอกสารเหลือชุดเดียว | **เลือก** |
| B. เก็บปุ่มไว้ แต่เอกสารพูดถึงวิธีแม่นยำเท่านั้น | แอปยังมีสองวิธี ขัดกับคำขอ | ไม่เลือก |
| C. คงสองวิธีไว้ | ขัดกับคำขอ | ไม่เลือก |

## สิ่งที่เปลี่ยน

- `dc_bias.py`: ลบ `METHOD_APPROX`, `METHOD_EXACT`, `METHODS`, `DEFAULT_METHOD`,
  `normalize_method`, ฟิลด์ `method` ของ `BiasResult`, พารามิเตอร์ `method`
  และสาขาสมการประมาณ — `solve_dc_bias(inp)` กลับไปเป็น Thevenin ชุดเดียว
- `app.py`: ไม่มี `normalize_method` / `METHODS` / context `method`, `methods`
- `templates/index.html`: ลบ fieldset `.method-picker`, ป้าย `.method-label`,
  และสาขา steps ของวิธีประมาณ — เหลือ steps ชุดเดียว (มี `RTH`, `VC`, `VCE`)
- `static/style.css`: ลบ `.method-picker`, `.method-option`, `.method-label`
- `tests/`: ลบ `ApproximateMethodTests`, `MethodRoutingTests`, `MethodPresentationTests`
  ที่ผูกกับ method; คงเทสต์ solver/region/UI ที่เหลือ และปรับให้เรียกแบบไม่มี method
- เอกสาร: README, `docs/validation.md`, `AGENTS.md` เหลือวิธีเดียว

## ไม่ทำ

- ไม่เปลี่ยนสมการ ตัวเลข หรือค่าคงที่ของวิธีแม่นยำ
- ไม่แตะ parsing/validation, region logic, UI ส่วนอื่น
- ไม่ commit (กฎ AGENTS.md ข้อ 8)

## ยอมรับได้เมื่อ

- `solve_dc_bias()` ไม่รับพารามิเตอร์ method และให้ VB 1.942 V กับค่าตัวอย่าง
- หน้าเว็บไม่มีคำว่า "วิธีประมาณ" หรือ radio เลือกวิธี
- บล็อกขั้นตอนคำนวณแสดง `RTH` และ `VC` ครบ
- test suite เขียวทั้งหมด และจำนวน test ลดลงตามที่ลบ
- README / validation / AGENTS อธิบายวิธีเดียว

# Design Note — BJT DC Bias Web App

**วันที่:** 2026-11-10 · **วิชา:** ENG29 2121 Lab 02
**Design ฉบับเต็ม:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-web-app-design.md`
**แผนงาน:** `docs/superpowers/plans/2026-11-10-bjt-dc-bias-web-app.md`

## ขอบเขต

คำนวณ DC Operating Point ของวงจร BJT NPN Common Emitter แบบ Voltage-Divider Bias
ภายใต้สมมติฐาน Forward-Active เท่านั้น ไม่มี AC, transient, หรือ SPICE

## สถาปัตยกรรม

หนึ่ง route `/` รับทั้ง GET (แสดงฟอร์ม) และ POST (คำนวณ) แยกความรับผิดชอบเป็นสามชั้น:

| ชั้น | ไฟล์ | หน้าที่ |
|---|---|---|
| Presentation | `templates/index.html`, `static/style.css` | ฟอร์ม, ตารางผล, แถบเตือน — ไม่มีสมการ |
| Web | `app.py` | รับ HTTP, เรียก logic, จัดรูปแบบตัวเลข |
| Engineering | `dc_bias.py` | parse หน่วย, validate, แก้สมการ — pure function |

การพึ่งพาเป็นทางเดียว: `app.py → dc_bias.py` ทำให้สมการทดสอบได้โดยไม่ต้องมี HTTP

## ค่าคงที่และเกณฑ์

- `VCE_SAT = 0.3 V` — เกณฑ์เตือน Saturation (ค่าโดยทั่วไปของซิลิกอน ไม่ใช่ค่าอุปกรณ์จริง)
- `VTH ≤ VBE` → Cutoff (บังคับกระแสเป็นศูนย์)
- `VBE` นอกช่วง 0.5–0.9 V → `notes` (คำแนะนำ) ไม่ใช่ `warnings`
- เพดานความสมเหตุสมผล: `VCC ≤ 1e4 V`, `R ≤ 1e12 Ω`, `β ≤ 1e5`

## ทางเลือกที่ตัดสินใจ

เลือก **Server-side form POST + Jinja** แทน AJAX เพราะตรงกับเกณฑ์ตรวจรับ,
ทดสอบด้วย `test_client` ได้ตรงไปตรงมา, และใช้เวลา build น้อยกว่าในกรอบ 75 นาที

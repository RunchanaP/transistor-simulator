# BJT DC Bias Calculator — ENG29 2121 Lab 02

เว็บแอปพลิเคชัน Flask สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT
NPN Common Emitter แบบ **Voltage-Divider Bias** ภายใต้สมมติฐาน Forward-Active
(β คงที่, VBE คงที่) คำนวณด้วยวิธี Thevenin (คิดกระแสเบสผ่าน `RTH`)

Lab 02 · Computer Programming for Electrical Engineers · 2/2569

---

## สิ่งที่แอปทำ

- รับค่า `VCC, R1, R2, RC, RE, β, VBE` ผ่านฟอร์มบนเว็บ
- คำนวณด้วย Python backend (`dc_bias.py`) ไม่ใช่ตัวเลขที่เขียนค้างใน HTML
- แสดง `VB, VE, VC, VCE, IC, IB, IE` พร้อมหน่วย และบล็อก "ขั้นตอนคำนวณ"
  (`VTH, RTH, IB, IC, IE, VE, VB, VC, VCE`) สำหรับคัดลอกลงสมุด
- ตรวจสอบข้อมูลเข้าและแจ้ง error ภาษาไทยทีละช่อง
- เตือนเมื่อวงจรอยู่นอกช่วง Forward-Active (Cutoff / Saturation)

## ความต้องการของระบบ

- Python 3.13 (ทดสอบกับ 3.13.17)
- Flask 3.1.2 (ติดตั้งผ่าน `requirements.txt`)
- ไม่ต้องใช้อินเทอร์เน็ตตอนรัน — ไม่มี CDN, ฟอนต์ หรือ JS ภายนอก

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

## การรัน

```powershell
.venv\Scripts\python.exe -m flask --app app run --debug
```

แล้วเปิด <http://127.0.0.1:5000/>

## การทดสอบ

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ต้องได้ **46 tests ... OK** — 23 engineering tests ใน `test_dc_bias.py`
(7 การแปลงหน่วย, 10 validation, 6 solver) และ 23 HTTP tests ใน `test_web.py`

## การกรอกค่า

ช่องความต้านทานรับหน่วยได้โดยตรง:

| พิมพ์ | ความหมาย |
|---|---|
| `100k`, `100K` | 100 000 Ω |
| `2.2k` | 2 200 Ω |
| `1M`, `1meg` | 1 000 000 Ω |
| `2200` | 2 200 Ω (ไม่ใส่หน่วย = Ω) |
| `5m` | ❌ ปฏิเสธ (กำกวมระหว่าง milli และ mega) |

ช่อง `VCC`, `β`, `VBE` เป็นตัวเลขล้วน (V, เท่า, V)

## แบบจำลองและข้อจำกัด

สมการที่ใช้ (วิธี Thevenin):

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
IC  = β · IB
IE  = (β + 1) · IB
VE  = IE · RE
VB  = VE + VBE
VC  = VCC − IC · RC
VCE = VC − VE
```

ค่าที่ได้กับค่าอุปกรณ์ตัวอย่าง (12 V, 100k, 22k, 2.2k, 1k, β=100, VBE=0.70 V):

| ปริมาณ | ค่า |
|---|---|
| VB | 1.942 V |
| VE | 1.242 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| IC | 1.230 mA |
| IB | 12.30 µA |
| IE | 1.242 mA |

- **Cutoff** (`VTH ≤ VBE`): กระแสเป็นศูนย์, `VC = VCC` — แบบจำลอง Forward-Active ใช้ไม่ได้
- **Saturation** (`VCE ≤ 0.3 V`): ตัวเลขยังแสดง แต่มาจากสมการ Forward-Active
  จึงไม่ตรงกับวงจรจริง (ของจริง `VCE ≈ 0.2 V`)
- ไม่ใช่ SPICE — ไม่มีการแก้สมการแบบไม่เชิงเส้น, ไม่มี AC, ไม่มี transient

## ทำไมจึงเป็น Web App ไม่ใช่ไฟล์ HTML

1. **เปิด `templates/index.html` ตรง ๆ ได้แต่ไม่เท่ากับรัน Flask** — เบราว์เซอร์จะแสดง
   Jinja template ดิบ (`{{ }}`) และไม่มีอะไรคำนวณ เพราะการคำนวณอยู่ใน `dc_bias.py`
   ซึ่งถูกรันโดย Python เท่านั้น
2. **ฟอร์มส่งข้อมูลไป Python อย่างไร** — `<form method="post">` ทำให้เบราว์เซอร์ส่ง
   HTTP POST ไปที่ `/` พร้อมข้อมูลในรูป `application/x-www-form-urlencoded`
   Flask อ่านด้วย `request.form` แล้วเรียก `parse_inputs()` และ `solve_dc_bias()`
   จากนั้น `render_template()` สร้าง HTML ใหม่ส่งกลับมา
3. **แก้สมการใน `dc_bias.py` แล้วต้องแก้ HTML ไหม** — ไม่ต้อง ถ้าแก้แค่สูตรภายใน
   `solve_dc_bias()` เพราะ template แสดงค่าที่ส่งมาจาก Python อยู่แล้ว แต่ถ้าเพิ่ม
   ค่าใหม่ที่ต้องแสดง ต้องเพิ่มแถวในตารางผลลัพธ์ด้วย
4. **ทำไม Region ที่แบบจำลองใช้ไม่ได้ต้องมี Warning** — เพราะสมการ Forward-Active
   สมมติว่า `VBE ≈ 0.7 V` และ `IC = β·IB` ตลอด ซึ่งไม่จริงใน Cutoff/Saturation
   หากแสดงตัวเลขโดยไม่เตือน ผู้ใช้จะเข้าใจผิดว่าค่านั้นใช้ได้จริง

## โครงสร้างไฟล์

```
app.py              Flask routes (GET/POST /)
dc_bias.py          สมการ + parsing + validation (ไม่รู้จัก Flask/HTML)
templates/index.html  ฟอร์ม + ผลลัพธ์ (Jinja)
static/style.css    หน้าตา
tests/              unittest (engineering + HTTP)
docs/               design note, validation record, reflection
```

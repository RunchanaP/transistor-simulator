"""ngspice adapter for the Lab 04 reference CE amplifier.

This module owns netlist generation, the batch subprocess, output parsing, and
server-side SVG rendering. It has no Flask, HTTP, or template dependencies.
"""

from __future__ import annotations

import html
import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dc_bias import VCE_SAT, ValidationError, parse_resistance

ANALYSIS_ANALYTICAL = "analytical"
ANALYSIS_DC = "dc"
ANALYSIS_AC = "ac"
ANALYSIS_TRAN = "tran"
ANALYSIS_MODES = (ANALYSIS_ANALYTICAL, ANALYSIS_DC, ANALYSIS_AC, ANALYSIS_TRAN)
SPICE_MODES = (ANALYSIS_DC, ANALYSIS_AC, ANALYSIS_TRAN)


class SpiceError(Exception):
    """Raised when the external ngspice engine or its output cannot be used."""


_MODEL_MISSING_MSG = (
    "ไม่พบ BJT model จาก Starter Kit — กรุณาตั้ง NGSPICE_MODEL ให้ชี้ไฟล์ .model ที่อาจารย์ให้ "
    r'เช่น $env:NGSPICE_MODEL = "C:\path\to\instructor-model.lib" '
    "แล้ว restart Flask ก่อนรัน (ห้ามใช้โมเดลที่เดาขึ้นเอง)"
)


@dataclass(frozen=True)
class SpiceConfig:
    executable: str
    model_path: str | None
    timeout: int
    model_name: str | None
    demo: bool = False


_MODEL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MODEL_DECL_RE = re.compile(
    r"^\s*\.model\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:NPN|PNP)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _validate_model_name(name: object) -> str:
    """Accept only a plain SPICE identifier for the BJT model name."""
    candidate = str(name or "").strip()
    if not _MODEL_NAME_RE.fullmatch(candidate):
        raise SpiceError("NGSPICE_MODEL_NAME ต้องเป็นชื่อโมเดลที่ถูกต้อง (ตัวอักษร/ตัวเลข/_)")
    return candidate


def normalize_analysis(raw: object) -> str:
    """Return a supported analysis mode; report an unknown value as an error."""
    if raw is None:
        return ANALYSIS_ANALYTICAL
    if isinstance(raw, str):
        mode = raw.strip().lower()
        if mode in ANALYSIS_MODES:
            return mode
    raise ValidationError({"analysis": "Analysis mode ไม่ถูกต้อง"})


def resolve_config(env: Mapping[str, str] | None = None) -> SpiceConfig:
    """Resolve executable/model/timeout, preferring explicit environment values."""
    source = os.environ if env is None else env
    executable = str(source.get("NGSPICE_EXECUTABLE") or "").strip()
    if not executable:
        executable = shutil.which("ngspice", path=source.get("PATH")) or ""
    if not executable:
        raise SpiceError("ไม่พบ ngspice — กรุณาตั้ง NGSPICE_EXECUTABLE หรือเพิ่ม ngspice ใน PATH")

    model = str(source.get("NGSPICE_MODEL") or "").strip()
    if any(char in model for char in ('"', "\n", "\r")):
        raise SpiceError("NGSPICE_MODEL มีอักขระที่ใช้ใน netlist ไม่ได้")
    model_name = str(source.get("NGSPICE_MODEL_NAME") or "").strip()
    if model_name:
        model_name = _validate_model_name(model_name)
    raw_timeout = str(source.get("NGSPICE_TIMEOUT") or "30").strip()
    try:
        timeout = int(raw_timeout)
    except ValueError as exc:
        raise SpiceError("NGSPICE_TIMEOUT ต้องเป็นตัวเลขจำนวนเต็ม") from exc
    if timeout <= 0:
        raise SpiceError("NGSPICE_TIMEOUT ต้องมากกว่า 0")
    demo = str(source.get("NGSPICE_MODEL_IS_DEMO") or "").strip().lower() in {
        "1", "true", "yes"}
    return SpiceConfig(executable, model or None, timeout, model_name or None, demo)


def resolve_model_name(model_path: str, override: str | None = None) -> str:
    """Find the BJT model name declared by the instructor file; never guess one."""
    if override:
        return _validate_model_name(override)
    try:
        text = Path(model_path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SpiceError("ไม่สามารถอ่าน BJT model จาก Starter Kit ได้") from exc
    names = []
    for name in _MODEL_DECL_RE.findall(text):
        if name not in names:
            names.append(name)
    if len(names) == 1:
        return names[0]
    raise SpiceError(
        "ไม่พบชื่อ BJT model ที่ชัดเจนใน Starter Kit — กรุณาตั้ง NGSPICE_MODEL_NAME "
        f"(พบ {len(names)} ชื่อในไฟล์)" if names else
        "ไม่พบชื่อ BJT model ใน Starter Kit — กรุณาตั้ง NGSPICE_MODEL_NAME")


@dataclass(frozen=True)
class SpiceInput:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    amplitude: float
    frequency: float


RESISTANCE_FIELDS = ("r1", "r2", "rc", "re", "rl")
CAPACITOR_FIELDS = ("cin", "cout")


def _parse_plain(text: object) -> float:
    if text is None:
        raise ValueError("กรุณากรอกตัวเลข")
    raw = str(text).strip()
    if not raw:
        raise ValueError("กรุณากรอกตัวเลข")
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError("กรุณากรอกตัวเลข") from exc


def parse_spice_inputs(form: Mapping[str, object]) -> SpiceInput:
    """Parse engineering-unit form values into SI values used by the netlist."""
    errors: dict[str, str] = {}
    parsed: dict[str, float] = {}

    for field in RESISTANCE_FIELDS:
        try:
            parsed[field] = parse_resistance(form.get(field))
        except ValueError:
            errors[field] = "กรุณากรอกตัวเลข"

    for field in ("vcc", *CAPACITOR_FIELDS, "amplitude", "frequency"):
        try:
            parsed[field] = _parse_plain(form.get(field))
        except ValueError:
            errors[field] = "กรุณากรอกตัวเลข"

    for field, value in parsed.items():
        if not math.isfinite(value):
            errors[field] = "ค่าตัวเลขไม่สมเหตุสมผล"
        elif field == "vcc" and not 1.0 <= value <= 24.0:
            errors[field] = "VCC ต้องอยู่ระหว่าง 1 ถึง 24 V"
        elif field in RESISTANCE_FIELDS and not 100.0 <= value <= 10e6:
            errors[field] = "ค่าความต้านทานต้องอยู่ระหว่าง 100 Ω ถึง 10 MΩ"
        elif field in CAPACITOR_FIELDS and not 0.001 <= value <= 1000.0:
            errors[field] = "ค่าความจุต้องอยู่ระหว่าง 1 nF ถึง 1000 µF"
        elif field == "amplitude" and not 0.0 < value <= 100.0:
            errors[field] = "Amplitude ต้องอยู่ระหว่าง 0 ถึง 100 mV"
        elif field == "frequency" and not 0.001 <= value <= 1000.0:
            errors[field] = "Frequency ต้องอยู่ระหว่าง 0.001 ถึง 1000 kHz"

    if errors:
        raise ValidationError(errors)

    return SpiceInput(
        vcc=parsed["vcc"],
        r1=parsed["r1"],
        r2=parsed["r2"],
        rc=parsed["rc"],
        re=parsed["re"],
        rl=parsed["rl"],
        cin=parsed["cin"] * 1e-6,
        cout=parsed["cout"] * 1e-6,
        amplitude=parsed["amplitude"] * 1e-3,
        frequency=parsed["frequency"] * 1e3,
    )


def _num(value: float) -> str:
    """Format a number for a SPICE deck without locale or trailing zeros."""
    return format(value, ".15g")


def build_netlist(mode: str, inp: SpiceInput, model_path: str | None,
                  model_name: str | None) -> str:
    """Build the single CE voltage-divider topology for one analysis mode."""
    if mode not in SPICE_MODES:
        raise SpiceError("Analysis mode ไม่รองรับสำหรับ SPICE")
    if not model_path:
        raise SpiceError(_MODEL_MISSING_MSG)
    name = _validate_model_name(model_name)

    lines = ["* Lab04 CE voltage-divider reference amplifier",
             f'.include "{Path(model_path).as_posix()}"']

    lines.extend([
        f"VCC vcc 0 DC {_num(inp.vcc)}",
        f"R1 vcc base {_num(inp.r1)}",
        f"R2 base 0 {_num(inp.r2)}",
        f"VRC vcc rcnode DC 0",
        f"RC rcnode collector {_num(inp.rc)}",
        f"RE emitter 0 {_num(inp.re)}",
        f"Q1 collector base emitter {name}",
        f"Cin in base {_num(inp.cin)}",
        f"Cout collector out {_num(inp.cout)}",
        f"RL out 0 {_num(inp.rl)}",
        f"V1 in 0 SIN(0 {_num(inp.amplitude)} {_num(inp.frequency)}) "
        f"AC {_num(inp.amplitude)}",
    ])

    if mode == ANALYSIS_DC:
        lines.append(".op")
    elif mode == ANALYSIS_AC:
        lines.append(".ac dec 20 1 1e6")
    elif mode == ANALYSIS_TRAN:
        lines.append(".tran 10u 0.5 0.4 10u")

    lines.append(".end")
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class OpPoint:
    vb: float
    ve: float
    vc: float
    vce: float
    ic: float
    region: str = "active"
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class AcSeries:
    frequency: list[float]
    gain_db: list[float]
    phase_deg: list[float]
    f_low: float | None
    f_high: float | None


@dataclass(frozen=True)
class TranSeries:
    time: list[float]
    vin: list[float]
    vout: list[float]
    inverted: bool


@dataclass(frozen=True)
class SpiceResult:
    analysis: str
    op: OpPoint | None
    ac: AcSeries | None
    tran: TranSeries | None
    engine_version: str
    model_name: str
    status: str
    demo: bool = False


def _parse_raw(raw: str) -> tuple[str, list[str], list[list[str]]]:
    """Read ngspice ASCII raw into (plotname, variable names, value rows)."""
    plotname = ""
    variables: list[str] = []
    values: list[str] = []
    expected_rows: int | None = None
    section = ""

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("Plotname:"):
            plotname = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("No. Variables:"):
            pass
        elif stripped.startswith("No. Points:"):
            try:
                expected_rows = int(stripped.split(":", 1)[1].strip())
            except ValueError as exc:
                raise SpiceError("raw file มีจำนวนจุดไม่ถูกต้อง") from exc
        elif stripped.startswith("Variables:"):
            section = "variables"
        elif stripped.startswith("Values:"):
            section = "values"
        elif section == "variables" and stripped:
            parts = stripped.split()
            if len(parts) >= 2 and parts[0].isdigit():
                variables.append(parts[1])
        elif section == "values" and stripped:
            values.append(stripped.split()[-1])

    if not plotname or not variables or not values:
        raise SpiceError("ไม่สามารถอ่านผลลัพธ์จาก ngspice ได้")
    width = len(variables)
    if len(values) % width != 0:
        raise SpiceError("ข้อมูล raw file ไม่ครบตามจำนวนตัวแปร")
    rows = [values[i:i + width] for i in range(0, len(values), width)]
    if expected_rows is not None and len(rows) != expected_rows:
        raise SpiceError("ข้อมูล raw file ไม่ครบตามจำนวนจุดที่ระบุ")
    return plotname, variables, rows


def _row_value(row: list[str], variables: list[str], name: str) -> str:
    try:
        return row[variables.index(name)]
    except ValueError as exc:
        raise SpiceError(f"raw file ไม่มีตัวแปร {name}") from exc


def _as_complex(token: str) -> complex:
    if "," in token:
        real, imag = token.split(",", 1)
        return complex(float(real), float(imag))
    return complex(float(token), 0.0)


def _half_power_frequency(f1: float, g1: float, f2: float, g2: float,
                          threshold: float) -> float | None:
    if g1 == g2 or (g1 - threshold) * (g2 - threshold) > 0:
        return None
    fraction = (threshold - g1) / (g2 - g1)
    if not 0.0 <= fraction <= 1.0:
        return None
    return math.exp(math.log(f1) + fraction * (math.log(f2) - math.log(f1)))


def parse_op(log: str, raw: str) -> OpPoint:
    """Extract the DC operating point from a real ngspice raw file."""
    del log  # log is retained in the interface for engine provenance
    _, variables, rows = _parse_raw(raw)
    if not rows:
        raise SpiceError("raw file ไม่มี operating point")
    row = rows[0]
    vb = float(_row_value(row, variables, "v(base)"))
    ve = float(_row_value(row, variables, "v(emitter)"))
    vc = float(_row_value(row, variables, "v(collector)"))
    # VRC is a zero-volt current probe in series with RC; i(vcc) would also
    # include the R1/R2 divider current and is therefore not IC.
    ic = float(_row_value(row, variables, "i(vrc)"))
    vce = vc - ve
    warnings: tuple[str, ...] = ()
    if ic <= 0:
        region = "cutoff"
        warnings = (
            f"IC = {ic * 1000:.3f} mA ≤ 0 — ทรานซิสเตอร์อยู่ในช่วง Cutoff — "
            "ค่าจาก ngspice ไม่ควรใช้เทียบกับแบบจำลอง Forward-Active",
        )
    elif vce <= VCE_SAT:
        region = "saturation"
        warnings = (
            f"VCE = {vce:.3f} V ≤ {VCE_SAT:.1f} V — "
            "ทรานซิสเตอร์อยู่ในช่วง Saturation — "
            "ค่าจาก ngspice ไม่ควรใช้เทียบกับแบบจำลอง Forward-Active",
        )
    else:
        region = "active"
    return OpPoint(vb=vb, ve=ve, vc=vc, vce=vce, ic=ic,
                   region=region, warnings=warnings)


def parse_ac(raw: str) -> AcSeries:
    """Convert complex AC raw pairs into gain/phase and -3 dB corners."""
    _, variables, rows = _parse_raw(raw)
    frequency: list[float] = []
    gain_db: list[float] = []
    phase_deg: list[float] = []
    for row in rows:
        # ngspice stores the AC frequency as a complex token in the raw file.
        freq = _as_complex(_row_value(row, variables, "frequency")).real
        vin = _as_complex(_row_value(row, variables, "v(base)"))
        vout = _as_complex(_row_value(row, variables, "v(out)"))
        if vin == 0:
            raise SpiceError("สัญญาณอินพุต AC เป็นศูนย์ ไม่สามารถหา gain ได้")
        ratio = vout / vin
        frequency.append(freq)
        gain_db.append(20.0 * math.log10(abs(ratio)))
        phase_deg.append(math.degrees(math.atan2(ratio.imag, ratio.real)))

    if not gain_db:
        raise SpiceError("raw file ไม่มีข้อมูล AC analysis")

    peak_index = max(range(len(gain_db)), key=gain_db.__getitem__)
    threshold = gain_db[peak_index] - 3.0
    f_low: float | None = None
    f_high: float | None = None
    for i in range(peak_index):
        f_low = _half_power_frequency(
            frequency[i], gain_db[i], frequency[i + 1], gain_db[i + 1], threshold)
        if f_low is not None:
            break
    for i in range(peak_index, len(gain_db) - 1):
        f_high = _half_power_frequency(
            frequency[i], gain_db[i], frequency[i + 1], gain_db[i + 1], threshold)
        if f_high is not None:
            break
    return AcSeries(frequency, gain_db, phase_deg, f_low, f_high)


def parse_tran(raw: str) -> TranSeries:
    """Convert transient raw samples into time series and inversion flag."""
    _, variables, rows = _parse_raw(raw)
    time: list[float] = []
    vin: list[float] = []
    vout: list[float] = []
    for row in rows:
        time.append(float(_row_value(row, variables, "time")))
        vin.append(float(_row_value(row, variables, "v(base)")))
        vout.append(float(_row_value(row, variables, "v(out)")))

    if not time:
        raise SpiceError("raw file ไม่มีข้อมูล transient analysis")

    mean_in = sum(vin) / len(vin)
    mean_out = sum(vout) / len(vout)
    covariance = sum((x - mean_in) * (y - mean_out) for x, y in zip(vin, vout))
    if covariance == 0:
        samples = [(x, y) for x, y in zip(vin, vout) if x and y]
        inverted = bool(samples) and samples[0][0] * samples[0][1] < 0
    else:
        inverted = covariance < 0
    return TranSeries(time, vin, vout, inverted)


def _engine_version(log: str, raw: str) -> str:
    match = re.search(r"ngspice-[0-9A-Za-z.]+", log + "\n" + raw)
    return match.group(0) if match else "unknown"


def run_analysis(mode: str, inp: SpiceInput, cfg: SpiceConfig) -> SpiceResult:
    """Run one ngspice batch analysis and parse its real output."""
    if mode not in SPICE_MODES:
        raise SpiceError("Analysis mode ไม่รองรับสำหรับ SPICE")
    if not cfg.model_path:
        raise SpiceError(_MODEL_MISSING_MSG)
    # ngspice runs with cwd=tmp, so a relative model path must be made absolute
    # before it is checked, read for its .model name, and written into .include.
    model_path = str(Path(cfg.model_path).resolve())
    if not Path(model_path).is_file():
        raise SpiceError(_MODEL_MISSING_MSG)
    model_name = resolve_model_name(model_path, cfg.model_name)
    netlist = build_netlist(mode, inp, model_path, model_name)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        circuit = work / "circuit.cir"
        log_path = work / "run.log"
        raw_path = work / "run.raw"
        circuit.write_text(netlist, encoding="utf-8")

        try:
            completed = subprocess.run(
                [cfg.executable, "-b", "-o", str(log_path), "-r", str(raw_path),
                 str(circuit)],
                timeout=cfg.timeout,
                capture_output=True,
                text=True,
                cwd=tmp,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SpiceError("ngspice รันนานเกินกำหนด") from exc
        except OSError as exc:
            raise SpiceError("ไม่สามารถรัน ngspice ได้") from exc

        if completed.returncode != 0:
            detail = (completed.stderr or "").strip()
            raise SpiceError(
                f"รัน ngspice ไม่สำเร็จ (exit {completed.returncode}) {detail}".strip())

        try:
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise SpiceError("ngspice ไม่ได้สร้างไฟล์ผลลัพธ์ที่อ่านได้") from exc

    if not log_text.strip() or not raw_text.strip():
        raise SpiceError("ngspice ไม่ได้สร้างผลลัพธ์สำหรับ analysis นี้")

    try:
        op = parse_op(log_text, raw_text) if mode == ANALYSIS_DC else None
        ac = parse_ac(raw_text) if mode == ANALYSIS_AC else None
        tran = parse_tran(raw_text) if mode == ANALYSIS_TRAN else None
        engine_version = _engine_version(log_text, raw_text)
    except (OSError, ValueError, ArithmeticError) as exc:
        raise SpiceError(f"ไม่สามารถอ่านผลลัพธ์จาก ngspice ได้: {exc}") from exc
    return SpiceResult(
        analysis=mode,
        op=op,
        ac=ac,
        tran=tran,
        engine_version=engine_version,
        model_name=model_name,
        status="success",
        demo=cfg.demo,
    )


_SVG_WIDTH = 720
_SVG_HEIGHT = 360
_SVG_LEFT = 60
_SVG_RIGHT = 700
_MAX_POINTS = 2000


def _escape(text: object) -> str:
    return html.escape(str(text), quote=True)


def _svg_empty(title: str, message: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_SVG_WIDTH} '
        f'{_SVG_HEIGHT}" role="img" aria-label="{_escape(title)}">'
        f'<rect width="{_SVG_WIDTH}" height="{_SVG_HEIGHT}" fill="#ffffff"/>'
        f'<text x="{_SVG_LEFT}" y="40" fill="#334155">{_escape(message)}</text>'
        f"</svg>"
    )


def _sample_indices(count: int) -> list[int]:
    if count <= _MAX_POINTS:
        return list(range(count))
    step = math.ceil(count / _MAX_POINTS)
    indices = list(range(0, count, step))
    if indices[-1] != count - 1:
        indices.append(count - 1)
    if len(indices) > _MAX_POINTS:
        indices = indices[:_MAX_POINTS - 1] + [count - 1]
    return indices


def _project(value: float, low: float, high: float, start: float,
             end: float) -> float:
    if high == low:
        return (start + end) / 2
    ratio = (value - low) / (high - low)
    return start + ratio * (end - start)


def _points(pairs: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in pairs)


def _corner_text(value: float | None) -> str:
    if value is None:
        return "not determined in sweep range"
    return f"{value:.3g} Hz"


def render_bode_svg(ac: AcSeries, marker_hz: float | None = None) -> str:
    """Render gain and phase from parsed AC samples as a server-side SVG."""
    count = min(len(ac.frequency), len(ac.gain_db), len(ac.phase_deg))
    samples = [(ac.frequency[i], ac.gain_db[i], ac.phase_deg[i])
               for i in _sample_indices(count) if ac.frequency[i] > 0]
    if not samples:
        return _svg_empty("Bode plot", "no AC data")

    log_freq = [math.log10(freq) for freq, _, _ in samples]
    x_low, x_high = min(log_freq), max(log_freq)
    gains = [gain for _, gain, _ in samples]
    phases = [phase for _, _, phase in samples]
    gain_low, gain_high = min(gains) - 3.0, max(gains) + 3.0
    phase_low, phase_high = min(phases) - 10.0, max(phases) + 10.0

    gain_points = [
        (_project(math.log10(freq), x_low, x_high, _SVG_LEFT, _SVG_RIGHT),
         _project(gain, gain_low, gain_high, 160, 30))
        for freq, gain, _ in samples
    ]
    phase_points = [
        (_project(math.log10(freq), x_low, x_high, _SVG_LEFT, _SVG_RIGHT),
         _project(phase, phase_low, phase_high, 320, 195))
        for freq, _, phase in samples
    ]

    corner = (
        f"fL {_corner_text(ac.f_low)} | fH {_corner_text(ac.f_high)}"
    )
    marker = ""
    if marker_hz and marker_hz > 0 and math.isfinite(marker_hz):
        marker_log = math.log10(marker_hz)
        if x_low <= marker_log <= x_high:
            marker_x = _project(marker_log, x_low, x_high,
                                _SVG_LEFT, _SVG_RIGHT)
            marker = (
                f'<line x1="{marker_x:.2f}" y1="30" x2="{marker_x:.2f}" '
                f'y2="320" stroke="#0c8078" stroke-dasharray="4 3"/>'
                f'<text x="{marker_x + 6:.2f}" y="50" fill="#0c8078">'
                f'marker {marker_hz:.3g} Hz</text>'
            )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_SVG_WIDTH} '
        f'{_SVG_HEIGHT}" role="img" aria-label="Bode plot from ngspice AC data">'
        f'<rect width="{_SVG_WIDTH}" height="{_SVG_HEIGHT}" fill="#ffffff"/>'
        f'<line x1="{_SVG_LEFT}" y1="160" x2="{_SVG_RIGHT}" y2="160" '
        f'stroke="#cbd5e1"/>'
        f'<line x1="{_SVG_LEFT}" y1="320" x2="{_SVG_RIGHT}" y2="320" '
        f'stroke="#cbd5e1"/>'
        f'<text x="{_SVG_LEFT}" y="20" fill="#334155">Gain (dB)</text>'
        f'<text x="{_SVG_LEFT}" y="185" fill="#334155">Phase (°)</text>'
        f'<text x="{_SVG_LEFT}" y="350" fill="#334155">Frequency (Hz)</text>'
        f'<text x="{_SVG_RIGHT}" y="20" text-anchor="end" fill="#334155">'
        f'{_escape(corner)}</text>'
        f'<polyline points="{_points(gain_points)}" fill="none" stroke="#2563eb" '
        f'stroke-width="2"/>'
        f'<polyline points="{_points(phase_points)}" fill="none" stroke="#dc2626" '
        f'stroke-width="2"/>'
        f'{marker}'
        f"</svg>"
    )


def render_wave_svg(tran: TranSeries) -> str:
    """Render Vin/Vout versus time from parsed transient samples as an SVG."""
    count = min(len(tran.time), len(tran.vin), len(tran.vout))
    indices = _sample_indices(count)
    if not indices:
        return _svg_empty("Waveform", "no transient data")

    times_ms = [tran.time[i] * 1000.0 for i in indices]
    vin = [tran.vin[i] for i in indices]
    vout = [tran.vout[i] for i in indices]
    x_low, x_high = min(times_ms), max(times_ms)
    voltage = vin + vout
    y_low, y_high = min(voltage) - 0.05, max(voltage) + 0.05

    vin_points = [
        (_project(t, x_low, x_high, _SVG_LEFT, _SVG_RIGHT),
         _project(v, y_low, y_high, 320, 30))
        for t, v in zip(times_ms, vin)
    ]
    vout_points = [
        (_project(t, x_low, x_high, _SVG_LEFT, _SVG_RIGHT),
         _project(v, y_low, y_high, 320, 30))
        for t, v in zip(times_ms, vout)
    ]
    phase_note = "inverted (180°)" if tran.inverted else "not inverted"

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_SVG_WIDTH} '
        f'{_SVG_HEIGHT}" role="img" aria-label="Waveform from ngspice transient data">'
        f'<rect width="{_SVG_WIDTH}" height="{_SVG_HEIGHT}" fill="#ffffff"/>'
        f'<line x1="{_SVG_LEFT}" y1="320" x2="{_SVG_RIGHT}" y2="320" '
        f'stroke="#cbd5e1"/>'
        f'<text x="{_SVG_LEFT}" y="20" fill="#334155">Voltage (V)</text>'
        f'<text x="{_SVG_LEFT}" y="350" fill="#334155">Time (ms)</text>'
        f'<text x="{_SVG_RIGHT}" y="20" text-anchor="end" fill="#334155">'
        f'{_escape(phase_note)}</text>'
        f'<text x="{_SVG_LEFT + 20}" y="40" fill="#2563eb">Vin</text>'
        f'<text x="{_SVG_LEFT + 80}" y="40" fill="#dc2626">Vout</text>'
        f'<polyline points="{_points(vin_points)}" fill="none" stroke="#2563eb" '
        f'stroke-width="2"/>'
        f'<polyline points="{_points(vout_points)}" fill="none" stroke="#dc2626" '
        f'stroke-width="2"/>'
        f"</svg>"
    )

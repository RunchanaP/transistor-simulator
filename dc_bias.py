"""Engineering logic for a BJT common-emitter DC bias (voltage-divider bias).

This module knows nothing about Flask, HTTP, or HTML. It converts user text
into numbers, validates them, and solves the forward-active operating point.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Mapping

# Typical silicon VCE(sat); a model threshold, not a device-specific value.
VCE_SAT = 0.3

MAX_VCC = 1e4          # V
MAX_RESISTANCE = 1e12  # ohm
MAX_BETA = 1e5

SAMPLE_VALUES = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                 "re": "1k", "beta": "100", "vbe": "0.7"}

RESISTANCE_FIELDS = ("r1", "r2", "rc", "re")
NUMERIC_FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

_OHM_SUFFIX = re.compile(r"(ohms?|\u03a9)$", re.IGNORECASE)


class ValidationError(Exception):
    """Raised when one or more form fields cannot be used."""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(f"{len(errors)} invalid field(s)")


@dataclass(frozen=True)
class BiasInput:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


def parse_resistance(text: str) -> float:
    """Convert text such as ``100k`` into ohms.

    Accepts an optional trailing ohm symbol and the multipliers ``k`` (1e3),
    ``M``/``meg`` (1e6). A bare number is taken as ohms. A lowercase ``m`` is
    rejected because it cannot be distinguished from ``M``.
    """
    if text is None:
        raise ValueError("กรุณากรอกตัวเลข")

    raw = str(text).strip()
    if not raw:
        raise ValueError("กรุณากรอกตัวเลข")

    raw = _OHM_SUFFIX.sub("", raw).strip()

    multiplier = 1.0
    if raw.lower().endswith("meg"):
        multiplier = 1e6
        raw = raw[:-3]
    else:
        suffix = raw[-1:]
        if suffix == "k" or suffix == "K":
            multiplier = 1e3
            raw = raw[:-1]
        elif suffix == "M":
            multiplier = 1e6
            raw = raw[:-1]
        elif suffix == "m":
            raise ValueError("ไม่รองรับหน่วย m (กำกวมระหว่าง milli และ mega) ให้ใช้ k หรือ M")

    try:
        return float(raw) * multiplier
    except ValueError as exc:
        raise ValueError("กรุณากรอกตัวเลข") from exc


def _parse_plain(text: str) -> float:
    if text is None:
        raise ValueError("กรุณากรอกตัวเลข")
    raw = str(text).strip()
    if not raw:
        raise ValueError("กรุณากรอกตัวเลข")
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError("กรุณากรอกตัวเลข") from exc


def parse_inputs(raw: Mapping[str, str]) -> BiasInput:
    """Parse and validate a form mapping.

    Every failing field is reported at once through ``ValidationError.errors``
    so the page can show all messages in a single pass.
    """
    errors: dict[str, str] = {}
    parsed: dict[str, float] = {}

    for field in NUMERIC_FIELDS:
        try:
            if field in RESISTANCE_FIELDS:
                parsed[field] = parse_resistance(raw.get(field))
            else:
                parsed[field] = _parse_plain(raw.get(field))
        except ValueError:
            errors[field] = "กรุณากรอกตัวเลข"

    for field, value in parsed.items():
        if not math.isfinite(value):
            errors[field] = "ค่าตัวเลขไม่สมเหตุสมผล"
        elif field in RESISTANCE_FIELDS:
            if value <= 0:
                errors[field] = "ค่าความต้านทานต้องมากกว่า 0"
            elif value > MAX_RESISTANCE:
                errors[field] = "ค่าตัวเลขไม่สมเหตุสมผล"
        elif field == "vcc":
            if value <= 0:
                errors[field] = "VCC ต้องมากกว่า 0"
            elif value > MAX_VCC:
                errors[field] = "ค่าตัวเลขไม่สมเหตุสมผล"
        elif field == "beta":
            if value <= 0:
                errors[field] = "β ต้องมากกว่า 0"
            elif value > MAX_BETA:
                errors[field] = "ค่าตัวเลขไม่สมเหตุสมผล"
        elif field == "vbe":
            if value <= 0 or value >= 2:
                errors[field] = "VBE ต้องอยู่ระหว่าง 0 ถึง 2 V"

    if errors:
        raise ValidationError(errors)

    return BiasInput(**parsed)


@dataclass(frozen=True)
class BiasResult:
    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: list[str]
    notes: list[str]


def solve_dc_bias(inp: BiasInput) -> BiasResult:
    """Solve the forward-active DC operating point.

    Region is ``"active"``, ``"cutoff"``, or ``"saturation"``. ``warnings``
    explains when the forward-active model does not describe the circuit;
    ``notes`` carries softer advisories and can be non-empty while active.
    """
    vth = inp.vcc * inp.r2 / (inp.r1 + inp.r2)
    rth = inp.r1 * inp.r2 / (inp.r1 + inp.r2)

    if vth <= inp.vbe:
        ib = ic = ie = 0.0
        ve = 0.0
        vb = vth
        vc = inp.vcc
        vce = inp.vcc
        region = "cutoff"
        warnings = [
            f"VTH = {vth:.3f} V ไม่มากกว่า VBE = {inp.vbe:.3f} V "
            "ทรานซิสเตอร์อยู่ในช่วง Cutoff — แบบจำลอง Forward-Active ใช้ไม่ได้"
        ]
    else:
        ib = (vth - inp.vbe) / (rth + (inp.beta + 1) * inp.re)
        ic = inp.beta * ib
        ie = (inp.beta + 1) * ib
        ve = ie * inp.re
        vb = ve + inp.vbe
        vc = inp.vcc - ic * inp.rc
        vce = vc - ve
        if vce > VCE_SAT:
            region = "active"
            warnings = []
        else:
            region = "saturation"
            warnings = [
                f"VCE = {vce:.3f} V ต่ำกว่า VCE(sat) ≈ 0.2–0.3 V — "
                "ค่าที่แสดงมาจากสมการ Forward-Active จึงไม่ตรงกับวงจรจริง"
            ]

    notes: list[str] = []
    if not 0.5 <= inp.vbe <= 0.9:
        notes.append(
            f"VBE = {inp.vbe:.2f} V อยู่นอกช่วงปกติของ BJT ซิลิกอน (0.5–0.9 V)"
        )

    values = (vth, rth, ib, ic, ie, ve, vb, vc, vce)
    if not all(math.isfinite(v) for v in values):
        raise ValidationError({"__all__": "ค่าที่คำนวณได้ไม่สมเหตุสมผล"})

    return BiasResult(
        vth=vth, rth=rth, ib=ib, ic=ic, ie=ie,
        vb=vb, ve=ve, vc=vc, vce=vce,
        region=region, warnings=warnings, notes=notes,
    )


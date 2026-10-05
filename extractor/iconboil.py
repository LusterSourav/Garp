"""Boil-ready icon paths: tabler SVG -> M/L-only polylines for rough.js rc.path.

rough.js draws sketchy SVG `path` data, but tabler icons also use
circle/ellipse/line/polyline/polygon/rect plus curve + arc commands.
This normalizes every drawable shape into plain M/L polylines (sampled
curves/arcs, baked transforms) so the browser just calls rc.path(d).
Stdlib only, offline."""
import math
import os
import re
import xml.etree.ElementTree as ET

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "assets", "tabler-icons")


def _mul(a, b):  # 2x3 affine compose
    return (a[0] * b[0] + a[1] * b[3], a[0] * b[1] + a[1] * b[4],
            a[0] * b[2] + a[1] * b[5] + a[2],
            a[3] * b[0] + a[4] * b[3], a[3] * b[1] + a[4] * b[4],
            a[3] * b[2] + a[4] * b[5] + a[5])


def _parse_transform(s):
    m = (1, 0, 0, 0, 1, 0)
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", s or ""):
        nums = [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]
        if name == "translate":
            t = (1, 0, nums[0], 0, 1, nums[1] if len(nums) > 1 else 0)
        elif name == "scale":
            t = (nums[0], 0, 0, 0, nums[1] if len(nums) > 1 else nums[0], 0)
        elif name == "rotate":
            a = math.radians(nums[0])
            c, s_ = math.cos(a), math.sin(a)
            r = (c, -s_, 0, s_, c, 0)
            if len(nums) == 3:
                cx, cy = nums[1], nums[2]
                r = _mul((1, 0, cx, 0, 1, cy),
                         _mul(r, (1, 0, -cx, 0, 1, -cy)))
            t = r
        else:
            continue
        m = _mul(m, t)
    return m


def _pt(m, x, y):
    return (m[0] * x + m[1] * y + m[2], m[3] * x + m[4] * y + m[5])


def _cubic(p0, p1, p2, p3, n=10):
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0]
                    + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1]
                    + t**3 * p3[1]))
    return out


def _arc(p0, rx, ry, rot, large, sweep, p1):
    """SVG endpoint arc -> sampled points (spec F.6.5)."""
    if rx == 0 or ry == 0:
        return [p1]
    phi = math.radians(rot)
    c, s = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1p, y1p = c * dx + s * dy, -s * dx + c * dy
    lam = x1p**2 / rx**2 + y1p**2 / ry**2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2
    num = max(0, num) / (rx**2 * y1p**2 + ry**2 * x1p**2 + 1e-12)
    f = math.sqrt(num) * (-1 if large == sweep else 1)
    cxp, cyp = f * rx * y1p / ry, -f * ry * x1p / rx
    cx, cy = c * cxp - s * cyp + (p0[0] + p1[0]) / 2, \
        s * cxp + c * cyp + (p0[1] + p1[1]) / 2
    a1 = math.atan2((y1p - cyp) / ry, (x1p - cxp) / rx)
    a2 = math.atan2((-y1p - cyp) / ry, (-x1p - cxp) / rx)
    span = a2 - a1
    if sweep == 0 and span > 0:
        span -= 2 * math.pi
    if sweep == 1 and span < 0:
        span += 2 * math.pi
    n = max(6, int(abs(span) / (math.pi / 12)) + 1)
    out = []
    for i in range(1, n + 1):
        a = a1 + span * i / n
        out.append((cx + rx * c * math.cos(a) - ry * s * math.sin(a),
                    cy + rx * s * math.cos(a) + ry * c * math.sin(a)))
    return out


TOK = re.compile(r"[AaCcHhLlMmQqSsTtVvZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _parse_d(d):
    """Path data -> list of subpaths (point lists, absolute). Curves/arcs sampled."""
    toks = [t for t in TOK.findall(d or "") if t]
    subs, cur, start, i = [], (0.0, 0.0), (0.0, 0.0), 0
    cmd = None
    last_c2, last_q = None, None

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v

    while i < len(toks):
        i0 = i
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
        if cmd is None:
            break
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            x, y = num(), num()
            cur = (x + cur[0], y + cur[1]) if rel else (x, y)
            start = cur
            subs.append([cur])
            cmd = "l" if rel else "L"
            last_c2 = last_q = None
        elif c == "Z":
            if subs and subs[-1][-1] != start:
                subs[-1].append(start)
            cur = start
            last_c2 = last_q = None
        elif c in "LHTV":
            if c == "H":
                x = num()
                cur = (x + cur[0], cur[1]) if rel else (x, cur[1])
            elif c == "V":
                y = num()
                cur = (cur[0], y + cur[1]) if rel else (cur[0], y)
            else:
                x, y = num(), num()
                cur = (x + cur[0], y + cur[1]) if rel else (x, y)
            (subs.append([start, cur]) if not subs else subs[-1].append(cur))
            if not subs:
                subs.append([cur])
            last_c2 = last_q = None
        elif c in "CSQT":
            pts = []
            if c in "CQ":
                x1, y1 = num(), num()
                c1 = (x1 + cur[0], y1 + cur[1]) if rel else (x1, y1)
            if c == "S":
                c1 = (2 * cur[0] - last_c2[0], 2 * cur[1] - last_c2[1]) \
                    if last_c2 else cur
            if c == "T":
                c1 = (2 * cur[0] - last_q[0], 2 * cur[1] - last_q[1]) \
                    if last_q else cur
            if c in "CS":
                x2, y2, x, y = num(), num(), num(), num()
                c2 = (x2 + cur[0], y2 + cur[1]) if rel else (x2, y2)
                end = (x + cur[0], y + cur[1]) if rel else (x, y)
                pts = _cubic(cur, c1, c2, end)
                last_c2, last_q = c2, None
            else:
                x, y = num(), num()
                end = (x + cur[0], y + cur[1]) if rel else (x, y)
                mid = ((cur[0] + 2 * c1[0]) / 3, (cur[1] + 2 * c1[1]) / 3)
                mid2 = ((end[0] + 2 * c1[0]) / 3, (end[1] + 2 * c1[1]) / 3)
                pts = _cubic(cur, mid, mid2, end)
                last_q, last_c2 = end, None
            (subs.append([start] + pts) if not subs else subs[-1].extend(pts))
            if not subs:
                subs.append(pts)
            cur = end
        elif c == "A":
            rx, ry, rot, large, sweep, x, y = (num(), num(), num(), num(),
                                               num(), num(), num())
            end = (x + cur[0], y + cur[1]) if rel else (x, y)
            pts = _arc(cur, rx, ry, rot, large, sweep, end)
            (subs.append([start] + pts) if not subs else subs[-1].extend(pts))
            if not subs:
                subs.append(pts)
            cur = end
            last_c2 = last_q = None
        else:
            break
        if i == i0:
            break  # malformed data: no progress
    return [s for s in subs if len(s) > 1]


def _fmt(pts):
    return "M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in pts)


def _shapes(el, m, out):
    tag = el.tag.split("}")[-1]
    if el.get("stroke") == "none" and tag == "path":
        return  # clear-rect backdrop
    nm = _mul(m, _parse_transform(el.get("transform")))
    if tag == "path":
        for s in _parse_d(el.get("d")):
            out.append([_pt(nm, x, y) for x, y in s])
    elif tag == "line":
        a = (float(el.get("x1", 0)), float(el.get("y1", 0)))
        b = (float(el.get("x2", 0)), float(el.get("y2", 0)))
        out.append([_pt(nm, *a), _pt(nm, *b)])
    elif tag in ("polyline", "polygon"):
        nums = [float(x) for x in re.split(r"[,\s]+", (el.get("points") or "")
                                           .strip()) if x]
        pts = [_pt(nm, nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        if tag == "polygon" and pts:
            pts.append(pts[0])
        if len(pts) > 1:
            out.append(pts)
    elif tag == "rect":
        x, y = float(el.get("x", 0)), float(el.get("y", 0))
        w, h = float(el.get("width", 0)), float(el.get("height", 0))
        rx = min(float(el.get("rx", 0) or 0), w / 2, h / 2)
        if rx <= 0:
            out.append([_pt(nm, *p) for p in
                        [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]])
        else:
            pts = [(x + rx, y)]
            for cx, cy, a0 in ((x + w - rx, y + rx, -90), (x + w - rx,
                               y + h - rx, 0), (x + rx, y + h - rx, 90),
                               (x + rx, y + rx, 180)):
                pts += [(cx + rx * math.cos(math.radians(a0 + i * 15)),
                         cy + rx * math.sin(math.radians(a0 + i * 15)))
                        for i in range(7)]
            pts.append((x + rx, y))
            out.append([_pt(nm, *p) for p in pts])
    elif tag in ("circle", "ellipse"):
        cx, cy = float(el.get("cx", 0)), float(el.get("cy", 0))
        rx = float(el.get("r", el.get("rx", 0)) or 0)
        ry = float(el.get("r", el.get("ry", 0)) or rx)
        pts = [((cx + rx * math.cos(i * math.pi / 8)),
                (cy + ry * math.sin(i * math.pi / 8))) for i in range(17)]
        out.append([_pt(nm, *p) for p in pts])
    for child in el:
        _shapes(child, nm, out)


def icon_paths(name):
    """tabler icon name -> {"paths": [M/L d, ...], "color": stroke}."""
    path = os.path.join(ICON_DIR, f"tabler-icon-{name}.svg")
    root = ET.parse(path).getroot()
    out = []
    _shapes(root, (1, 0, 0, 0, 1, 0), out)
    return {"paths": [_fmt(s) for s in out],
            "color": root.get("stroke", "currentColor")}


def all_icons():
    return {fn[len("tabler-icon-"):-len(".svg")]: icon_paths(
        fn[len("tabler-icon-"):-len(".svg")])
        for fn in sorted(os.listdir(ICON_DIR)) if fn.endswith(".svg")}

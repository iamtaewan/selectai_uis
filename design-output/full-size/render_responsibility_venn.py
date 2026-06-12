from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH, HEIGHT = 3840, 2160
OUT_PATH = Path("design-output/full-size/responsibility-venn.png")
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def rgba(hex_value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = hex_value.strip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    indices = {
        "light": 8,
        "regular": 0,
        "medium": 2,
        "semibold": 4,
        "bold": 6,
        "heavy": 6,
    }
    return ImageFont.truetype(FONT_PATH, size=size, index=indices.get(weight, 0))


SETS = {
    "cloud": {
        "label": "Cloud / Infra",
        "sub": "OCI · Network · HPC · GPU · OKE · DevOps",
        "color": "#2672C9",
        "fill": "#6DA8F2",
        "center": (1325, 960),
        "radius": 640,
        "label_pos": (720, 510),
    },
    "database": {
        "label": "Database / ADB",
        "sub": "Oracle Database · ADB · APEX · Vector Search",
        "color": "#7D55C7",
        "fill": "#A78BFA",
        "center": (1920, 1045),
        "radius": 700,
        "label_pos": (1720, 430),
    },
    "ai": {
        "label": "AI / ML",
        "sub": "Generative AI · AI Services · Data Science · AQUA",
        "color": "#129B71",
        "fill": "#5BD7A8",
        "center": (2515, 960),
        "radius": 640,
        "label_pos": (2730, 510),
    },
    "integration": {
        "label": "Integration",
        "sub": "OGG · Streaming · Catalog · Data Flow",
        "color": "#D46A26",
        "fill": "#FFA35C",
        "center": (1635, 1375),
        "radius": 560,
        "label_pos": (1110, 1710),
    },
    "analytics": {
        "label": "Analytics / App",
        "sub": "OAC · APEX · Ontology · OML · AIDP",
        "color": "#B89112",
        "fill": "#FFD85C",
        "center": (2205, 1375),
        "radius": 560,
        "label_pos": (2360, 1710),
    },
}


PEOPLE = [
    {
        "name": "이창근",
        "headline": "OCI · Network · HPC · 기타 영역",
        "color": "cloud",
        "pos": (720, 760),
        "size": (620, 170),
    },
    {
        "name": "장진호",
        "headline": "OCI · Network · HPC · GPU",
        "color": "cloud",
        "pos": (800, 1015),
        "size": (560, 165),
    },
    {
        "name": "이동희",
        "headline": "OKE · DevOps Services · ADB(Vector Search)\nPrivate AI Agent Factory · Oracle Private AI Services Container",
        "color": "ai",
        "pos": (1515, 705),
        "size": (900, 205),
    },
    {
        "name": "최용석",
        "headline": "OGG · Streaming · Catalog(OCI, ADB) · ADB",
        "color": "integration",
        "pos": (1280, 1238),
        "size": (760, 170),
    },
    {
        "name": "고정민",
        "headline": "ADB(Select AI, Select AI Agent, ORDA, Data Deep Security)\nGenerative AI · Data Flow · Private Agent Factory · AI Services · Data Science AQUA",
        "color": "ai",
        "pos": (1810, 1000),
        "size": (1020, 220),
    },
    {
        "name": "김민지",
        "headline": "ADB(Ontology, OML) · AIDP · OAC",
        "color": "analytics",
        "pos": (2415, 1300),
        "size": (640, 170),
    },
    {
        "name": "김은혜",
        "headline": "Oracle Database · ADB(APEX) · OGG · Data Science",
        "color": "database",
        "pos": (1725, 1500),
        "size": (820, 170),
    },
]


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_line(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if text_size(draw, text, fnt)[0] <= max_width:
        return [text]
    words = text.split(" ")
    if len(words) == 1:
        return [text]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and text_size(draw, candidate, fnt)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    max_width: int,
    line_gap: int = 8,
    align: str = "left",
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int, int] | None = None,
) -> int:
    x, y = xy
    lines: list[str] = []
    for raw in text.splitlines():
        lines.extend(wrap_line(draw, raw, fnt, max_width))
    line_h = fnt.size + line_gap
    for index, line in enumerate(lines):
        line_w = text_size(draw, line, fnt)[0]
        if align == "center":
            tx = x + (max_width - line_w) / 2
        elif align == "right":
            tx = x + max_width - line_w
        else:
            tx = x
        draw.text(
            (tx, y + index * line_h),
            line,
            font=fnt,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
    return len(lines) * line_h - line_gap


def gradient_background(image: Image.Image) -> None:
    top = rgba("#F8FAFC")
    bottom = rgba("#EEF6F8")
    pix = image.load()
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        row = tuple(round(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(4))
        for x in range(WIDTH):
            pix[x, y] = row


def soft_circle(image: Image.Image, center: tuple[int, int], radius: int, fill: str, stroke: str) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    cx, cy = center
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(box, fill=rgba(fill, 88), outline=rgba(stroke, 210), width=7)
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse(box, outline=rgba(stroke, 42), width=34)
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    image.alpha_composite(glow)
    image.alpha_composite(overlay)


def set_label(draw: ImageDraw.ImageDraw, item: dict) -> None:
    x, y = item["label_pos"]
    label_f = font(42, "bold")
    sub_f = font(26, "medium")
    color = rgba(item["color"])
    fill = rgba("#FFFFFF", 218)
    label_w = max(text_size(draw, item["label"], label_f)[0], text_size(draw, item["sub"], sub_f)[0]) + 70
    label_h = 116
    draw.rounded_rectangle((x, y, x + label_w, y + label_h), radius=34, fill=fill, outline=rgba(item["color"], 175), width=3)
    draw.ellipse((x + 26, y + 32, x + 52, y + 58), fill=color)
    draw.text((x + 68, y + 20), item["label"], font=label_f, fill=rgba("#111827"))
    draw.text((x + 68, y + 73), item["sub"], font=sub_f, fill=rgba("#526071"))


def person_bubble(image: Image.Image, draw: ImageDraw.ImageDraw, person: dict) -> None:
    x, y = person["pos"]
    w, _ = person["size"]
    cfg = SETS[person["color"]]

    halo = Image.new("RGBA", image.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse((x + 15, y + 18, x + 99, y + 102), fill=rgba("#FFFFFF", 150))
    halo = halo.filter(ImageFilter.GaussianBlur(13))
    image.alpha_composite(halo)

    draw.ellipse((x + 18, y + 20, x + 96, y + 98), fill=rgba(cfg["fill"], 176), outline=rgba(cfg["color"]), width=4)
    initial = person["name"][0]
    initial_f = font(33, "bold")
    iw, ih = text_size(draw, initial, initial_f)
    draw.text(
        (x + 57 - iw / 2, y + 60 - ih / 2 - 2),
        initial,
        font=initial_f,
        fill=rgba(cfg["color"]),
        stroke_width=2,
        stroke_fill=rgba("#FFFFFF", 220),
    )
    draw.rounded_rectangle((x + 116, y + 36, x + 124, y + 118), radius=4, fill=rgba(cfg["color"]))
    draw.text(
        (x + 142, y + 20),
        person["name"],
        font=font(43, "bold"),
        fill=rgba("#111827"),
        stroke_width=5,
        stroke_fill=rgba("#FFFFFF", 235),
    )
    draw_wrapped(
        draw,
        (x + 142, y + 82),
        person["headline"],
        font(28, "medium"),
        rgba("#303A49"),
        w - 150,
        line_gap=5,
        stroke_width=4,
        stroke_fill=rgba("#FFFFFF", 230),
    )


def draw_intersection_marks(draw: ImageDraw.ImageDraw) -> None:
    marks = [
        ("Cloud + Database + AI", (1660, 640), "#334155"),
        ("Database + Integration", (1320, 1455), "#9A3412"),
        ("Database + AI + Analytics", (2340, 1495), "#166534"),
    ]
    for text, (x, y), color in marks:
        fnt = font(24, "semibold")
        tw, th = text_size(draw, text, fnt)
        draw.rounded_rectangle((x, y, x + tw + 36, y + th + 22), radius=22, fill=rgba("#FFFFFF", 180), outline=rgba(color, 110), width=2)
        draw.text((x + 18, y + 10), text, font=fnt, fill=rgba(color))


def main() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), rgba("#F8FAFC"))
    gradient_background(image)
    draw = ImageDraw.Draw(image)

    grid = rgba("#D8E0EA", 90)
    for x in range(0, WIDTH + 1, 120):
        draw.line((x, 0, x, HEIGHT), fill=grid, width=1)
    for y in range(0, HEIGHT + 1, 120):
        draw.line((0, y, WIDTH, y), fill=grid, width=1)

    draw.text((170, 98), "담당영역 벤다이어그램", font=font(82, "bold"), fill=rgba("#111827"))
    draw.text(
        (174, 206),
        "담당자를 주요 기술 축의 교집합 위치에 배치",
        font=font(34, "semibold"),
        fill=rgba("#5C6677"),
    )
    size_text = "Full Size 3840 × 2160"
    size_f = font(32, "bold")
    size_w = text_size(draw, size_text, size_f)[0]
    draw.text((3650 - size_w, 134), size_text, font=size_f, fill=rgba("#C74634"))

    for key in ["cloud", "database", "ai", "integration", "analytics"]:
        item = SETS[key]
        soft_circle(image, item["center"], item["radius"], item["fill"], item["color"])

    draw = ImageDraw.Draw(image)
    for key in ["cloud", "database", "ai", "integration", "analytics"]:
        set_label(draw, SETS[key])

    draw_intersection_marks(draw)

    for person in PEOPLE:
        person_bubble(image, draw, person)

    footer_y = 2000
    draw.rounded_rectangle((170, footer_y, 3670, footer_y + 86), radius=30, fill=rgba("#111827", 240))
    draw.text((238, footer_y + 26), "배치 기준", font=font(28, "bold"), fill=rgba("#FFFFFF"))
    draw.text(
        (400, footer_y + 26),
        "단일 원은 주 담당 축, 겹친 영역은 복합 담당 축을 의미합니다.",
        font=font(28, "medium"),
        fill=rgba("#E7ECF4"),
    )
    footer = "OCI · ADB · AI/ML · Integration · Analytics"
    footer_f = font(25, "medium")
    footer_w = text_size(draw, footer, footer_f)[0]
    draw.text((3610 - footer_w, footer_y + 29), footer, font=footer_f, fill=rgba("#AEB7C5"))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT_PATH, "PNG", optimize=True)
    print(OUT_PATH.resolve())


if __name__ == "__main__":
    main()

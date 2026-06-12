from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH, HEIGHT = 3840, 2160
OUT_PATH = Path("design-output/full-size/responsibility-map.png")
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def rgb(hex_value: str, alpha: int = 255) -> tuple[int, int, int, int]:
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


CATEGORIES = {
    "cloud": {
        "title": "Cloud / Infra",
        "fill": rgb("#E8F2FF"),
        "stroke": rgb("#2672C9"),
        "dark": rgb("#174E8C"),
    },
    "database": {
        "title": "Database / ADB",
        "fill": rgb("#F4ECFF"),
        "stroke": rgb("#7D55C7"),
        "dark": rgb("#563399"),
    },
    "ai": {
        "title": "AI / ML",
        "fill": rgb("#E8FAF2"),
        "stroke": rgb("#129B71"),
        "dark": rgb("#087253"),
    },
    "integration": {
        "title": "Integration",
        "fill": rgb("#FFF0E6"),
        "stroke": rgb("#D46A26"),
        "dark": rgb("#A24510"),
    },
    "analytics": {
        "title": "Analytics / App",
        "fill": rgb("#FFF7D9"),
        "stroke": rgb("#B89112"),
        "dark": rgb("#7C6200"),
    },
    "other": {
        "title": "기타",
        "fill": rgb("#ECEFF3"),
        "stroke": rgb("#6B7280"),
        "dark": rgb("#374151"),
    },
}


PEOPLE = [
    {
        "name": "이창근",
        "role": "Cloud Infrastructure 중심",
        "accent": "cloud",
        "chips": [
            ("OCI", "cloud"),
            ("Network", "cloud"),
            ("HPC", "cloud"),
            ("기타 영역", "other"),
        ],
    },
    {
        "name": "장진호",
        "role": "Infra / GPU / HPC",
        "accent": "cloud",
        "chips": [
            ("OCI", "cloud"),
            ("Network", "cloud"),
            ("HPC", "cloud"),
            ("GPU", "cloud"),
        ],
    },
    {
        "name": "최용석",
        "role": "Data Integration / ADB",
        "accent": "integration",
        "chips": [
            ("OGG", "integration"),
            ("Streaming", "integration"),
            ("Catalog (OCI, ADB)", "database"),
            ("ADB", "database"),
        ],
    },
    {
        "name": "이동희",
        "role": "OKE / DevOps / Private AI",
        "accent": "ai",
        "chips": [
            ("OKE", "cloud"),
            ("DevOps Services", "cloud"),
            ("ADB (Vector Search)", "database"),
            ("Private AI Agent Factory", "ai"),
            ("Oracle Private AI Services Container", "cloud"),
        ],
    },
    {
        "name": "고정민",
        "role": "Select AI / GenAI / Data Science",
        "accent": "ai",
        "chips": [
            ("ADB (Select AI, Select AI Agent, ORDA, Data Deep Security)", "database"),
            ("Generative AI", "ai"),
            ("Data Flow", "integration"),
            ("Private Agent Factory", "ai"),
            ("AI Services", "ai"),
            ("Data Science AQUA", "ai"),
        ],
    },
    {
        "name": "김민지",
        "role": "ADB Ontology / Analytics",
        "accent": "analytics",
        "chips": [
            ("ADB (Ontology, OML)", "database"),
            ("AIDP", "ai"),
            ("OAC", "analytics"),
        ],
    },
    {
        "name": "김은혜",
        "role": "Oracle DB / APEX / OGG",
        "accent": "database",
        "chips": [
            ("Oracle Database", "database"),
            ("ADB (APEX)", "analytics"),
            ("OGG", "integration"),
            ("Data Science", "ai"),
        ],
    },
]


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 3) -> list[str]:
    if text_size(draw, text, fnt)[0] <= max_width:
        return [text]

    parts = text.split(" ")
    if len(parts) == 1:
        line = ""
        lines: list[str] = []
        for char in text:
            candidate = f"{line}{char}"
            if line and text_size(draw, candidate, fnt)[0] > max_width:
                lines.append(line)
                line = char
            else:
                line = candidate
        if line:
            lines.append(line)
        return lines[:max_lines]

    lines = []
    current = ""
    for part in parts:
        candidate = part if not current else f"{current} {part}"
        if current and text_size(draw, candidate, fnt)[0] > max_width:
            lines.append(current)
            current = part
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(",") + "..."
    return lines


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    max_width: int | None = None,
    align: str = "left",
    line_gap: int = 8,
) -> int:
    x, y = xy
    lines = [text] if max_width is None else wrap_text(draw, text, fnt, max_width)
    line_heights = [text_size(draw, line, fnt)[1] for line in lines]
    line_height = max(line_heights) if line_heights else fnt.size
    for index, line in enumerate(lines):
        line_width = text_size(draw, line, fnt)[0]
        if align == "right":
            line_x = x + (max_width or 0) - line_width
        elif align == "center":
            line_x = x + ((max_width or line_width) - line_width) / 2
        else:
            line_x = x
        draw.text((line_x, y + index * (line_height + line_gap)), line, font=fnt, fill=fill)
    return len(lines) * line_height + max(0, len(lines) - 1) * line_gap


def rounded_shadow(base: Image.Image, box: tuple[int, int, int, int], radius: int, blur: int = 28, offset_y: int = 12) -> None:
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    x0, y0, x1, y1 = box
    sd.rounded_rectangle((x0, y0 + offset_y, x1, y1 + offset_y), radius=radius, fill=(17, 24, 39, 36))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(shadow)


def draw_chip(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    category: str,
    max_width: int,
    compact: bool,
) -> tuple[int, int]:
    cfg = CATEGORIES[category]
    fnt = font(29 if compact else 32, "medium")
    pad_x = 24 if compact else 28
    pad_y = 14 if compact else 16
    line_gap = 5
    max_text_width = max_width - pad_x * 2
    lines = wrap_text(draw, text, fnt, max_text_width)
    line_height = max(text_size(draw, line, fnt)[1] for line in lines) + line_gap
    text_width = min(max(text_size(draw, line, fnt)[0] for line in lines), max_text_width)
    chip_w = min(max_width, int(text_width + pad_x * 2))
    chip_h = int(len(lines) * line_height + pad_y * 2 - line_gap)

    draw.rounded_rectangle((x, y, x + chip_w, y + chip_h), radius=22, fill=cfg["fill"], outline=fade(cfg["stroke"], 86), width=2)
    draw.rounded_rectangle((x + 2, y + 2, x + 12, y + chip_h - 2), radius=5, fill=cfg["stroke"])
    text_y = y + pad_y - 1
    for line in lines:
        draw.text((x + pad_x, text_y), line, font=fnt, fill=cfg["dark"])
        text_y += line_height
    return chip_w, chip_h


def chip_estimate(draw: ImageDraw.ImageDraw, text: str, max_width: int, compact: bool) -> tuple[int, int]:
    fnt = font(29 if compact else 32, "medium")
    pad_x = 24 if compact else 28
    pad_y = 14 if compact else 16
    max_text_width = max_width - pad_x * 2
    lines = wrap_text(draw, text, fnt, max_text_width)
    widths = [text_size(draw, line, fnt)[0] for line in lines]
    line_height = max(text_size(draw, line, fnt)[1] for line in lines) + 5
    return min(max_width, max(widths) + pad_x * 2), len(lines) * line_height + pad_y * 2 - 5


def draw_chip_cloud(
    draw: ImageDraw.ImageDraw,
    chips: Iterable[tuple[str, str]],
    x: int,
    y: int,
    width: int,
    compact: bool,
) -> int:
    gap_x = 16 if compact else 18
    gap_y = 16 if compact else 18
    cursor_x = x
    cursor_y = y
    row_h = 0
    for text, category in chips:
        est_w, est_h = chip_estimate(draw, text, width, compact)
        if cursor_x > x and cursor_x + est_w > x + width:
            cursor_x = x
            cursor_y += row_h + gap_y
            row_h = 0
        chip_w, chip_h = draw_chip(draw, cursor_x, cursor_y, text, category, min(est_w, width), compact)
        cursor_x += chip_w + gap_x
        row_h = max(row_h, chip_h)
    return cursor_y + row_h - y


def fade(color: tuple[int, int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color[:3] + (alpha,)


def draw_person_card(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    person: dict,
    x: int,
    y: int,
    width: int,
    height: int,
    compact: bool,
) -> None:
    accent = CATEGORIES[person["accent"]]
    box = (x, y, x + width, y + height)
    rounded_shadow(image, box, 34)
    draw.rounded_rectangle(box, radius=34, fill=rgb("#FFFFFF"), outline=rgb("#DDE4EE"), width=2)
    draw.rounded_rectangle((x, y, x + 18, y + height), radius=9, fill=accent["stroke"])

    avatar = 82 if compact else 92
    ax, ay = x + 48, y + 46
    draw.ellipse((ax, ay, ax + avatar, ay + avatar), fill=accent["fill"], outline=fade(accent["stroke"], 145), width=3)
    initial_fnt = font(42 if compact else 48, "bold")
    initial = person["name"][0]
    tw, th = text_size(draw, initial, initial_fnt)
    draw.text((ax + (avatar - tw) / 2, ay + (avatar - th) / 2 - 3), initial, font=initial_fnt, fill=accent["dark"])

    name_x = ax + avatar + 28
    draw.text((name_x, y + 42), person["name"], font=font(42 if compact else 48, "bold"), fill=rgb("#101827"))
    draw.text((name_x, y + 106), person["role"], font=font(25 if compact else 28, "medium"), fill=rgb("#667085"))

    chip_top = y + (182 if compact else 190)
    used_h = draw_chip_cloud(draw, person["chips"], x + 48, chip_top, width - 96, compact)
    summary_y = min(y + height - 92, chip_top + used_h + 32)
    draw.text((x + 48, summary_y), f"{len(person['chips'])}개 담당영역", font=font(26, "semibold"), fill=rgb("#8A94A6"))


def draw_gradient_background(image: Image.Image) -> None:
    pix = image.load()
    top = rgb("#F7F9FC")
    bottom = rgb("#EEF4F8")
    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        color = tuple(round(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(4))
        for x in range(WIDTH):
            pix[x, y] = color


def main() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), rgb("#F7F9FC"))
    draw_gradient_background(image)
    draw = ImageDraw.Draw(image)

    grid = fade(rgb("#D8E0EA"), 118)
    for x in range(0, WIDTH + 1, 120):
        draw.line((x, 0, x, HEIGHT), fill=grid, width=1)
    for y in range(0, HEIGHT + 1, 120):
        draw.line((0, y, WIDTH, y), fill=grid, width=1)

    draw.rounded_rectangle((160, 108, 3680, 368), radius=42, fill=rgb("#FFFFFF", 184), outline=rgb("#DCE5EF"), width=2)
    draw.text((220, 141), "담당영역 맵", font=font(88, "bold"), fill=rgb("#111827"))
    draw.text((224, 260), "OCI · Database · AI/ML · Data Integration · Analytics", font=font(34, "semibold"), fill=rgb("#5C6677"))

    legend_x = 1788
    legend_y = 168
    for key in ["cloud", "database", "ai", "integration", "analytics", "other"]:
        cfg = CATEGORIES[key]
        legend_font = font(27, "semibold")
        label_w = text_size(draw, cfg["title"], legend_font)[0]
        legend_w = max(230, label_w + 92)
        draw.rounded_rectangle((legend_x, legend_y, legend_x + legend_w, legend_y + 70), radius=24, fill=cfg["fill"], outline=fade(cfg["stroke"], 86), width=2)
        draw.ellipse((legend_x + 24, legend_y + 21, legend_x + 52, legend_y + 49), fill=cfg["stroke"])
        draw.text((legend_x + 66, legend_y + 18), cfg["title"], font=legend_font, fill=cfg["dark"])
        legend_x += legend_w + 22

    full_text = "Full Size 3840 × 2160"
    full_font = font(32, "bold")
    full_w = text_size(draw, full_text, full_font)[0]
    draw.text((3570 - full_w, 268), full_text, font=full_font, fill=rgb("#C74634"))

    margin = 160
    gap = 42
    top_y = 430
    top_h = 630
    top_w = math.floor((WIDTH - margin * 2 - gap * 3) / 4)
    for index, person in enumerate(PEOPLE[:4]):
        draw_person_card(image, draw, person, margin + index * (top_w + gap), top_y, top_w, top_h, True)

    bottom_y = 1116
    bottom_h = 790
    bottom_w = math.floor((WIDTH - margin * 2 - gap * 2) / 3)
    for index, person in enumerate(PEOPLE[4:]):
        draw_person_card(image, draw, person, margin + index * (bottom_w + gap), bottom_y, bottom_w, bottom_h, False)

    draw.rounded_rectangle((160, 1978, 3680, 2076), radius=32, fill=rgb("#111827"))
    draw.text((224, 2006), "공통 축", font=font(30, "bold"), fill=rgb("#FFFFFF"))
    draw.text((404, 2006), "OCI · ADB · AI/ML · Data Integration 영역이 교차되는 팀 담당 범위를 한 장으로 요약", font=font(30, "medium"), fill=rgb("#E7ECF4"))
    footer = "Generated responsibility overview"
    footer_font = font(26, "medium")
    footer_w = text_size(draw, footer, footer_font)[0]
    draw.text((3540 - footer_w, 2010), footer, font=footer_font, fill=rgb("#AEB7C5"))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(OUT_PATH, "PNG", optimize=True)
    print(OUT_PATH.resolve())


if __name__ == "__main__":
    main()

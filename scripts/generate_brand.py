"""Generate HACS/Home Assistant brand images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "aeg_fse73768p" / "brand"
RED = (200, 16, 46, 255)
WHITE = (255, 255, 255, 255)
DARK = (18, 19, 22, 255)


def _rounded_square(size: int, fill: tuple[int, int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = int(size * 0.22)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=fill)
    return image


def _dishwasher(draw: ImageDraw.ImageDraw, size: int, color: tuple[int, int, int, int]) -> None:
    x0, y0 = int(size * 0.27), int(size * 0.18)
    x1, y1 = int(size * 0.73), int(size * 0.82)
    width = max(2, size // 42)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=size // 18, outline=color, width=width)
    # Control strip
    draw.rounded_rectangle(
        (x0 + size * 0.04, y0 + size * 0.05, x1 - size * 0.04, y0 + size * 0.16),
        radius=size // 40,
        fill=color,
    )
    # Door handle
    hy = (y0 + y1) / 2
    draw.rounded_rectangle(
        (size * 0.46, hy - size * 0.015, size * 0.54, hy + size * 0.015),
        radius=size // 50,
        fill=color,
    )
    # TimeBeam
    draw.ellipse(
        (size * 0.34, size * 0.84, size * 0.66, size * 0.92),
        fill=color,
    )


def write_icon(path: Path, background: tuple[int, int, int, int], glyph: tuple[int, int, int, int], size: int) -> None:
    image = _rounded_square(size, background)
    draw = ImageDraw.Draw(image)
    _dishwasher(draw, size, glyph)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def write_logo(path: Path, dark: bool) -> None:
    width, height = 1024, 256
    bg = DARK if dark else RED
    fg = WHITE
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=48, fill=bg)
    # Glyph
    glyph = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glyph)
    _dishwasher(gdraw, 256, fg)
    image.alpha_composite(glyph, (24, 0))
    draw.text((300, 78), "FSE73768P", fill=fg)
    draw.text((300, 148), "7000 ComfortLift", fill=fg)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def main() -> None:
    write_icon(BRAND / "icon.png", RED, WHITE, 512)
    write_icon(BRAND / "icon@2x.png", RED, WHITE, 1024)
    write_icon(BRAND / "dark_icon.png", DARK, RED, 512)
    write_icon(BRAND / "dark_icon@2x.png", DARK, RED, 1024)
    write_logo(BRAND / "logo.png", dark=False)
    write_logo(BRAND / "dark_logo.png", dark=True)


if __name__ == "__main__":
    main()

"""Render the "Stack in motion" (2e) app icon.

Ports the SVG from `YouTube app design system/YouT Icon.dc.html` to
Pillow so we can produce a real multi-resolution .ico. The designer
sheds the topmost plate at sizes 40px and below (icon becomes two
plates + arrow), so we honour that.

Run with the venv's Python:
    venv/Scripts/python.exe create_icon.py
"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit("Pillow not installed. Run: pip install pillow") from exc


# ----- 2e "Stack in motion" -----------------------------------------
# All coordinates are in the SVG's 256x256 design canvas. We render at
# the full canvas size then scale to each target when packing the .ico.
#
# 3-plate variant (for sizes >= 48px):
#   Top dark plate:  x=52, y=16, w=152, h=86,  rx=20, fill=#4A2320
#   Middle plate:    x=34, y=52, w=188, h=104, rx=24, fill=#8E2E27
#   Bottom accent:   x=16, y=96, w=224, h=144, rx=34, fill=#F0483E
#   Arrow bar:       x=114, y=126, w=28, h=46, rx=8, fill=#fff
#   Arrow head path: M92 166h72l-32 40a6 6 0 0 1-8 0z
#
# 2-plate variant (for sizes <= 32px) drops the top dark plate and
# widens the arrow slightly for legibility.

C_DARK  = (0x4A, 0x23, 0x20, 0xFF)
C_MID   = (0x8E, 0x2E, 0x27, 0xFF)
C_ACC   = (0xF0, 0x48, 0x3E, 0xFF)
C_WHITE = (0xFF, 0xFF, 0xFF, 0xFF)


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, radius, fill):
    """Pillow's rounded_rectangle takes (x0, y0, x1, y1)."""
    x, y, w, h = xy
    draw.rounded_rectangle((x, y, x + w, y + h), radius=radius, fill=fill)


def _arrow_head(draw: ImageDraw.ImageDraw, x1: int, x2: int, y_top: int, tip_y: int, fill):
    """Downward-pointing triangle from a horizontal top edge (x1..x2, y_top)
    to a single tip at midpoint (mid, tip_y). Approximates the SVG's tiny
    rounded corner at the tip with a plain triangle — invisible at raster
    sizes we care about."""
    mid = (x1 + x2) // 2
    draw.polygon([(x1, y_top), (x2, y_top), (mid, tip_y)], fill=fill)


def _draw_three_plate(canvas: int = 256) -> Image.Image:
    """Full 3-plate design at any square canvas."""
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = canvas / 256  # uniform scale from the design canvas

    def R(x, y, w, h, r):
        return (round(x * s), round(y * s), round(w * s), round(h * s)), round(r * s)

    _rounded_rect(d, *R(52, 16, 152, 86, 20), fill=C_DARK)
    _rounded_rect(d, *R(34, 52, 188, 104, 24), fill=C_MID)
    _rounded_rect(d, *R(16, 96, 224, 144, 34), fill=C_ACC)

    # Arrow bar
    _rounded_rect(d, *R(114, 126, 28, 46, 8), fill=C_WHITE)
    # Arrow head — bar from x=92..164 at y=166, tip at y=206
    _arrow_head(
        d,
        round(92 * s), round(164 * s),
        round(166 * s), round(206 * s),
        fill=C_WHITE,
    )
    return img


def _draw_two_plate(canvas: int) -> Image.Image:
    """Simplified 2-plate variant for small (<=32px) sizes. Uses the
    designer's own 24px geometry so the arrow is chunkier and legible."""
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = canvas / 256

    def R(x, y, w, h, r):
        return (round(x * s), round(y * s), round(w * s), round(h * s)), round(r * s)

    _rounded_rect(d, *R(30, 26, 196, 80, 22), fill=C_MID)
    _rounded_rect(d, *R(12, 78, 232, 162, 38), fill=C_ACC)

    _rounded_rect(d, *R(110, 112, 36, 52, 8), fill=C_WHITE)
    _arrow_head(
        d,
        round(84 * s), round(172 * s),
        round(158 * s), round(206 * s),
        fill=C_WHITE,
    )
    return img


def render_icon(size: int) -> Image.Image:
    """Sizes <= 32 use the 2-plate variant; larger use full 3-plate.
    Small sizes render at 4x then downscale for smoother edges."""
    variant = _draw_two_plate if size <= 32 else _draw_three_plate
    if size < 64:
        big = variant(size * 4)
        return big.resize((size, size), Image.LANCZOS)
    return variant(size)


def main():
    out = Path(__file__).parent

    # Standard Windows .ico sizes. Explorer uses 16/32/48; taskbar uses
    # 32/48; the shell scales to 128/256 for large-icon views.
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [render_icon(s) for s in sizes]

    ico_path = out / "icon.ico"
    # Pillow packs all provided images into a single multi-resolution .ico
    # when we pass `sizes=` and the base image is the largest.
    images[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"[OK] {ico_path.name} ({ico_path.stat().st_size // 1024} KB, {len(sizes)} sizes)")

    # Convenience PNG for docs / marketing.
    png_path = out / "icon.png"
    render_icon(512).save(png_path, "PNG")
    print(f"[OK] {png_path.name}")

    # macOS ICNS — optional; only writes if Pillow was built with the
    # pillow-heif dependency.
    try:
        icns_path = out / "icon.icns"
        render_icon(512).save(icns_path, "ICNS")
        print(f"[OK] {icns_path.name}")
    except Exception:
        print("[skip] icon.icns (install pillow-heif for macOS builds)")


if __name__ == "__main__":
    main()

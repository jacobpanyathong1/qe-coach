"""Generate the PWA app icons into webapp/static/icons/ (192 + 512 px)."""
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

FONT = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans-Bold.ttf"
OUT = Path(__file__).parent / "static" / "icons"
NAVY, RED, WHITE = (31, 78, 121), (192, 0, 0), (255, 255, 255)


def make(size):
    img = Image.new("RGB", (size, size), NAVY)
    d = ImageDraw.Draw(img)
    # red accent bar near the bottom
    bar_h = int(size * 0.06)
    d.rectangle([0, size - bar_h, size, size], fill=RED)
    # "QE" centered
    font = ImageFont.truetype(str(FONT), int(size * 0.46))
    text = "QE"
    box = d.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((size - w) / 2 - box[0], (size - h) / 2 - box[1] - size * 0.03),
           text, font=font, fill=WHITE)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"icon-{size}.png")
    print("wrote", OUT / f"icon-{size}.png")


if __name__ == "__main__":
    for s in (192, 512):
        make(s)

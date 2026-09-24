"""
Genera logo.png e icon.ico para CardChecker R
"""
from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 256

img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Fondo circular degradado (simulado con capas)
for i in range(SIZE // 2, 0, -1):
    t = i / (SIZE // 2)
    r = int(26  + (80  - 26)  * t)
    g = int(26  + (10  - 26)  * t)
    b = int(46  + (96  - 46)  * t)
    draw.ellipse(
        [SIZE // 2 - i, SIZE // 2 - i, SIZE // 2 + i, SIZE // 2 + i],
        fill=(r, g, b, 255)
    )

# Círculo borde accent
draw.ellipse([6, 6, SIZE - 6, SIZE - 6], outline=(233, 69, 96, 255), width=6)

# Letra R grande
try:
    font_r = ImageFont.truetype("arialbd.ttf", 110)
except Exception:
    font_r = ImageFont.load_default()

text_r = "R"
bbox = draw.textbbox((0, 0), text_r, font=font_r)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text(
    (SIZE // 2 - tw // 2 - 2, SIZE // 2 - th // 2 - 22),
    text_r, font=font_r, fill=(233, 69, 96, 255)
)

# Texto "check card" pequeño abajo
try:
    font_sub = ImageFont.truetype("arial.ttf", 22)
except Exception:
    font_sub = ImageFont.load_default()

sub = "check card"
bbox2 = draw.textbbox((0, 0), sub, font=font_sub)
sw = bbox2[2] - bbox2[0]
draw.text(
    (SIZE // 2 - sw // 2, SIZE - 58),
    sub, font=font_sub, fill=(200, 200, 200, 220)
)

# Guardar PNG
img.save("logo.png")
print("✅ logo.png generado")

# Guardar ICO (múltiples tamaños para mejor calidad en Windows)
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icons = [img.resize(s, Image.LANCZOS) for s in sizes]
icons[0].save("icon.ico", format="ICO", sizes=sizes,
              append_images=icons[1:])
print("✅ icon.ico generado")

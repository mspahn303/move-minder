from PIL import Image, ImageDraw

SIZE = 256
BG = "#4f46e5"
FG = "#ffffff"

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=56, fill=BG)


def thick_line(p1, p2, width, fill):
    draw.line([p1, p2], fill=fill, width=width)
    r = width / 2
    for (x, y) in (p1, p2):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


head_center = (168, 58)
head_r = 20
neck = (154, 80)
hip = (118, 132)
knee = (176, 158)
foot = (168, 208)
shoulder = (148, 88)
hand = (90, 102)

thick_line(neck, hip, 17, FG)
thick_line(hip, knee, 17, FG)
thick_line(knee, foot, 15, FG)
thick_line(shoulder, hand, 13, FG)

draw.ellipse(
    [head_center[0] - head_r, head_center[1] - head_r,
     head_center[0] + head_r, head_center[1] + head_r],
    fill=FG,
)

img.save(
    "icon.ico",
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("icon.ico written")

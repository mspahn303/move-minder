import math

from PIL import Image, ImageDraw

SIZE = 256

SKIN = "#f3c299"
HAIR = "#5b3a24"
SHIRT = "#2563eb"
SHORTS = "#f5a623"
SHOE = "#ffffff"
SHOE_OUTLINE = "#c9cfd8"

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)


def thick_line(p1, p2, width, fill):
    draw.line([p1, p2], fill=fill, width=width)
    r = width / 2
    for (x, y) in (p1, p2):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


cx = 128
head_center = (cx, 46)
head_r = 24
neck = (cx, 74)
hip = (cx, 138)
shoulder_l = (cx - 24, 84)
shoulder_r = (cx + 24, 84)
hand_l = (cx - 74, 24)
hand_r = (cx + 74, 24)
foot_l = (cx - 58, 224)
foot_r = (cx + 58, 224)

# legs (skin) with shorts overlay near hip, torso, shoulder caps, arms, shoes, head, hair
thick_line(hip, foot_l, 26, SKIN)
thick_line(hip, foot_r, 26, SKIN)

for foot in (foot_l, foot_r):
    shorts_end = (hip[0] + (foot[0] - hip[0]) * 0.4, hip[1] + (foot[1] - hip[1]) * 0.4)
    thick_line(hip, shorts_end, 34, SHORTS)

shoe_w, shoe_h = 42, 24
for foot in (foot_l, foot_r):
    draw.ellipse(
        [foot[0] - shoe_w / 2, foot[1] - shoe_h / 2, foot[0] + shoe_w / 2, foot[1] + shoe_h / 2],
        fill=SHOE, outline=SHOE_OUTLINE, width=3,
    )

thick_line(neck, hip, 42, SHIRT)
for shoulder in (shoulder_l, shoulder_r):
    draw.ellipse(
        [shoulder[0] - 18, shoulder[1] - 18, shoulder[0] + 18, shoulder[1] + 18], fill=SHIRT,
    )
thick_line(shoulder_l, hand_l, 15, SKIN)
thick_line(shoulder_r, hand_r, 15, SKIN)

draw.ellipse(
    [head_center[0] - head_r, head_center[1] - head_r,
     head_center[0] + head_r, head_center[1] + head_r],
    fill=SKIN,
)
draw.pieslice(
    [head_center[0] - head_r - 4, head_center[1] - head_r - 4,
     head_center[0] + head_r + 4, head_center[1] + head_r + 4],
    182, 358, fill=HAIR,
)

img.save(
    "icon.ico",
    format="ICO",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("icon.ico written")


def make_gear_png(path, color, display_size=22, supersample=8):
    s = display_size * supersample
    gear = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gear)

    cx = cy = s / 2
    outer_r = s * 0.46
    inner_r = s * 0.32
    hub_r = s * 0.15
    num_teeth = 8
    tooth_w = s * 0.16
    tooth_len = outer_r - inner_r * 0.9

    gdraw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=color)

    for i in range(num_teeth):
        theta = 2 * math.pi * i / num_teeth
        r_mid = (inner_r * 0.9 + outer_r) / 2
        center = (cx + r_mid * math.cos(theta), cy + r_mid * math.sin(theta))
        local = [(-tooth_len / 2, -tooth_w / 2), (tooth_len / 2, -tooth_w / 2),
                  (tooth_len / 2, tooth_w / 2), (-tooth_len / 2, tooth_w / 2)]
        pts = []
        for x, y in local:
            rx = x * math.cos(theta) - y * math.sin(theta)
            ry = x * math.sin(theta) + y * math.cos(theta)
            pts.append((center[0] + rx, center[1] + ry))
        gdraw.polygon(pts, fill=color)

    gdraw.ellipse([cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r], fill=(0, 0, 0, 0))

    gear = gear.resize((display_size, display_size), Image.LANCZOS)
    gear.save(path)


make_gear_png("gear.png", "#6b7280")
print("gear.png written")

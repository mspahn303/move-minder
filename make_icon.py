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


head_center = (170, 58)
head_r = 25
neck = (150, 85)
hip = (108, 130)
knee = (174, 160)
foot = (166, 206)
shoulder = (146, 94)
hand = (82, 110)

# legs (skin), shorts overlay near hip, shirt torso, sleeve cap, arm, shoe, head, hair
thick_line(hip, knee, 32, SKIN)
thick_line(knee, foot, 26, SKIN)

shorts_end = (hip[0] + (knee[0] - hip[0]) * 0.62, hip[1] + (knee[1] - hip[1]) * 0.62)
thick_line(hip, shorts_end, 37, SHORTS)

shoe_w, shoe_h = 48, 26
draw.ellipse(
    [foot[0] - shoe_w / 2, foot[1] - shoe_h / 2, foot[0] + shoe_w / 2, foot[1] + shoe_h / 2],
    fill=SHOE, outline=SHOE_OUTLINE, width=3,
)

thick_line(neck, hip, 34, SHIRT)
draw.ellipse(
    [shoulder[0] - 20, shoulder[1] - 20, shoulder[0] + 20, shoulder[1] + 20], fill=SHIRT,
)
thick_line(shoulder, hand, 15, SKIN)

draw.ellipse(
    [head_center[0] - head_r, head_center[1] - head_r,
     head_center[0] + head_r, head_center[1] + head_r],
    fill=SKIN,
)
draw.pieslice(
    [head_center[0] - head_r - 4, head_center[1] - head_r - 6,
     head_center[0] + head_r + 4, head_center[1] + head_r + 4],
    178, 345, fill=HAIR,
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

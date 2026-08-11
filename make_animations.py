from PIL import Image, ImageDraw

SKIN = "#f3c299"
HAIR = "#5b3a24"
SHIRT = "#2563eb"
SHORTS = "#f5a623"
SHOE = "#ffffff"
SHOE_OUTLINE = "#c9cfd8"

DISPLAY_SIZE = 64
SUPERSAMPLE = 6
CANVAS = DISPLAY_SIZE * SUPERSAMPLE


def new_canvas():
    return Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))


def thick_line(draw, p1, p2, width, fill):
    draw.line([p1, p2], fill=fill, width=width)
    r = width / 2
    for (x, y) in (p1, p2):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def draw_head(draw, center, r, hair_span=(182, 358)):
    draw.ellipse([center[0] - r, center[1] - r, center[0] + r, center[1] + r], fill=SKIN)
    draw.pieslice(
        [center[0] - r - 4, center[1] - r - 4, center[0] + r + 4, center[1] + r + 4],
        hair_span[0], hair_span[1], fill=HAIR,
    )


def draw_shoe(draw, center, w, h):
    draw.ellipse(
        [center[0] - w / 2, center[1] - h / 2, center[0] + w / 2, center[1] + h / 2],
        fill=SHOE, outline=SHOE_OUTLINE, width=8,
    )


def draw_shorts_overlay(draw, hip, far_point, width, fraction=0.55):
    end = (
        hip[0] + (far_point[0] - hip[0]) * fraction,
        hip[1] + (far_point[1] - hip[1]) * fraction,
    )
    thick_line(draw, hip, end, width, SHORTS)


def save_frame(img, name):
    small = img.resize((DISPLAY_SIZE, DISPLAY_SIZE), Image.LANCZOS)
    small.save(f"{name}.png")
    print(f"{name}.png written")


# All coordinates below are hand-placed within the actual 384x384 canvas
# (DISPLAY_SIZE * SUPERSAMPLE) -- keep new poses within roughly [20, 364].

# ---------- squats: standing <-> squatting (side profile, facing right) ----------

def squats_frame_a():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    head = (230, 55)
    neck = (220, 95)
    hip = (210, 220)
    knee = (210, 290)
    foot = (205, 350)
    shoulder = (216, 105)
    hand = (210, 200)
    thick_line(d, hip, knee, 46, SKIN)
    thick_line(d, knee, foot, 40, SKIN)
    draw_shorts_overlay(d, hip, knee, 52, 0.5)
    draw_shoe(d, foot, 70, 38)
    thick_line(d, neck, hip, 50, SHIRT)
    d.ellipse([shoulder[0] - 26, shoulder[1] - 26, shoulder[0] + 26, shoulder[1] + 26], fill=SHIRT)
    thick_line(d, shoulder, hand, 22, SKIN)
    draw_head(d, head, 34, (178, 350))
    save_frame(img, "anim_squats_0")


def squats_frame_b():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    head = (280, 90)
    neck = (250, 125)
    hip = (180, 200)
    knee = (290, 235)
    foot = (275, 330)
    shoulder = (230, 135)
    hand = (100, 155)
    thick_line(d, hip, knee, 46, SKIN)
    thick_line(d, knee, foot, 40, SKIN)
    draw_shorts_overlay(d, hip, knee, 52, 0.5)
    draw_shoe(d, foot, 70, 38)
    thick_line(d, neck, hip, 50, SHIRT)
    d.ellipse([shoulder[0] - 26, shoulder[1] - 26, shoulder[0] + 26, shoulder[1] + 26], fill=SHIRT)
    thick_line(d, shoulder, hand, 22, SKIN)
    draw_head(d, head, 34, (178, 350))
    save_frame(img, "anim_squats_1")


# ---------- push-ups: arms extended (up) <-> arms bent (down), lying prone ----------

def pushups_frame_a():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    head = (330, 140)
    neck = (290, 155)
    hip = (150, 190)
    foot = (50, 280)
    hand = (290, 280)
    thick_line(d, hip, foot, 40, SKIN)
    draw_shorts_overlay(d, hip, foot, 48, 0.4)
    draw_shoe(d, foot, 40, 62)
    thick_line(d, neck, hip, 48, SHIRT)
    thick_line(d, neck, hand, 24, SKIN)
    draw_head(d, head, 34, (170, 345))
    save_frame(img, "anim_pushups_0")


def pushups_frame_b():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    head = (330, 210)
    neck = (290, 220)
    hip = (150, 235)
    foot = (50, 285)
    hand = (290, 285)
    thick_line(d, hip, foot, 40, SKIN)
    draw_shorts_overlay(d, hip, foot, 48, 0.4)
    draw_shoe(d, foot, 40, 62)
    thick_line(d, neck, hip, 48, SHIRT)
    thick_line(d, neck, hand, 24, SKIN)
    draw_head(d, head, 34, (170, 345))
    save_frame(img, "anim_pushups_1")


# ---------- sit-ups: lying flat <-> crunched up, hip/knee/foot stay planted ----------

def situps_frame_a():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    head = (60, 300)
    neck = (120, 300)
    hip = (230, 310)
    knee = (320, 280)
    foot = (310, 350)
    hand = (100, 290)
    thick_line(d, hip, knee, 44, SKIN)
    thick_line(d, knee, foot, 38, SKIN)
    draw_shorts_overlay(d, hip, knee, 50, 0.5)
    draw_shoe(d, foot, 60, 38)
    thick_line(d, neck, hip, 48, SHIRT)
    thick_line(d, neck, hand, 20, SKIN)
    draw_head(d, head, 34, (250, 60))
    save_frame(img, "anim_situps_0")


def situps_frame_b():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    head = (220, 150)
    neck = (240, 190)
    hip = (230, 310)
    knee = (320, 280)
    foot = (310, 350)
    hand = (270, 220)
    thick_line(d, hip, knee, 44, SKIN)
    thick_line(d, knee, foot, 38, SKIN)
    draw_shorts_overlay(d, hip, knee, 50, 0.5)
    draw_shoe(d, foot, 60, 38)
    thick_line(d, neck, hip, 48, SHIRT)
    thick_line(d, neck, hand, 20, SKIN)
    draw_head(d, head, 34, (200, 15))
    save_frame(img, "anim_situps_1")


# ---------- burpees: crouched/plank (down) <-> jump with arms overhead (up) ----------

def burpees_frame_a():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    head = (330, 220)
    neck = (295, 230)
    hip = (170, 250)
    foot = (60, 300)
    hand = (295, 300)
    thick_line(d, hip, foot, 42, SKIN)
    draw_shorts_overlay(d, hip, foot, 48, 0.45)
    draw_shoe(d, foot, 44, 58)
    thick_line(d, neck, hip, 46, SHIRT)
    thick_line(d, neck, hand, 22, SKIN)
    draw_head(d, head, 34, (170, 345))
    save_frame(img, "anim_burpees_0")


def burpees_frame_b():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    cx = 190
    head = (cx, 50)
    neck = (cx, 90)
    hip = (cx, 230)
    foot = (cx, 340)
    shoulder_l, shoulder_r = (cx - 24, 105), (cx + 24, 105)
    hand_l, hand_r = (cx - 90, 25), (cx + 90, 25)
    thick_line(d, hip, foot, 44, SKIN)
    draw_shorts_overlay(d, hip, foot, 50, 0.4)
    draw_shoe(d, foot, 66, 36)
    thick_line(d, neck, hip, 48, SHIRT)
    for shoulder in (shoulder_l, shoulder_r):
        d.ellipse([shoulder[0] - 22, shoulder[1] - 22, shoulder[0] + 22, shoulder[1] + 22], fill=SHIRT)
    thick_line(d, shoulder_l, hand_l, 18, SKIN)
    thick_line(d, shoulder_r, hand_r, 18, SKIN)
    draw_head(d, head, 34, (182, 358))
    save_frame(img, "anim_burpees_1")


# ---------- jumping jacks: closed (arms/legs together) <-> open (arms/legs spread) ----------

def jumping_jacks_frame_a():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    cx = 190
    head = (cx, 70)
    neck = (cx, 120)
    hip = (cx, 230)
    shoulder_l, shoulder_r = (cx - 18, 128), (cx + 18, 128)
    hand_l, hand_r = (cx - 25, 210), (cx + 25, 210)
    foot_l, foot_r = (cx - 12, 350), (cx + 12, 350)
    thick_line(d, hip, foot_l, 40, SKIN)
    thick_line(d, hip, foot_r, 40, SKIN)
    for foot in (foot_l, foot_r):
        draw_shorts_overlay(d, hip, foot, 46, 0.35)
        draw_shoe(d, foot, 52, 30)
    thick_line(d, neck, hip, 50, SHIRT)
    for shoulder in (shoulder_l, shoulder_r):
        d.ellipse([shoulder[0] - 20, shoulder[1] - 20, shoulder[0] + 20, shoulder[1] + 20], fill=SHIRT)
    thick_line(d, shoulder_l, hand_l, 16, SKIN)
    thick_line(d, shoulder_r, hand_r, 16, SKIN)
    draw_head(d, head, 36, (182, 358))
    save_frame(img, "anim_jumping_jacks_0")


def jumping_jacks_frame_b():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    cx = 190
    head = (cx, 70)
    neck = (cx, 120)
    hip = (cx, 230)
    shoulder_l, shoulder_r = (cx - 32, 132), (cx + 32, 132)
    hand_l, hand_r = (cx - 100, 35), (cx + 100, 35)
    foot_l, foot_r = (cx - 80, 355), (cx + 80, 355)
    thick_line(d, hip, foot_l, 40, SKIN)
    thick_line(d, hip, foot_r, 40, SKIN)
    for foot in (foot_l, foot_r):
        draw_shorts_overlay(d, hip, foot, 46, 0.35)
        draw_shoe(d, foot, 52, 30)
    thick_line(d, neck, hip, 50, SHIRT)
    for shoulder in (shoulder_l, shoulder_r):
        d.ellipse([shoulder[0] - 20, shoulder[1] - 20, shoulder[0] + 20, shoulder[1] + 20], fill=SHIRT)
    thick_line(d, shoulder_l, hand_l, 16, SKIN)
    thick_line(d, shoulder_r, hand_r, 16, SKIN)
    draw_head(d, head, 36, (182, 358))
    save_frame(img, "anim_jumping_jacks_1")


if __name__ == "__main__":
    squats_frame_a()
    squats_frame_b()
    pushups_frame_a()
    pushups_frame_b()
    situps_frame_a()
    situps_frame_b()
    burpees_frame_a()
    burpees_frame_b()
    jumping_jacks_frame_a()
    jumping_jacks_frame_b()

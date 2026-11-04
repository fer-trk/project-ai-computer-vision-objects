"""Generate a synthetic nox_texto diagnostic set, kept apart from the official data.

Every image is drawn procedurally. No real frame, photo or brand asset is used,
and the NOX wordmark is rendered with generic DejaVu fonts, not the real brand
typography. The set only checks the pipeline and a controlled pattern.
"""

import argparse
import colorsys
import hashlib
import io
import json
import math
import platform
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

VERSION = "1.0.0"
CLASS_NAME = "nox_texto"
WORD = "NOX"
SPLITS = ("diag_train", "diag_val")
SIZES = ((640, 640), (540, 960), (960, 540))
ALPHA_THRESHOLD = 0.3
MIN_VISIBLE_FRACTION = 0.6
MIN_BOX_SIZE = (32, 14)
FONTS = {
    "sans-bold": "DejaVuSans-Bold.ttf",
    "serif-bold": "DejaVuSerif-Bold.ttf",
    "sans-bold-oblique": "DejaVuSans-BoldOblique.ttf",
    "mono-bold": "DejaVuSansMono-Bold.ttf",
}
# Reserved for positive validation prints; negative decoy text can use every font.
VAL_ONLY_FONT = "mono-bold"
FONT_LICENSE = "Bitstream Vera / DejaVu fonts license (free to use and redistribute); bundled with matplotlib, not copied into the repository"
TEXT_PALETTE = ((255, 255, 255), (245, 245, 245), (12, 12, 12), (255, 115, 20), (255, 214, 0), (200, 200, 200), (230, 30, 50), (20, 60, 180))
SKIN_TONES = ((224, 172, 105), (198, 134, 66), (141, 85, 36), (255, 219, 172), (110, 70, 45))
DECOY_WORDS = ("HOX", "MOX", "NOK", "KOX", "NOZ", "VOX", "NQX", "POX", "PADEL", "TEAM", "ACE", "PRO")
POSITIVE_KINDS = ("shirt_chest", "shirt_sleeve", "paddle_face")
NEGATIVE_KINDS = ("neg_lookalike_text", "neg_plain_garment", "neg_limbs", "neg_crowd", "neg_texture")
YAML_TEXT = (
    "# Synthetic diagnostic set. Not part of the official train/val/test splits.\n"
    "train: images/diag_train\n"
    "val: images/diag_val\n"
    "names:\n"
    "  0: nox_texto\n"
)
LIMITATIONS = [
    "Fully synthetic: the wordmark uses generic DejaVu fonts, not the real NOX typography",
    "Backgrounds, occluders and lighting are simplified procedural drawings, not real scenes",
    "Validation shares the generator with training; it is not independent evidence of generalization",
    "Results on this set must never be reported as detector reliability or as official metrics",
]


def digest(path):
    """Hash a file without retaining all bytes."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def font_directory():
    """Locate the DejaVu fonts that ship with matplotlib."""
    import matplotlib

    return Path(matplotlib.get_data_path()) / "fonts" / "ttf"


def luminance(rgb):
    """Relative luminance of an 8-bit RGB color."""
    r, g, b = (c / 255 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def random_color(rng, value_range=(0.08, 0.95), max_saturation=0.9):
    """Draw an arbitrary 8-bit RGB color."""
    hue, sat, val = rng.random(), rng.uniform(0, max_saturation), rng.uniform(*value_range)
    return tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(hue, sat, val))


def pick_text_color(rng, under, min_delta):
    """Choose a print color whose luminance differs enough from the surface."""
    options = [c for c in TEXT_PALETTE if abs(luminance(c) - luminance(under)) >= min_delta]
    if not options:
        return (255, 255, 255) if luminance(under) < 0.5 else (12, 12, 12)
    return options[int(rng.integers(len(options)))]


def smooth_noise(rng, height, width, cells):
    """Low-frequency noise in [0, 1] used for wrinkles and uneven backgrounds."""
    small = Image.fromarray((rng.random((cells, cells)) * 255).astype(np.uint8))
    return np.asarray(small.resize((width, height), Image.BICUBIC), dtype=np.float32) / 255


def perspective_coeffs(output_points, input_points):
    """Coefficients for PIL: output pixel -> input pixel."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(output_points, input_points):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rhs.append(u)
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        rhs.append(v)
    return np.linalg.solve(np.array(rows, float), np.array(rhs, float)).tolist()


def render_word(rng, word, font_path, color, outline, target_width, rotation, warp):
    """Render a word as a tight RGBA layer, perspective-warped and rotated."""
    font = ImageFont.truetype(str(font_path), 220)
    stroke = 0 if outline is None else 10
    outer = Image.new("L", (1400, 500), 0)
    inner = Image.new("L", (1400, 500), 0)
    ImageDraw.Draw(outer).text((60, 60), word, font=font, fill=255, stroke_width=stroke)
    ImageDraw.Draw(inner).text((60, 60), word, font=font, fill=255)
    box = outer.getbbox()
    layer = Image.new("RGBA", outer.size, (*(outline or color), 255))
    layer.paste((*color, 255), mask=inner)
    layer.putalpha(outer)
    layer = layer.crop(box)
    scale = target_width / layer.width
    layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))), Image.LANCZOS)
    pad_x, pad_y = round(layer.width * 0.2), round(layer.height * 0.2)
    padded = Image.new("RGBA", (layer.width + 2 * pad_x, layer.height + 2 * pad_y), (0, 0, 0, 0))
    padded.paste(layer, (pad_x, pad_y))
    w, h = padded.size
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    moved = [(x + rng.uniform(-warp, warp) * w, y + rng.uniform(-warp, warp) * h) for x, y in corners]
    padded = padded.transform((w, h), Image.PERSPECTIVE, perspective_coeffs(moved, corners), Image.BICUBIC)
    padded = padded.rotate(rotation, expand=True, resample=Image.BICUBIC)
    solid = padded.getchannel("A").point(lambda a: 255 if a > 8 else 0)
    return padded.crop(solid.getbbox())


def place_layer(layer, size, center):
    """Paste a layer on a transparent full-size canvas, kept inside the image."""
    width, height = size
    x = int(min(max(round(center[0] - layer.width / 2), 0), width - layer.width))
    y = int(min(max(round(center[1] - layer.height / 2), 0), height - layer.height))
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(layer, (x, y))
    return canvas


def rotated_mask(draw_fn, size, angle, center):
    """Draw on an L mask and rotate it about a center."""
    mask = Image.new("L", size, 0)
    draw_fn(ImageDraw.Draw(mask))
    return mask.rotate(angle, center=center, resample=Image.BICUBIC)


def scene_garment(rng, size, sleeve):
    """Close-up of fabric, optionally with a color-block or sleeve band."""
    width, height = size
    base = random_color(rng)
    image = Image.new("RGB", size, base)
    center = (width / 2, height / 2)
    under, angle, max_width = base, rng.uniform(-12, 12), 0.7 * width
    if sleeve or rng.random() < 0.4:
        under = random_color(rng)
        if sleeve:
            angle = float(rng.choice([-1, 1]) * rng.uniform(25, 70))
            band = height * rng.uniform(0.25, 0.45)
            max_width = 1.5 * band
        else:
            band = height * rng.uniform(0.4, 0.7)
        mask = rotated_mask(lambda d: d.rectangle([-width, center[1] - band / 2, 2 * width, center[1] + band / 2], fill=255), size, angle, center)
        image.paste(under, mask=mask)
    return dict(image=image, backdrop=None, holes=None, center=center, under=under, angle=float(angle), max_width=float(max_width), spread=0.12 * width)


def scene_paddle(rng, size):
    """Perforated paddle face over a court-colored backdrop."""
    width, height = size
    backdrop = Image.new("RGB", size, random_color(rng, (0.25, 0.9), 0.6))
    cx, cy = width * rng.uniform(0.4, 0.6), height * rng.uniform(0.4, 0.6)
    rx, ry = width * rng.uniform(0.3, 0.55), height * rng.uniform(0.3, 0.55)
    angle = float(rng.uniform(-40, 40))
    color = random_color(rng, (0.06, 0.8))

    def face(draw):
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
        draw.rectangle([cx - 0.12 * rx, cy, cx + 0.12 * rx, cy + 2.2 * ry], fill=255)

    paddle = rotated_mask(face, size, angle, (cx, cy))
    image = backdrop.copy()
    image.paste(color, mask=paddle)
    step, radius = 0.045 * width, 0.008 * width
    holes = Image.new("L", size, 0)
    hole_draw = ImageDraw.Draw(holes)
    for row, y in enumerate(np.arange(0, height + step, step * 0.866)):
        for x in np.arange((row % 2) * step / 2, width + step, step):
            hole_draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=255)
    holes = Image.fromarray(np.minimum(np.asarray(holes), np.asarray(paddle)))
    ox, oy = rng.uniform(-0.3, 0.3) * rx, rng.uniform(-0.3, 0.3) * ry
    theta = math.radians(angle)
    center = (cx + ox * math.cos(theta) + oy * math.sin(theta), cy - ox * math.sin(theta) + oy * math.cos(theta))
    text_angle = angle + float(rng.choice([0, 0, 90]))
    return dict(image=image, backdrop=backdrop, holes=holes, center=center, under=color, angle=text_angle, max_width=1.2 * min(rx, ry), spread=0.0)


def decoy_garment(rng, size):
    """Garment with stripes, circles or chevrons, never any NOX."""
    scene = scene_garment(rng, size, sleeve=False)
    draw = ImageDraw.Draw(scene["image"])
    width, height = size
    for _ in range(int(rng.integers(1, 5))):
        color = random_color(rng)
        kind = int(rng.integers(3))
        if kind == 0:
            y = rng.uniform(0, height)
            draw.line([(0, y), (width, y + rng.uniform(-0.2, 0.2) * height)], fill=color, width=int(rng.uniform(0.02, 0.1) * height))
        elif kind == 1:
            x, y, r = rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0.04, 0.2) * min(size)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
        else:
            x, y, s = rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0.1, 0.3) * min(size)
            draw.polygon([(x - s, y), (x, y - s / 2), (x + s, y), (x, y + s / 2)], fill=color)
    return scene


def scene_limbs(rng, size):
    """Skin-toned arms and a wristband over cloth."""
    image = Image.new("RGB", size, random_color(rng))
    draw = ImageDraw.Draw(image)
    width, height = size
    for _ in range(int(rng.integers(2, 5))):
        x, y, theta = rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0, math.pi)
        half = max(size)
        thick = int(rng.uniform(0.1, 0.3) * min(size))
        dx, dy = math.cos(theta) * half, math.sin(theta) * half
        tone = SKIN_TONES[int(rng.integers(len(SKIN_TONES)))]
        draw.line([(x - dx, y - dy), (x + dx, y + dy)], fill=tone, width=thick)
        if rng.random() < 0.5:
            draw.line([(x - dx * 0.05, y - dy * 0.05), (x + dx * 0.05, y + dy * 0.05)], fill=(240, 240, 240), width=thick + 6)
    return dict(image=image)


def scene_crowd(rng, size):
    """Rows of simplified spectators."""
    width, height = size
    image = Image.new("RGB", size, tuple(int(v) for v in rng.integers(10, 60, 3)))
    draw = ImageDraw.Draw(image)
    rows = int(rng.integers(3, 7))
    for row in range(rows):
        scale = 0.6 + row / rows
        radius = 0.025 * min(size) * scale
        y = height * (row + 0.5) / rows
        for x in np.arange(rng.uniform(0, radius * 3), width + radius * 4, radius * 3.2):
            xj, yj = x + rng.uniform(-radius, radius), y + rng.uniform(-radius, radius)
            draw.rectangle([xj - radius * 1.3, yj + radius, xj + radius * 1.3, yj + radius * 4], fill=random_color(rng))
            draw.ellipse([xj - radius, yj - radius, xj + radius, yj + radius], fill=SKIN_TONES[int(rng.integers(len(SKIN_TONES)))])
    return dict(image=image)


def scene_texture(rng, size):
    """Net mesh, court lines or a perforated paddle without any print."""
    width, height = size
    choice = int(rng.integers(3))
    if choice == 2:
        scene = scene_paddle(rng, size)
        image = scene["image"].copy()
        image.paste(scene["backdrop"], mask=scene["holes"])
        return dict(image=image, texture="perforated_paddle")
    image = Image.new("RGB", size, random_color(rng, (0.1, 0.8)))
    draw = ImageDraw.Draw(image)
    if choice == 0:
        spacing = int(rng.integers(18, 40))
        for offset in range(-height, width + height, spacing):
            draw.line([(offset, 0), (offset + height, height)], fill=(20, 20, 20), width=2)
            draw.line([(offset + height, 0), (offset, height)], fill=(20, 20, 20), width=2)
        return dict(image=image, texture="net_mesh")
    for _ in range(int(rng.integers(2, 6))):
        draw.line([(rng.uniform(0, width), 0), (rng.uniform(0, width), height)], fill=(240, 240, 240), width=int(rng.integers(4, 14)))
    return dict(image=image, texture="court_lines")


def make_occluder(rng, size, focus):
    """Arm, ball or frame edge drawn over a point of interest."""
    width, height = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = rng.uniform(focus[0], focus[2]), rng.uniform(focus[1], focus[3])
    kind = ("arm", "ball", "frame_edge")[int(rng.integers(3))]
    if kind == "ball":
        r = rng.uniform(0.08, 0.2) * min(size)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(205, 230, 60, 255))
        draw.arc([x - r * 0.7, y - r * 0.7, x + r * 0.7, y + r * 0.7], 200, 340, fill=(250, 250, 250, 255), width=max(2, int(r * 0.08)))
    else:
        theta, half = rng.uniform(0, math.pi), max(size)
        fill = (*SKIN_TONES[int(rng.integers(len(SKIN_TONES)))], 255) if kind == "arm" else (30, 30, 35, 255)
        thick = int(rng.uniform(0.12, 0.3) * min(size)) if kind == "arm" else int(rng.uniform(0.05, 0.12) * min(size))
        draw.line([(x - math.cos(theta) * half, y - math.sin(theta) * half), (x + math.cos(theta) * half, y + math.sin(theta) * half)], fill=fill, width=thick)
    return layer, kind


def shade_map(rng, size, strength):
    """Multiplicative folds and wrinkles."""
    width, height = size
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    folds = np.zeros((height, width), np.float32)
    for _ in range(3):
        theta, freq, phase = rng.uniform(0, math.pi), rng.uniform(0.5, 3.0), rng.uniform(0, 2 * math.pi)
        folds += rng.uniform(0.3, 1) * np.sin(2 * math.pi * freq * (xx * math.cos(theta) + yy * math.sin(theta)) / max(size) + phase)
    folds /= 3
    wrinkles = (smooth_noise(rng, height, width, 6) - 0.5) * 2
    weave = 0.02 * np.sin(xx * 1.6) * np.sin(yy * 1.6)
    return (1 + strength * (folds + 0.5 * wrinkles) + weave)[..., None]


def finish(rng, flat, params):
    """Apply shading, lighting, blur, noise and compression; record the choices."""
    width, height = flat.size
    arr = np.asarray(flat, np.float32) / 255
    strength = float(rng.uniform(0.05, 0.3))
    arr = arr * shade_map(rng, flat.size, strength)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    theta, gradient = float(rng.uniform(0, 2 * math.pi)), float(rng.uniform(0, 0.5))
    arr = arr * (1 + gradient * ((xx * math.cos(theta) + yy * math.sin(theta)) / max(size_of(flat)) - 0.5))[..., None]
    gain, contrast = float(rng.uniform(0.55, 1.25)), float(rng.uniform(0.7, 1.3))
    cast = rng.uniform(-0.06, 0.06, 3)
    arr = (arr * gain - arr.mean()) * contrast + arr.mean()
    arr = arr * (1 + cast)
    glare = bool(rng.random() < 0.25)
    if glare:
        gx, gy, gr = rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0.1, 0.35) * max(size_of(flat))
        arr = arr + 0.35 * np.exp(-((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * gr**2))[..., None]
    params["lighting"] = dict(fold_strength=strength, gradient=gradient, gradient_angle=theta, gain=gain, contrast=contrast, color_cast=[float(c) for c in cast], glare=glare)
    blur_kind = ("none", "gaussian", "motion")[int(rng.choice(3, p=[0.4, 0.3, 0.3]))]
    blur = dict(kind=blur_kind)
    arr = np.clip(arr, 0, 1)
    if blur_kind == "gaussian":
        blur["radius"] = float(rng.uniform(0.8, 2.5))
        from PIL import ImageFilter

        arr = np.asarray(Image.fromarray((arr * 255 + 0.5).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur["radius"])), np.float32) / 255
    elif blur_kind == "motion":
        blur["length"], blur["angle"] = int(rng.integers(5, 15)), float(rng.uniform(0, math.pi))
        pad = blur["length"]
        padded = np.pad(arr, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        acc = np.zeros_like(arr)
        for i in range(blur["length"]):
            t = (i / (blur["length"] - 1) - 0.5) * blur["length"]
            dx, dy = round(t * math.cos(blur["angle"])), round(t * math.sin(blur["angle"]))
            acc += padded[pad + dy : pad + dy + height, pad + dx : pad + dx + width]
        arr = acc / blur["length"]
    params["blur"] = blur
    sigma = float(rng.choice([0.0, 0.01, 0.02, 0.03]))
    arr = np.clip(arr + rng.normal(0, sigma, arr.shape), 0, 1)
    params["noise_sigma"] = sigma
    out = Image.fromarray((arr * 255 + 0.5).astype(np.uint8))
    quality = int(rng.integers(40, 91)) if rng.random() < 0.4 else None
    if quality:
        buffer = io.BytesIO()
        out.save(buffer, "JPEG", quality=quality)
        out = Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")
    params["jpeg_quality"] = quality
    return out


def size_of(image):
    return image.size


def make_prints(rng, scene, size, font_ids, word, params):
    """Create 1-2 non-overlapping print layers (RGBA full-canvas) for a scene."""
    width, height = size
    fonts = font_directory()
    prints = []
    for k in range(2 if rng.random() < 0.15 and scene["max_width"] > 0.5 * width else 1):
        font_id = font_ids[int(rng.integers(len(font_ids)))]
        target = float(np.exp(rng.uniform(math.log(0.1), math.log(0.6))) * width) * (0.5 if k else 1)
        target = max(60.0, min(target, scene["max_width"]))
        color = pick_text_color(rng, scene["under"], float(rng.uniform(0.2, 0.5)))
        outline = None if rng.random() < 0.7 else pick_text_color(rng, color, 0.4)
        rotation = scene["angle"] + float(rng.uniform(-8, 8)) * (k + 1)
        warp = float(rng.uniform(0, 0.1))
        layer = render_word(rng, word, fonts / FONTS[font_id], color, outline, target, rotation, warp)
        while layer.width > 0.95 * width or layer.height > 0.95 * height:
            layer = layer.resize((int(layer.width * 0.9), int(layer.height * 0.9)), Image.LANCZOS)
        cx = scene["center"][0] + rng.uniform(-1, 1) * scene["spread"] * (3 if k else 1)
        cy = scene["center"][1] + rng.uniform(-1, 1) * (0.25 * height if (k or not scene["spread"] == 0) else 0.1 * height)
        if k:
            cx, cy = rng.uniform(0, width), rng.uniform(0, height)
        canvas = place_layer(layer, size, (cx, cy))
        box = canvas.getchannel("A").point(lambda a: 255 if a > 76 else 0).getbbox()
        if any(not (box[2] <= b[0] - 4 or box[0] >= b[2] + 4 or box[3] <= b[1] - 4 or box[1] >= b[3] + 4) for b in [p["box0"] for p in prints]):
            continue
        prints.append(dict(canvas=canvas, box0=box, font=font_id, color=list(color), outline=None if outline is None else list(outline), target_width=target, rotation=float(rotation), warp=warp, text_bg_luminance_delta=abs(luminance(color) - luminance(scene["under"]))))
    params["prints_requested"] = len(prints)
    return prints


def compose_positive(rng, kind, size, font_ids, params):
    """One positive image plus tight visible boxes, or None if constraints fail."""
    scene = scene_garment(rng, size, kind == "shirt_sleeve") if kind != "paddle_face" else scene_paddle(rng, size)
    prints = make_prints(rng, scene, size, font_ids, WORD, params)
    image = scene["image"].copy()
    for p in prints:
        image.paste(p["canvas"], mask=p["canvas"].getchannel("A"))
    if scene["holes"] is not None:
        image.paste(scene["backdrop"], mask=scene["holes"])
    holes = np.asarray(scene["holes"], np.float32) / 255 if scene["holes"] is not None else 0
    occluder, occlusion = None, "none"
    if rng.random() < 0.35:
        focus = prints[0]["box0"]
        layer, occlusion = make_occluder(rng, size, focus)
        occluder = layer
        image.paste(layer, mask=layer.getchannel("A"))
    occ = np.asarray(occluder.getchannel("A"), np.float32) / 255 if occluder is not None else 0
    boxes = []
    for p in prints:
        alpha = np.asarray(p["canvas"].getchannel("A"), np.float32) / 255
        total = (alpha > ALPHA_THRESHOLD).sum()
        visible = alpha * (1 - holes) * (1 - occ)
        mask = visible > ALPHA_THRESHOLD
        if mask.sum() < MIN_VISIBLE_FRACTION * total:
            return None
        ys, xs = np.nonzero(mask)
        x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        if x2 - x1 < MIN_BOX_SIZE[0] or y2 - y1 < MIN_BOX_SIZE[1]:
            return None
        boxes.append(dict(bbox_xyxy=[x1, y1, x2, y2], visible_fraction=float(mask.sum() / total)))
    params["prints"] = [{k: v for k, v in p.items() if k not in ("canvas", "box0")} for p in prints]
    params["occluder"] = occlusion
    params["surface_angle"] = scene["angle"]
    return image, boxes


def compose_negative(rng, kind, size, params):
    """One hard negative image without NOX."""
    if kind == "neg_lookalike_text":
        scene = scene_paddle(rng, size) if rng.random() < 0.4 else scene_garment(rng, size, sleeve=bool(rng.random() < 0.3))
        word = DECOY_WORDS[int(rng.integers(len(DECOY_WORDS)))]
        params["decoy_word"] = word
        prints = make_prints(rng, scene, size, tuple(FONTS), word, params)
        image = scene["image"].copy()
        for p in prints:
            image.paste(p["canvas"], mask=p["canvas"].getchannel("A"))
        if scene["holes"] is not None:
            image.paste(scene["backdrop"], mask=scene["holes"])
        params["prints"] = [{k: v for k, v in p.items() if k not in ("canvas", "box0")} for p in prints]
        params.pop("prints_requested", None)
    elif kind == "neg_plain_garment":
        image = decoy_garment(rng, size)["image"]
    elif kind == "neg_limbs":
        image = scene_limbs(rng, size)["image"]
    elif kind == "neg_crowd":
        image = scene_crowd(rng, size)["image"]
    else:
        scene = scene_texture(rng, size)
        image, params["texture"] = scene["image"], scene["texture"]
    occlusion = "none"
    if rng.random() < 0.35:
        layer, occlusion = make_occluder(rng, size, (0, 0, size[0], size[1]))
        image.paste(layer, mask=layer.getchannel("A"))
    params["occluder"] = occlusion
    return image


def generate_image(seed, index, kind, split):
    """Create one image deterministically from (seed, index)."""
    rng = np.random.default_rng([seed, index])
    size = SIZES[int(rng.integers(len(SIZES)))]
    font_ids = tuple(FONTS) if split == "diag_val" else tuple(f for f in FONTS if f != VAL_ONLY_FONT)
    params = dict(image_size=list(size))
    for _ in range(60):
        if kind in POSITIVE_KINDS:
            built = compose_positive(rng, kind, size, font_ids, params)
            if built is None:
                continue
            flat, boxes = built
        else:
            flat, boxes = compose_negative(rng, kind, size, params), []
        return finish(rng, flat, params), boxes, params
    raise RuntimeError(f"No valid {kind} image after 60 attempts (index {index})")


def yolo_row(box, size):
    """Normalized YOLO row for class 0."""
    (x1, y1, x2, y2), (w, h) = box, size
    return "0 " + " ".join(f"{v:.10f}" for v in ((x1 + x2) / (2 * w), (y1 + y2) / (2 * h), (x2 - x1) / w, (y2 - y1) / h))


def kind_plan(count, kinds):
    """Balanced, deterministic kind sequence."""
    return [kinds[i % len(kinds)] for i in range(count)]


def tool_versions():
    import matplotlib

    return dict(generator=VERSION, python=platform.python_version(), pillow=Image.__version__, numpy=np.__version__, matplotlib=matplotlib.__version__)


def build(output, seed, counts):
    """Write images, labels, YAML and manifest to a new folder."""
    output = Path(output)
    if (output / "images").exists() or (output / "manifest.json").exists():
        raise FileExistsError("Refusing to overwrite a generated set")
    fonts = font_directory()
    for name in FONTS.values():
        if not (fonts / name).is_file():
            raise FileNotFoundError(f"Missing font {fonts / name}")
    records, index = [], 0
    for split in SPLITS:
        pos, neg = counts[split]
        plan = kind_plan(pos, POSITIVE_KINDS) + kind_plan(neg, NEGATIVE_KINDS)
        for kind in plan:
            image, boxes, params = generate_image(seed, index, kind, split)
            stem = f"nox_synth_{split}_{index:04d}_{kind}"
            image_path, label_path = output / "images" / split / (stem + ".png"), output / "labels" / split / (stem + ".txt")
            image_path.parent.mkdir(parents=True, exist_ok=True)
            label_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(image_path)
            rows = [yolo_row(b["bbox_xyxy"], image.size) for b in boxes]
            label_path.write_text("".join(row + "\n" for row in rows), encoding="utf-8")
            records.append(dict(
                image=image_path.relative_to(output).as_posix(), label=label_path.relative_to(output).as_posix(), split=split, index=index,
                synthetic=True, seed=[seed, index], scene_type=kind, positive=bool(boxes), width=image.width, height=image.height,
                image_sha256=digest(image_path), label_sha256=digest(label_path),
                boxes=[dict(class_id=0, class_name=CLASS_NAME, bbox_xyxy=b["bbox_xyxy"], yolo=[float(v) for v in row.split()[1:]], visible_fraction=b["visible_fraction"]) for b, row in zip(boxes, rows)],
                transformations=params))
            index += 1
    (output / "dataset.yaml").write_text(YAML_TEXT, encoding="utf-8")
    summary = {split: dict(images=sum(r["split"] == split for r in records), positives=sum(r["split"] == split and r["positive"] for r in records), negatives=sum(r["split"] == split and not r["positive"] for r in records), boxes=sum(len(r["boxes"]) for r in records if r["split"] == split)) for split in SPLITS}
    manifest = dict(
        synthetic=True, purpose="Pipeline check and controlled-pattern study for nox_texto; not a measure of real-world reliability",
        tool=tool_versions(), seed=seed, classes={"0": CLASS_NAME}, official_dataset_mixing=False,
        generation_parameters=dict(counts_per_split={s: dict(positives=counts[s][0], negatives=counts[s][1]) for s in SPLITS}, sizes=[list(s) for s in SIZES], alpha_threshold=ALPHA_THRESHOLD, min_visible_fraction=MIN_VISIBLE_FRACTION, min_box_size=list(MIN_BOX_SIZE), word=WORD, decoy_words=list(DECOY_WORDS), val_only_font=VAL_ONLY_FONT, positive_kinds=list(POSITIVE_KINDS), negative_kinds=list(NEGATIVE_KINDS)),
        fonts=[dict(id=k, file=v, sha256=digest(fonts / v), license=FONT_LICENSE, source="matplotlib bundled DejaVu fonts") for k, v in FONTS.items()],
        rights="No external images or real frames are used; every pixel is generated by this script. Only the DejaVu fonts are external.",
        summary=summary, limitations=LIMITATIONS, images=records)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def validate(output, ultralytics=False):
    """Check files, hashes, boxes and YAML; raise ValueError listing problems."""
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    if manifest.get("synthetic") is not True or manifest.get("official_dataset_mixing") is not False:
        problems.append("manifest must declare synthetic=true and official_dataset_mixing=false")
    if manifest.get("classes") != {"0": CLASS_NAME}:
        problems.append("only class 0 nox_texto is allowed")
    if (output / "dataset.yaml").read_text(encoding="utf-8") != YAML_TEXT:
        problems.append("dataset.yaml differs from the expected synthetic definition")
    listed, hashes = set(), set()
    for record in manifest["images"]:
        name = record["image"]
        image_path, label_path = output / name, output / record["label"]
        listed |= {image_path.resolve(), label_path.resolve()}
        if record["split"] not in SPLITS or record["synthetic"] is not True:
            problems.append(f"{name}: bad split or synthetic flag")
        if not image_path.is_file() or not label_path.is_file():
            problems.append(f"{name}: missing image or label")
            continue
        if digest(image_path) != record["image_sha256"] or digest(label_path) != record["label_sha256"]:
            problems.append(f"{name}: hash mismatch")
        hashes.add(record["image_sha256"])
        with Image.open(image_path) as image:
            image.load()
            width, height = image.size
        if (width, height) != (record["width"], record["height"]):
            problems.append(f"{name}: dimensions differ from manifest")
        rows = [line.split() for line in label_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if record["positive"] != bool(rows) or len(rows) != len(record["boxes"]):
            problems.append(f"{name}: label rows do not match the decision (positive needs a box, negative none)")
        for row, box in zip(rows, record["boxes"]):
            cx, cy, w, h = map(float, row[1:])
            x1, y1, x2, y2 = box["bbox_xyxy"]
            if row[0] != "0" or not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                problems.append(f"{name}: box outside the image or wrong class")
            restored = [(cx - w / 2) * width, (cy - h / 2) * height, (cx + w / 2) * width, (cy + h / 2) * height]
            if not all(0 <= v <= 1 for v in (cx, cy, w, h)) or max(abs(a - b) for a, b in zip(restored, box["bbox_xyxy"])) > 0.001:
                problems.append(f"{name}: YOLO row does not match the pixel box")
    if len(hashes) != len(manifest["images"]):
        problems.append("duplicate image hashes")
    on_disk = {p.resolve() for folder in ("images", "labels") for p in (output / folder).rglob("*") if p.is_file() and p.suffix in (".png", ".txt")}
    if on_disk != listed:
        problems.append("files on disk differ from the manifest")
    if problems:
        raise ValueError("; ".join(problems[:20]))
    result = dict(images=len(manifest["images"]), positives=sum(r["positive"] for r in manifest["images"]), negatives=sum(not r["positive"] for r in manifest["images"]), boxes=sum(len(r["boxes"]) for r in manifest["images"]))
    if ultralytics:
        result["ultralytics"] = ultralytics_check(output, manifest)
    return result


def ultralytics_check(output, manifest):
    """Load each split with the real Ultralytics dataset class and compare counts."""
    from ultralytics.data.dataset import YOLODataset
    from ultralytics.data.utils import check_det_dataset

    data = check_det_dataset(str(output / "dataset.yaml"))
    report = {}
    for key, split in (("train", "diag_train"), ("val", "diag_val")):
        dataset = YOLODataset(img_path=data[key], data=data, task="detect", imgsz=640, augment=False)
        records = [r for r in manifest["images"] if r["split"] == split]
        loaded_boxes = sum(len(label["cls"]) for label in dataset.labels)
        expected_boxes = sum(len(r["boxes"]) for r in records)
        if len(dataset.labels) != len(records) or loaded_boxes != expected_boxes:
            raise ValueError(f"Ultralytics loaded {len(dataset.labels)} images/{loaded_boxes} boxes for {split}, expected {len(records)}/{expected_boxes}")
        report[split] = dict(images=len(dataset.labels), boxes=loaded_boxes, corrupt=len(records) - len(dataset.labels))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "local-artifacts/nox-text-diagnostic",
                        help="new generated folder (default: local-artifacts/nox-text-diagnostic); never overwrites a set")
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--train", type=int, nargs=2, metavar=("POS", "NEG"), default=(100, 60))
    parser.add_argument("--val", type=int, nargs=2, metavar=("POS", "NEG"), default=(24, 16))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--ultralytics", action="store_true", help="also load the splits with Ultralytics")
    args = parser.parse_args()
    if not args.validate_only:
        print(json.dumps(build(args.output, args.seed, dict(diag_train=args.train, diag_val=args.val))))
    print(json.dumps(validate(args.output, args.ultralytics)))

"""Generate Kaggle writeup card (16:9 + 1:1) and 16:9 gallery charts with Pillow."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = "/mnt/c/Users/golub/Downloads/tsk/repo/assets"
os.makedirs(OUT, exist_ok=True)

# ---------- palette ----------
BG     = (15, 23, 42)      # slate-900
PANEL  = (30, 41, 59)      # slate-800
TEXT   = (226, 232, 240)   # slate-200
MUTED  = (148, 163, 184)   # slate-400
ACCENT = (56, 189, 248)    # sky-400
GOOD   = (52, 211, 153)    # emerald-400
BAD    = (248, 113, 113)   # red-400
AMBER  = (251, 191, 36)


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def rounded(d, xy, r, fill):
    d.rounded_rectangle(xy, radius=r, fill=fill)


def center(d, box, text, f, fill):
    x0, y0, x1, y1 = box
    bb = d.textbbox((0, 0), text, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x0 + (x1 - x0 - w) / 2 - bb[0], y0 + (y1 - y0 - h) / 2 - bb[1]),
           text, font=f, fill=fill)


# ============================================================
# 1) CARD 16:9  (1280x720)
# ============================================================
W, H = 1280, 720
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, 8], fill=ACCENT)

f_kicker = font(26, True)
f_title  = font(60, True)
f_sub    = font(30)
f_small  = font(22)
f_big    = font(66, True)

d.text((70, 70), "POSTGRESQL + JSONB  ·  DATA PIPELINE", font=f_kicker, fill=ACCENT)
d.text((70, 116), "Expand at 300M rows", font=f_title, fill=TEXT)
d.text((70, 196), "Chunked · Resumable · Bulk-load", font=f_sub, fill=MUTED)

panels = [
    ("3.3x", "faster on 1M rows", GOOD),
    ("22 MB", "peak client RAM", ACCENT),
    ("O(1)", "restart cost", AMBER),
]
px, py, pw, ph, gap = 70, 318, 360, 158, 30
for i, (big, label, col) in enumerate(panels):
    x = px + i * (pw + gap)
    rounded(d, [x, py, x + pw, py + ph], 18, PANEL)
    center(d, [x, py + 22, x + pw, py + 102], big, f_big, col)
    center(d, [x, py + 106, x + pw, py + 148], label, f_small, MUTED)

d.text((70, 552), "baseline 198.8 s", font=f_small, fill=BAD)
d.text((342, 552), "->", font=f_small, fill=MUTED)
d.text((400, 552), "optimized ~60 s", font=f_small, fill=GOOD)
d.text((70, 606), "symmetric-diff 0  ·  kill -9 resume 0 dup  ·  constant RSS",
       font=f_small, fill=MUTED)
d.text((W - 350, 606), "MEASURED PROCESSING TOTAL", font=font(18, True), fill=ACCENT)
img.save(os.path.join(OUT, "card_16x9.png"), "PNG")
img.save(os.path.join(OUT, "card_16x9.jpg"), "JPEG", quality=92)

# ============================================================
# 2) CARD 1:1  (1080x1080)
# ============================================================
S = 1080
img = Image.new("RGB", (S, S), BG)
d = ImageDraw.Draw(img)
d.rectangle([0, 0, S, 8], fill=ACCENT)

d.text((80, 80), "POSTGRESQL + JSONB", font=font(28, True), fill=ACCENT)
d.text((80, 120), "DATA PIPELINE", font=font(28, True), fill=ACCENT)

f_sq_title = font(72, True)
d.text((80, 196), "Expand at", font=f_sq_title, fill=TEXT)
d.text((80, 280), "300M rows", font=f_sq_title, fill=ACCENT)
d.text((80, 386), "Chunked · Resumable · Bulk-load", font=font(30), fill=MUTED)

# three stacked metric rows
rows = [
    ("3.3x", "faster on 1M rows", GOOD),
    ("22 MB", "peak client RAM", ACCENT),
    ("O(1)", "restart cost", AMBER),
]
ry, rh, rgap = 470, 132, 22
for i, (big, label, col) in enumerate(rows):
    y = ry + i * (rh + rgap)
    rounded(d, [80, y, S - 80, y + rh], 18, PANEL)
    d.text((120, y + 28), big, font=font(58, True), fill=col)
    d.text((400, y + 50), label, font=font(30), fill=TEXT)

# bottom comparison
d.text((80, 958), "baseline 198.8 s", font=font(24), fill=BAD)
d.text((330, 958), "->", font=font(24), fill=MUTED)
d.text((386, 958), "optimized ~60 s", font=font(24), fill=GOOD)
d.text((80, 1000), "symmetric-diff 0 · kill -9 resume 0 dup · constant RSS",
       font=font(20), fill=MUTED)
img.save(os.path.join(OUT, "card_1x1.png"), "PNG")
img.save(os.path.join(OUT, "card_1x1.jpg"), "JPEG", quality=92)

# ============================================================
# 3) GALLERY: baseline vs optimized  (1280x720, 16:9)
# ============================================================
W2, H2 = 1280, 720
img = Image.new("RGB", (W2, H2), BG)
d = ImageDraw.Draw(img)
d.text((60, 44), "1M rows — MEASURED PROCESSING TOTAL", font=font(36, True), fill=TEXT)
d.text((60, 92), "interleaved A/B, same warmed machine", font=font(23), fill=MUTED)

bars = [
    ("Baseline (one txn)", 198.75, BAD),
    ("Optimized 200k — run 1", 68.6, ACCENT),
    ("Optimized 200k — run 2", 58.4, GOOD),
    ("Optimized — hot cache", 34.5, GOOD),
]
lx, top, maxw, bh, vgap = 60, 170, 620, 74, 46
maxv = 200
for i, (label, val, col) in enumerate(bars):
    y = top + i * (bh + vgap)
    d.text((lx, y - 28), label, font=font(21), fill=TEXT)
    bw = int(maxw * val / maxv)
    rounded(d, [lx, y + 6, lx + bw, y + 6 + bh - 18], 8, col)
    d.text((lx + bw + 16, y + 10), f"{val:.1f} s", font=font(25, True), fill=col)

rx = 880
rounded(d, [rx, 170, W2 - 40, 596], 18, PANEL)
d.text((rx + 32, 196), "headline", font=font(20, True), fill=MUTED)
items = [("3.3x", "faster", GOOD), ("4.3x", "less RAM", ACCENT), ("0", "semantic diff", AMBER)]
yy = 250
for big, label, col in items:
    d.text((rx + 32, yy), big, font=font(44, True), fill=col)
    d.text((rx + 32, yy + 52), label, font=font(24), fill=TEXT)
    yy += 118
img.save(os.path.join(OUT, "gallery_benchmark.png"), "PNG")

# ============================================================
# 4) GALLERY: memory scaling  (1280x720, 16:9)
# ============================================================
W3, H3 = 1280, 720
img = Image.new("RGB", (W3, H3), BG)
d = ImageDraw.Draw(img)
d.text((60, 44), "Peak client RSS is independent of chunk size", font=font(34, True), fill=TEXT)
d.text((60, 90), "50k / 200k / 500k chunk rows — 1M source rows", font=font(22), fill=MUTED)

data = [("50k", 21.9, 38.0), ("200k", 21.9, 35.1), ("500k", 21.9, 34.5)]
bx0, by0, bw, bh = 150, 170, 210, 300
gap = 120
d.line([bx0 - 40, by0 + bh, bx0 + 3 * bw + 2 * gap, by0 + bh], fill=MUTED, width=2)
for i, (label, rss, wall) in enumerate(data):
    x = bx0 + i * (bw + gap)
    h = int(bh * rss / 30.0)
    rounded(d, [x, by0 + bh - h, x + bw, by0 + bh], 10, ACCENT)
    center(d, [x, by0 + bh - h - 40, x + bw, by0 + bh - h - 8], f"{rss} MB", font(23, True), ACCENT)
    center(d, [x, by0 + bh + 14, x + bw, by0 + bh + 48], f"{label} chunks", font(21), TEXT)
    center(d, [x, by0 + bh + 52, x + bw, by0 + bh + 82], f"wall {wall:.1f}s", font(18), MUTED)

d.text((60, 592), "Same 21.9 MB client footprint at every chunk size -> memory is bounded by",
       font=font(21), fill=MUTED)
d.text((60, 626), "chunk_rows, not by dataset size. Scales to 300M rows without RAM growth.",
       font=font(21), fill=MUTED)
img.save(os.path.join(OUT, "gallery_memory.png"), "PNG")

# ============================================================
# 5) GALLERY: architecture  (1280x720, 16:9)
# ============================================================
W4, H4 = 1280, 720
img = Image.new("RGB", (W4, H4), BG)
d = ImageDraw.Draw(img)
d.text((60, 44), "Chunked, resumable expansion", font=font(36, True), fill=TEXT)
d.text((60, 92), "checkpoint committed in the SAME transaction as the data",
       font=font(22), fill=MUTED)

# source
rounded(d, [60, 175, 320, 330], 14, PANEL)
center(d, [60, 190, 320, 236], "raw_data (JSONB)", font(21, True), TEXT)
center(d, [60, 236, 320, 276], "2 GB · 1M rows", font(18), MUTED)
center(d, [60, 272, 320, 310], "jsonb_to_record", font(17), ACCENT)

for i in range(3):
    y = 175 + i * 120
    d.line([320, y + 48, 400, y + 48], fill=MUTED, width=3)

chunks = [
    "chunk 1  raw_id 1..200k",
    "chunk 2  raw_id 200k..400k",
    "chunk 3  ...",
]
for i, c in enumerate(chunks):
    y = 175 + i * 120
    rounded(d, [400, y, 860, y + 100], 12, PANEL)
    center(d, [400, y + 12, 860, y + 48], c, font(21, True), ACCENT)
    center(d, [400, y + 48, 860, y + 88],
           "BEGIN > stage > delete+insert > checkpoint > COMMIT", font(16), MUTED)

# destinations
rounded(d, [920, 175, 1220, 475], 14, PANEL)
d.text((945, 196), "destinations", font=font(21, True), fill=TEXT)
for i, t in enumerate(["table1 (1M)", "table2 (2.3M)", "table5 (1M)", "table6 (1M)"]):
    d.text((950, 238 + i * 44), "• " + t, font=font(20), fill=MUTED)
d.text((945, 420), "table3/4 = refs", font=font(18), fill=ACCENT)

# guarantees strip
rounded(d, [60, 560, 1220, 660], 14, (20, 30, 48))
d.text((90, 582), "Guarantees", font=font(21, True), fill=GOOD)
d.text((90, 620), "checkpoint never ahead of data · chunks idempotent (advisory lock) · "
       "index state durable · verify built-in", font=font(18), fill=MUTED)
img.save(os.path.join(OUT, "gallery_architecture.png"), "PNG")

print("WROTE:")
for f in ["card_16x9.png", "card_16x9.jpg", "card_1x1.png", "card_1x1.jpg",
          "gallery_benchmark.png", "gallery_memory.png", "gallery_architecture.png"]:
    p = os.path.join(OUT, f)
    im = Image.open(p)
    print(f"{f:32s} {im.size[0]}x{im.size[1]}  ratio={im.size[0]/im.size[1]:.4f}  {os.path.getsize(p)} B")

from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
from flask_cors import CORS
import io, zipfile, os
import requests as http_requests

app = Flask(__name__)
CORS(app)

W, H = 1080, 1350
FONT_PATH = "/usr/share/fonts/truetype/poppins/"

def font(bold=False, size=48):
    name = "Poppins-ExtraBold.ttf" if bold else "Poppins-Regular.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_PATH, name), size)
    except:
        return ImageFont.load_default()

TEXT_DARK    = (20, 20, 20)
TEXT_REGULAR = (50, 50, 50)
TEXT_MUTED   = (160, 160, 160)
ACCENT       = (180, 145, 60)
BG_CAPA      = (255, 255, 255)

TEXT_ZONE_TOP    = 290
TEXT_ZONE_BOTTOM = 1170
TEXT_ZONE_LEFT   = 100
TEXT_ZONE_RIGHT  = W - 80

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.jpg")

def load_template(url=None):
    if url and url.strip():
        try:
            resp = http_requests.get(url.strip(), timeout=10)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            return img.resize((W, H), Image.LANCZOS)
        except:
            pass
    if os.path.exists(TEMPLATE_PATH):
        return Image.open(TEMPLATE_PATH).convert("RGB").resize((W, H), Image.LANCZOS)
    return Image.new("RGB", (W, H), (255, 255, 255))

def line_width(draw, parts, size_reg, size_bold):
    total = 0
    for word, bold in parts:
        f = font(bold, size_bold if bold else size_reg)
        total += draw.textbbox((0, 0), word + " ", font=f)[2]
    return total

def draw_rich_text(draw, text, x, y, size_reg=52, size_bold=52,
                   color_reg=None, color_bold=None, max_w=None, center=False):
    if color_reg is None:
        color_reg = TEXT_REGULAR
    if color_bold is None:
        color_bold = TEXT_DARK
    if max_w is None:
        max_w = TEXT_ZONE_RIGHT - x

    text = text.replace("\\n", "\n")
    line_h = int(font(False, size_reg).getbbox("A")[3] * 1.2)
    cy = y

    for para in text.split("\n"):
        if para.strip() == "":
            cy += int(line_h * 0.55)
            continue

        tokens = []
        rem = para
        while "**" in rem:
            idx = rem.index("**")
            if idx > 0:
                tokens.append((rem[:idx], False))
            rem = rem[idx + 2:]
            end = rem.index("**") if "**" in rem else len(rem)
            tokens.append((rem[:end], True))
            rem = rem[end + 2:] if "**" in rem else ""
        if rem:
            tokens.append((rem, False))
        if not tokens:
            tokens = [(para, False)]

        words = []
        for txt, bold in tokens:
            for w in txt.split(" "):
                if w:
                    words.append((w, bold))

        lines, cur, cw = [], [], 0
        for word, bold in words:
            f = font(bold, size_bold if bold else size_reg)
            bw = draw.textbbox((0, 0), word + " ", font=f)[2]
            if cw + bw > max_w and cur:
                lines.append(cur)
                cur = [(word, bold)]
                cw = bw
            else:
                cur.append((word, bold))
                cw += bw
        if cur:
            lines.append(cur)

        for line in lines:
            lw = line_width(draw, line, size_reg, size_bold)
            cx = x + (max_w - lw) // 2 if center else x
            for word, bold in line:
                f = font(bold, size_bold if bold else size_reg)
                color = color_bold if bold else color_reg
                draw.text((cx, cy), word + " ", font=f, fill=color)
                cx += draw.textbbox((0, 0), word + " ", font=f)[2]
            cy += line_h
        cy += int(line_h * 0.1)

    return cy

def measure_rich(text, size_reg, size_bold, max_w):
    if not text:
        return 0
    text = text.replace("\\n", "\n")
    dummy = Image.new("RGB", (1, 1))
    dd = ImageDraw.Draw(dummy)
    line_h = int(font(False, size_reg).getbbox("A")[3] * 1.2)
    total = 0
    for para in text.split("\n"):
        if para.strip() == "":
            total += int(line_h * 0.55)
            continue
        tokens = []
        rem = para
        while "**" in rem:
            idx = rem.index("**")
            if idx > 0:
                tokens.append((rem[:idx], False))
            rem = rem[idx + 2:]
            end = rem.index("**") if "**" in rem else len(rem)
            tokens.append((rem[:end], True))
            rem = rem[end + 2:] if "**" in rem else ""
        if rem:
            tokens.append((rem, False))
        if not tokens:
            tokens = [(para, False)]
        words = []
        for txt, bold in tokens:
            for w in txt.split(" "):
                if w:
                    words.append((w, bold))
        lines, cur, cw = [], [], 0
        for word, bold in words:
            f = font(bold, size_bold if bold else size_reg)
            bw = dd.textbbox((0, 0), word + " ", font=f)[2]
            if cw + bw > max_w and cur:
                lines.append(cur)
                cur = [(word, bold)]
                cw = bw
            else:
                cur.append((word, bold))
                cw += bw
        if cur:
            lines.append(cur)
        total += len(lines) * line_h + int(line_h * 0.1)
    return total

def slide_capa(data):
    imagem_url = data.get("imagem_url", "").strip()

    if imagem_url:
        try:
            resp = http_requests.get(imagem_url, timeout=10)
            resp.raise_for_status()
            bg = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            ratio = max(W / bg.width, H / bg.height)
            nw, nh = int(bg.width * ratio), int(bg.height * ratio)
            bg = bg.resize((nw, nh), Image.LANCZOS)
            l, t = (nw - W) // 2, (nh - H) // 2
            bg = bg.crop((l, t, l + W, t + H))
            img = bg.convert("RGBA")
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            for yy in range(H):
                alpha = int(min(215, (yy / H) * 270))
                d.line([(0, yy), (W, yy)], fill=(0, 0, 0, alpha))
            img = Image.alpha_composite(img, ov).convert("RGB")
            tc = (255, 255, 255)
            ts = (210, 210, 210)
            acc = (255, 200, 80)
        except:
            img = load_template()
            tc = (20, 20, 20)
            ts = (80, 80, 80)
            acc = ACCENT
    else:
        img = load_template()
        tc = (20, 20, 20)
        ts = (80, 80, 80)
        acc = ACCENT

    draw = ImageDraw.Draw(img)
    pad = TEXT_ZONE_LEFT
    max_w = W - pad * 2

    tag = data.get("tag", "").upper()
    titulo = data.get("titulo", "")
    sub = data.get("subtitulo", "")

    tag_h    = int(font(True, 30).getbbox("A")[3] * 1.5) + 20 if tag else 0
    titulo_h = measure_rich(titulo, 80, 80, max_w)
    sub_h    = measure_rich(sub, 44, 44, max_w) + 50 if sub else 0

    total_h = tag_h + titulo_h + sub_h
    cy = H - total_h - 200

    if tag:
        f_tag = font(True, 30)
        tag_w = draw.textbbox((0, 0), tag, font=f_tag)[2]
        draw.text((W // 2 - tag_w // 2, cy), tag, font=f_tag, fill=acc)
        cy += tag_h

    cy = draw_rich_text(draw, titulo, pad, cy,
                        size_reg=80, size_bold=80,
                        color_reg=tc, color_bold=tc,
                        max_w=max_w, center=True)

    if sub:
        draw_rich_text(draw, sub, pad, cy + 50,
                       size_reg=44, size_bold=44,
                       color_reg=ts, color_bold=ts,
                       max_w=max_w, center=True)

    handle = data.get("handle", "")
    if handle:
        f = font(False, 30)
        bw = draw.textbbox((0, 0), handle, font=f)[2]
        draw.text((W // 2 - bw // 2, H - 80), handle, font=f, fill=(160, 160, 160))

    return img

def slide_conteudo(data):
    img = load_template(data.get("layout_url", ""))
    draw = ImageDraw.Draw(img)
    draw_rich_text(draw, data.get("texto", ""),
                   TEXT_ZONE_LEFT, TEXT_ZONE_TOP,
                   size_reg=52, size_bold=52,
                   color_reg=TEXT_REGULAR, color_bold=TEXT_DARK,
                   max_w=TEXT_ZONE_RIGHT - TEXT_ZONE_LEFT)
    return img

def slide_cta(data):
    img = load_template(data.get("layout_url", ""))
    draw = ImageDraw.Draw(img)
    draw_rich_text(draw, data.get("texto", ""),
                   TEXT_ZONE_LEFT, TEXT_ZONE_TOP,
                   size_reg=52, size_bold=52,
                   color_reg=TEXT_REGULAR, color_bold=TEXT_DARK,
                   max_w=TEXT_ZONE_RIGHT - TEXT_ZONE_LEFT)
    return img

RENDERERS = {"capa": slide_capa, "conteudo": slide_conteudo, "cta": slide_cta}

def render_slide(data):
    return RENDERERS.get(data.get("tipo", "conteudo"), slide_conteudo)(data)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/gerar", methods=["POST"])
def gerar():
    body = request.get_json()
    if not body or "slides" not in body:
        return jsonify({"erro": "Campo 'slides' obrigatório"}), 400
    slides = body["slides"][:10]
    handle = body.get("handle", "")
    for s in slides:
        if "handle" not in s:
            s["handle"] = handle
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, slide in enumerate(slides):
            img = render_slide(slide)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            buf.seek(0)
            zf.writestr(f"slide_{i+1:02d}.png", buf.read())
    zip_buf.seek(0)
    return send_file(zip_buf, mimetype="application/zip",
                     as_attachment=True, download_name="carrossel.zip")

@app.route("/slide", methods=["POST"])
def slide_unico():
    body = request.get_json()
    if not body:
        return jsonify({"erro": "Body JSON obrigatório"}), 400
    img = render_slide(body)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

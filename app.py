from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import io, zipfile, os
import requests as http_requests

app = Flask(__name__)

# ─── DIMENSÕES ───────────────────────────────────────────────────────────────
W, H = 1080, 1350

# ─── FONTES ──────────────────────────────────────────────────────────────────
FONT_PATH = "/usr/share/fonts/truetype/dejavu/"

def font(bold=False, size=48):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_PATH, name), size)
    except:
        return ImageFont.load_default()

# ─── CORES ───────────────────────────────────────────────────────────────────
TEXT_DARK    = (20, 20, 20)
TEXT_REGULAR = (50, 50, 50)
TEXT_MUTED   = (160, 160, 160)
ACCENT       = (180, 145, 60)
BG_CAPA      = (15, 15, 15)

# ─── ZONA DE TEXTO DO TEMPLATE ───────────────────────────────────────────────
# O template tem header ~160px e rodapé ~170px
TEXT_ZONE_TOP    = 290   # onde o texto começa
TEXT_ZONE_BOTTOM = 1170  # onde o texto termina (antes do handle)
TEXT_ZONE_LEFT   = 100
TEXT_ZONE_RIGHT  = W - 80

# ─── TEMPLATE BASE ───────────────────────────────────────────────────────────
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.jpg")

def load_template(url=None):
    """Carrega template do disco ou de uma URL. Retorna PIL Image."""
    if url and url.strip():
        try:
            resp = http_requests.get(url.strip(), timeout=10)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            return img.resize((W, H), Image.LANCZOS)
        except:
            pass  # fallback para template local
    if os.path.exists(TEMPLATE_PATH):
        return Image.open(TEMPLATE_PATH).convert("RGB").resize((W, H), Image.LANCZOS)
    # Último fallback: branco puro
    return Image.new("RGB", (W, H), (255, 255, 255))

# ─── UTILITÁRIOS DE TEXTO ────────────────────────────────────────────────────

def line_width(draw, parts, size_reg, size_bold):
    """Calcula largura total de uma linha de partes (word, bold)."""
    total = 0
    for word, bold in parts:
        f = font(bold, size_bold if bold else size_reg)
        total += draw.textbbox((0,0), word+" ", font=f)[2]
    return total

def draw_rich_text(draw, text, x, y, size_reg=52, size_bold=52,
                   color_reg=None, color_bold=None, max_w=None, center=False):
    """
    Renderiza texto com suporte a **bold** e quebras de linha \\n.
    Se center=True, centraliza cada linha dentro de max_w.
    Retorna y final.
    """
    if color_reg  is None: color_reg  = TEXT_REGULAR
    if color_bold is None: color_bold = TEXT_DARK
    if max_w      is None: max_w      = TEXT_ZONE_RIGHT - x

    line_h = int(font(False, size_reg).getbbox("A")[3] * 1.2)
    cy = y

    for para in text.split("\n"):
        if para.strip() == "":
            cy += int(line_h * 0.55)
            continue

        # Parse **bold**
        tokens = []
        rem = para
        while "**" in rem:
            idx = rem.index("**")
            if idx > 0:
                tokens.append((rem[:idx], False))
            rem = rem[idx+2:]
            end = rem.index("**") if "**" in rem else len(rem)
            tokens.append((rem[:end], True))
            rem = rem[end+2:] if "**" in rem else ""
        if rem:
            tokens.append((rem, False))
        if not tokens:
            tokens = [(para, False)]

        # Tokeniza palavras
        words = []
        for txt, bold in tokens:
            for w in txt.split(" "):
                if w:
                    words.append((w, bold))

        # Word-wrap
        lines, cur, cw = [], [], 0
        for word, bold in words:
            f = font(bold, size_bold if bold else size_reg)
            bw = draw.textbbox((0,0), word+" ", font=f)[2]
            if cw + bw > max_w and cur:
                lines.append(cur); cur = [(word,bold)]; cw = bw
            else:
                cur.append((word,bold)); cw += bw
        if cur:
            lines.append(cur)

        # Renderiza linhas
        for line in lines:
            lw = line_width(draw, line, size_reg, size_bold)
            cx = x + (max_w - lw) // 2 if center else x
            for word, bold in line:
                f = font(bold, size_bold if bold else size_reg)
                color = color_bold if bold else color_reg
                draw.text((cx, cy), word+" ", font=f, fill=color)
                cx += draw.textbbox((0,0), word+" ", font=f)[2]
            cy += line_h
        cy += int(line_h * 0.1)

    return cy

# ─── SLIDES ──────────────────────────────────────────────────────────────────

def slide_capa(data):
    imagem_url = data.get("imagem_url", "").strip()

    if imagem_url:
        try:
            resp = http_requests.get(imagem_url, timeout=10)
            resp.raise_for_status()
            bg = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            ratio = max(W / bg.width, H / bg.height)
            nw, nh = int(bg.width*ratio), int(bg.height*ratio)
            bg = bg.resize((nw, nh), Image.LANCZOS)
            l, t = (nw-W)//2, (nh-H)//2
            bg = bg.crop((l, t, l+W, t+H))
            img = bg.convert("RGBA")
            ov = Image.new("RGBA", (W,H), (0,0,0,0))
            d = ImageDraw.Draw(ov)
            for yy in range(H):
                alpha = int(min(215, (yy/H)*270))
                d.line([(0,yy),(W,yy)], fill=(0,0,0,alpha))
            img = Image.alpha_composite(img, ov).convert("RGB")
        except:
            img = Image.new("RGB", (W, H), BG_CAPA)
    else:
        img = Image.new("RGB", (W, H), BG_CAPA)

    draw = ImageDraw.Draw(img)
    tc = (255,255,255); ts = (210,210,210)
    acc = (255,200,80) if imagem_url else ACCENT
    pad = TEXT_ZONE_LEFT
    max_w = W - pad * 2

    # Mede altura total do bloco para centralizar verticalmente
    tag = data.get("tag","").upper()
    titulo = data.get("titulo","")
    sub = data.get("subtitulo","")

    def measure_rich(text, size_reg, size_bold):
        if not text: return 0
        dummy = Image.new("RGB", (1,1))
        dd = ImageDraw.Draw(dummy)
        line_h = int(font(False, size_reg).getbbox("A")[3] * 1.55)
        total = 0
        for para in text.split("\n"):
            if para.strip() == "":
                total += int(line_h * 0.55)
                continue
            tokens = []
            rem = para
            while "**" in rem:
                idx = rem.index("**")
                if idx > 0: tokens.append((rem[:idx], False))
                rem = rem[idx+2:]
                end = rem.index("**") if "**" in rem else len(rem)
                tokens.append((rem[:end], True))
                rem = rem[end+2:] if "**" in rem else ""
            if rem: tokens.append((rem, False))
            if not tokens: tokens = [(para, False)]
            words = []
            for txt, bold in tokens:
                for w in txt.split(" "):
                    if w: words.append((w, bold))
            lines, cur, cw = [], [], 0
            for word, bold in words:
                f = font(bold, size_bold if bold else size_reg)
                bw = dd.textbbox((0,0), word+" ", font=f)[2]
                if cw + bw > max_w and cur:
                    lines.append(cur); cur = [(word,bold)]; cw = bw
                else:
                    cur.append((word,bold)); cw += bw
            if cur: lines.append(cur)
            total += len(lines) * line_h + int(line_h * 0.1)
        return total

    tag_h    = int(font(True,30).getbbox("A")[3] * 1.5) + 20 if tag else 0
    titulo_h = measure_rich(titulo, 82, 82)
    sub_h    = measure_rich(sub, 44, 44) + 50 if sub else 0

    total_h = tag_h + titulo_h + sub_h
    cy = (H - total_h) // 2

    # Desenha tag
    if tag:
        f_tag = font(True, 30)
        tag_w = draw.textbbox((0,0), tag, font=f_tag)[2]
        draw.text((W//2 - tag_w//2, cy), tag, font=f_tag, fill=acc)
        cy += tag_h

    # Desenha título
    cy = draw_rich_text(draw, titulo, pad, cy,
                        size_reg=96, size_bold=900,
                        color_reg=tc, color_bold=tc,
                        max_w=max_w, center=True)

    # Desenha subtítulo
    if sub:
        draw_rich_text(draw, sub, pad, cy + 50,
                       size_reg=44, size_bold=44,
                       color_reg=ts, color_bold=ts,
                       max_w=max_w, center=True)

    # Handle
    handle = data.get("handle","")
    if handle:
        f = font(False, 30)
        bw = draw.textbbox((0,0), handle, font=f)[2]
        draw.text((W//2 - bw//2, H-80), handle, font=f, fill=(180,180,180))

    return img


def slide_conteudo(data):
    template_url = data.get("layout_url", "")
    img = load_template(template_url)
    draw = ImageDraw.Draw(img)

    draw_rich_text(draw, data.get("texto",""),
                   TEXT_ZONE_LEFT, TEXT_ZONE_TOP,
                   size_reg=52, size_bold=52,
                   color_reg=TEXT_REGULAR, color_bold=TEXT_DARK,
                   max_w=TEXT_ZONE_RIGHT - TEXT_ZONE_LEFT)
    return img


def slide_cta(data):
    template_url = data.get("layout_url", "")
    img = load_template(template_url)
    draw = ImageDraw.Draw(img)

    draw_rich_text(draw, data.get("texto",""),
                   TEXT_ZONE_LEFT, TEXT_ZONE_TOP,
                   size_reg=52, size_bold=52,
                   color_reg=TEXT_REGULAR, color_bold=TEXT_DARK,
                   max_w=TEXT_ZONE_RIGHT - TEXT_ZONE_LEFT)
    return img


RENDERERS = {"capa": slide_capa, "conteudo": slide_conteudo, "cta": slide_cta}

def render_slide(data):
    return RENDERERS.get(data.get("tipo","conteudo"), slide_conteudo)(data)

# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/gerar", methods=["POST"])
def gerar():
    body = request.get_json()
    if not body or "slides" not in body:
        return jsonify({"erro": "Campo 'slides' obrigatório"}), 400

    slides = body["slides"][:10]
    handle = body.get("handle","")
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

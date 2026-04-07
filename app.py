from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile
import os
import textwrap

app = Flask(__name__)

# ─── CONFIGURAÇÕES VISUAIS ───────────────────────────────────────────────────
W, H = 1080, 1080
FONT_PATH = "/usr/share/fonts/truetype/dejavu/"

# Paleta
COLOR_BG       = "#FFFFFF"
COLOR_BG_CAPA  = "#0D0D0D"
COLOR_BG_CTA   = "#1A1A2E"
COLOR_ACCENT   = "#FF3C5F"
COLOR_TEXT     = "#1A1A1A"
COLOR_TEXT_INV = "#FFFFFF"
COLOR_MUTED    = "#888888"
COLOR_NUM      = "#F0F0F0"

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def load_font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONT_PATH, name), size)
    except:
        return ImageFont.load_default()

def draw_multiline(draw, text, x, y, font, color, max_width, line_spacing=1.3):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_h = draw.textbbox((0, 0), "A", font=font)[3] * line_spacing
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_h), line, font=font, fill=color)
    return y + len(lines) * line_h

def add_accent_bar(draw, x, y, width=60, height=6, color=COLOR_ACCENT):
    draw.rectangle([x, y, x + width, y + height], fill=hex_to_rgb(color))

def add_handle(draw, handle, font, color):
    if handle:
        bbox = draw.textbbox((0, 0), handle, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((W - tw - 60, H - 60), handle, font=font, fill=color)

# ─── SLIDES ──────────────────────────────────────────────────────────────────

def slide_capa(data):
    img = Image.new("RGB", (W, H), hex_to_rgb(COLOR_BG_CAPA))
    draw = ImageDraw.Draw(img)

    # Accent top bar
    draw.rectangle([0, 0, W, 10], fill=hex_to_rgb(COLOR_ACCENT))

    # Etiqueta (tag)
    tag = data.get("tag", "").upper()
    if tag:
        font_tag = load_font("DejaVuSans-Bold.ttf", 28)
        draw.text((80, 120), tag, font=font_tag, fill=hex_to_rgb(COLOR_ACCENT))

    # Título principal
    titulo = data.get("titulo", "")
    font_titulo = load_font("DejaVuSans-Bold.ttf", 88)
    draw_multiline(draw, titulo, 80, 200, font_titulo, hex_to_rgb(COLOR_TEXT_INV), W - 160, 1.2)

    # Subtítulo
    sub = data.get("subtitulo", "")
    if sub:
        font_sub = load_font("DejaVuSans.ttf", 42)
        draw_multiline(draw, sub, 80, 700, font_sub, hex_to_rgb(COLOR_MUTED), W - 160, 1.4)

    # Accent bottom bar
    add_accent_bar(draw, 80, H - 130)

    # Handle
    add_handle(draw, data.get("handle", ""), load_font("DejaVuSans.ttf", 26), hex_to_rgb(COLOR_MUTED))

    return img


def slide_conteudo(data):
    img = Image.new("RGB", (W, H), hex_to_rgb(COLOR_BG))
    draw = ImageDraw.Draw(img)

    # Número do slide ao fundo (decorativo)
    numero = data.get("numero", "")
    if numero:
        font_num = load_font("DejaVuSans-Bold.ttf", 380)
        bbox = draw.textbbox((0, 0), numero, font=font_num)
        nw = bbox[2] - bbox[0]
        draw.text((W - nw - 20, H - 360), numero, font=font_num, fill=hex_to_rgb(COLOR_NUM))

    # Accent bar
    add_accent_bar(draw, 80, 100)

    # Título
    titulo = data.get("titulo", "")
    font_titulo = load_font("DejaVuSans-Bold.ttf", 72)
    y = draw_multiline(draw, titulo, 80, 140, font_titulo, hex_to_rgb(COLOR_TEXT), W - 200, 1.25)

    # Texto
    texto = data.get("texto", "")
    if texto:
        font_texto = load_font("DejaVuSans.ttf", 46)
        draw_multiline(draw, texto, 80, y + 60, font_texto, hex_to_rgb(COLOR_TEXT), W - 160, 1.6)

    # Handle
    add_handle(draw, data.get("handle", ""), load_font("DejaVuSans.ttf", 26), hex_to_rgb(COLOR_MUTED))

    return img


def slide_cta(data):
    img = Image.new("RGB", (W, H), hex_to_rgb(COLOR_BG_CTA))
    draw = ImageDraw.Draw(img)

    # Accent bar topo
    draw.rectangle([0, 0, W, 10], fill=hex_to_rgb(COLOR_ACCENT))

    # Ícone / label
    label = data.get("label", "GOSTOU?").upper()
    font_label = load_font("DejaVuSans-Bold.ttf", 32)
    draw.text((80, 160), label, font=font_label, fill=hex_to_rgb(COLOR_ACCENT))

    # Título CTA
    titulo = data.get("titulo", "")
    font_titulo = load_font("DejaVuSans-Bold.ttf", 78)
    y = draw_multiline(draw, titulo, 80, 240, font_titulo, hex_to_rgb(COLOR_TEXT_INV), W - 160, 1.2)

    # Botão / instrução
    cta = data.get("cta", "")
    if cta:
        # Caixa do botão
        pad_x, pad_y = 50, 25
        font_cta = load_font("DejaVuSans-Bold.ttf", 44)
        bbox = draw.textbbox((0, 0), cta, font=font_cta)
        bw = bbox[2] - bbox[0] + pad_x * 2
        bh = bbox[3] - bbox[1] + pad_y * 2
        bx, by = 80, y + 80
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12, fill=hex_to_rgb(COLOR_ACCENT))
        draw.text((bx + pad_x, by + pad_y), cta, font=font_cta, fill=hex_to_rgb(COLOR_TEXT_INV))

    # Handle
    add_handle(draw, data.get("handle", ""), load_font("DejaVuSans.ttf", 26), hex_to_rgb(COLOR_MUTED))

    return img

# ─── ROTEADOR DE TIPOS ───────────────────────────────────────────────────────

SLIDE_RENDERERS = {
    "capa":     slide_capa,
    "conteudo": slide_conteudo,
    "cta":      slide_cta,
}

def render_slide(slide_data):
    tipo = slide_data.get("tipo", "conteudo")
    renderer = SLIDE_RENDERERS.get(tipo, slide_conteudo)
    return renderer(slide_data)

# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/gerar", methods=["POST"])
def gerar():
    body = request.get_json()
    if not body or "slides" not in body:
        return jsonify({"erro": "Campo 'slides' obrigatório"}), 400

    slides = body["slides"][:10]  # máximo 10 lâminas
    handle = body.get("handle", "")

    # Injeta handle em cada slide se não vier explícito
    for s in slides:
        if "handle" not in s:
            s["handle"] = handle

    images = []
    for slide in slides:
        img = render_slide(slide)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        images.append(buf)

    # ZIP com todos os PNGs
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img_buf in enumerate(images):
            zf.writestr(f"slide_{i+1:02d}.png", img_buf.read())
    zip_buf.seek(0)

    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="carrossel.zip"
    )


@app.route("/slide", methods=["POST"])
def slide_unico():
    """Gera um único slide. Útil para preview."""
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

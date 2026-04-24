from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from playwright.sync_api import sync_playwright
import io, zipfile, os, base64, re
import requests as http_requests

app = Flask(__name__)
CORS(app)

W, H = 1080, 1350
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.jpg")

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def load_image_as_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = path.split(".")[-1].lower()
        mime = "image/jpeg" if ext in ("jpg","jpeg") else "image/png"
        return f"data:{mime};base64,{data}"
    return None

def fetch_image_as_base64(url):
    try:
        resp = http_requests.get(url.strip(), timeout=10)
        resp.raise_for_status()
        ct = resp.headers.get("content-type","image/jpeg").split(";")[0]
        data = base64.b64encode(resp.content).decode()
        return f"data:{ct};base64,{data}"
    except:
        return None

def parse_rich(text):
    """Converte **bold** em <strong> e \n em <br>."""
    text = text.replace("\\n", "\n")
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = text.replace("\n", "<br>")
    return text

# ─── HTML TEMPLATES ──────────────────────────────────────────────────────────

def html_capa(data, template_b64):
    imagem_url = data.get("imagem_url", "").strip()
    tag        = data.get("tag", "").upper()
    titulo     = parse_rich(data.get("titulo", ""))
    sub        = data.get("subtitulo", "")
    handle     = data.get("handle", "")

    # Decide fundo e cores
    if imagem_url:
        img_b64 = fetch_image_as_base64(imagem_url)
        if img_b64:
            bg_css = f"background-image: url('{img_b64}'); background-size: cover; background-position: center;"
            overlay = """
                <div style="position:absolute;inset:0;
                    background: linear-gradient(to bottom,
                        rgba(0,0,0,0.0) 0%,
                        rgba(0,0,0,0.55) 50%,
                        rgba(0,0,0,0.82) 100%);
                    z-index:1"></div>
            """
            text_color = "#ffffff"
            sub_color  = "rgba(255,255,255,0.80)"
            acc_color  = "#ffc850"
            handle_color = "rgba(255,255,255,0.55)"
            position_css = "justify-content: flex-end; padding-bottom: 200px;"
        else:
            img_b64 = None
    
    if not imagem_url or not img_b64 if imagem_url else True:
        if template_b64:
            bg_css = f"background-image: url('{template_b64}'); background-size: cover; background-position: center;"
        else:
            bg_css = "background: #ffffff;"
        overlay = ""
        text_color = "#141414"
        sub_color  = "#444444"
        acc_color  = "#b4913c"
        handle_color = "#aaaaaa"
        position_css = "justify-content: center;"

    tag_html = f'<div style="font-size:30px;font-weight:800;color:{acc_color};letter-spacing:0.08em;margin-bottom:20px">{tag}</div>' if tag else ""
    sub_html = f'<div style="font-size:44px;font-weight:400;color:{sub_color};margin-top:40px;line-height:1.4">{parse_rich(sub)}</div>' if sub else ""
    handle_html = f'<div style="position:absolute;bottom:70px;left:0;right:0;text-align:center;font-size:30px;color:{handle_color};z-index:10">{handle}</div>' if handle else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{W}px; height:{H}px; overflow:hidden; font-family:'Poppins',sans-serif; }}
.slide {{
    width:{W}px; height:{H}px;
    position:relative;
    {bg_css}
    display:flex;
    flex-direction:column;
    align-items:center;
    {position_css}
}}
.content {{
    position:relative;
    z-index:10;
    width:100%;
    padding:0 100px;
    text-align:center;
}}
.titulo {{
    font-size:80px;
    font-weight:800;
    color:{text_color};
    line-height:1.15;
}}
</style>
</head>
<body>
<div class="slide">
    {overlay}
    <div class="content">
        {tag_html}
        <div class="titulo">{titulo}</div>
        {sub_html}
    </div>
    {handle_html}
</div>
</body>
</html>"""


def html_conteudo(data, template_b64):
    texto  = parse_rich(data.get("texto", ""))
    handle = data.get("handle", "")

    if template_b64:
        bg_css = f"background-image: url('{template_b64}'); background-size: cover; background-position: center;"
    else:
        bg_css = "background: #ffffff;"

    handle_html = f'<div class="handle">{handle}</div>' if handle else ""

    # Zona de texto: top=290, bottom=1170 => height=880, center=730
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{W}px; height:{H}px; overflow:hidden; font-family:'Poppins',sans-serif; }}
.slide {{
    width:{W}px; height:{H}px;
    position:relative;
    {bg_css}
}}
.zone {{
    position:absolute;
    top:290px;
    bottom:180px;
    left:100px;
    right:80px;
    display:flex;
    align-items:center;
}}
.texto {{
    font-size:52px;
    font-weight:400;
    color:#323232;
    line-height:1.5;
}}
.texto strong {{
    font-weight:800;
    color:#141414;
}}
.handle {{
    position:absolute;
    bottom:70px;
    left:0; right:0;
    text-align:center;
    font-size:28px;
    color:#aaaaaa;
}}
</style>
</head>
<body>
<div class="slide">
    <div class="zone">
        <div class="texto">{texto}</div>
    </div>
    {handle_html}
</div>
</body>
</html>"""


RENDERERS_HTML = {
    "capa":     html_capa,
    "conteudo": html_conteudo,
    "cta":      html_conteudo,
}

# ─── SCREENSHOT ──────────────────────────────────────────────────────────────

def render_html_to_png(html):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": W, "height": H})
        page.set_content(html, wait_until="networkidle")
        png = page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H})
        browser.close()
    return png

# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/gerar", methods=["POST"])
def gerar():
    body = request.get_json()
    if not body or "slides" not in body:
        return jsonify({"erro": "Campo 'slides' obrigatório"}), 400

    template_b64 = load_image_as_base64(TEMPLATE_PATH)
    slides  = body["slides"][:10]
    handle  = body.get("handle", "")
    for s in slides:
        if "handle" not in s:
            s["handle"] = handle

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, slide in enumerate(slides):
            tipo     = slide.get("tipo", "conteudo")
            renderer = RENDERERS_HTML.get(tipo, html_conteudo)
            html     = renderer(slide, template_b64)
            png      = render_html_to_png(html)
            zf.writestr(f"slide_{i+1:02d}.png", png)
    zip_buf.seek(0)

    return send_file(zip_buf, mimetype="application/zip",
                     as_attachment=True, download_name="carrossel.zip")

@app.route("/slide", methods=["POST"])
def slide_unico():
    body = request.get_json()
    if not body:
        return jsonify({"erro": "Body JSON obrigatório"}), 400
    template_b64 = load_image_as_base64(TEMPLATE_PATH)
    tipo     = body.get("tipo", "conteudo")
    renderer = RENDERERS_HTML.get(tipo, html_conteudo)
    html     = renderer(body, template_b64)
    png      = render_html_to_png(html)
    return send_file(io.BytesIO(png), mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

"""Renderiza os cards de um post (arquivos .dc.html do canvas) em JPEG 1080x1350 e monta fila/<CÓDIGO>/.

Uso:
  python3 scripts/renderizar.py blobs <pasta_canvas> <arquivo.dc.html>...
      -> imprime os ids de /_blob/<id> usados (para baixar do canvas antes de renderizar)
  python3 scripts/renderizar.py render <CÓDIGO> <pasta_canvas> <pasta_blobs> <arquivo.dc.html>...
      -> grava fila/<CÓDIGO>/01.jpg, 02.jpg... na ordem dada e cria post.json com aprovado = false
         (se ainda não existir). O sincronizar.py depois preenche legenda, alt e horário.

<pasta_canvas> tem os .dc.html (ex.: project/ baixado do canvas).
<pasta_blobs> tem os blobs baixados, nomeados <id>.<ext> (png/jpg/webp).
Fonte Montserrat local (scripts/fontes), sem depender da internet.
"""
import os, sys

# scripts/token.py tem o mesmo nome do módulo "token" do Python; tira a pasta do caminho de importação.
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]

import glob, json, re, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTES = os.path.join(ROOT, "scripts", "fontes")
BLOB_RE = re.compile(r"/_blob/([0-9a-f]{32})")


def ler(pasta, nome):
    return open(os.path.join(pasta, os.path.basename(nome)), encoding="utf-8").read()


def css_fontes():
    regras = []
    for f in sorted(glob.glob(os.path.join(FONTES, "montserrat-*-normal.woff2"))):
        peso = re.search(r"-(\d{3})-normal", f).group(1)
        ext = "-ext-" in f
        faixa = ("U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF"
                 if ext else
                 "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD")
        regras.append(f"@font-face{{font-family:'Montserrat';font-style:normal;font-weight:{peso};font-display:block;"
                      f"src:url('file://{f}') format('woff2');unicode-range:{faixa};}}")
    return "\n".join(regras)


def preparar_html(html, blobs):
    html = re.sub(r'<script src="\./support\.js"></script>', "", html)
    html = re.sub(r'<link[^>]+fonts\.googleapis\.com[^>]*>', "", html)
    html = re.sub(r'<script type="text/x-dc".*?</script>', "", html, flags=re.S)
    faltando = []

    def troca(m):
        bid = m.group(1)
        achados = glob.glob(os.path.join(blobs, bid + ".*"))
        if not achados:
            faltando.append(bid)
            return m.group(0)
        return "file://" + os.path.abspath(achados[0])

    html = BLOB_RE.sub(troca, html)
    if faltando:
        raise SystemExit("blobs faltando: " + ", ".join(sorted(set(faltando))))
    estilo = f"<style>{css_fontes()}\nhtml,body{{margin:0;padding:0;background:#fff}}</style>"
    return html.replace("</head>", estilo + "</head>", 1)


def render(codigo, canvas, blobs, arquivos):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    destino = os.path.join(ROOT, "fila", codigo)
    if os.path.isdir(os.path.join(ROOT, "publicados", codigo)):
        raise SystemExit(f"{codigo} já foi publicado; nada a fazer")
    os.makedirs(destino, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="render-")
    saidas = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for i, nome in enumerate(arquivos, 1):
            html = preparar_html(ler(canvas, nome), blobs)
            arq = os.path.join(tmp, f"{i:02d}.html")
            open(arq, "w", encoding="utf-8").write(html)
            pg.goto("file://" + arq)
            pg.wait_for_load_state("networkidle")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_function("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)", timeout=15000)
            el = pg.locator("x-dc > div").last
            png = os.path.join(tmp, f"{i:02d}.png")
            el.screenshot(path=png)
            img = Image.open(png).convert("RGB")
            if img.size != (1080, 1350):
                raise SystemExit(f"{nome}: tamanho {img.size}, esperado 1080x1350")
            jpg = os.path.join(destino, f"{i:02d}.jpg")
            img.save(jpg, "JPEG", quality=92, optimize=True, progressive=True)
            saidas.append(os.path.relpath(jpg, ROOT))
        nav.close()
    # remove imagens que sobraram de uma versão anterior com mais cards
    for velho in glob.glob(os.path.join(destino, "[0-9][0-9].jpg")):
        if int(os.path.basename(velho)[:2]) > len(arquivos):
            os.remove(velho)
    pj = os.path.join(destino, "post.json")
    if not os.path.isfile(pj):
        json.dump({"titulo": codigo, "legenda": "", "alt": [], "publicar_em": "", "aprovado": False},
                  open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"codigo": codigo, "imagens": saidas}, ensure_ascii=False))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "blobs" and len(a) >= 3:
        ids = set()
        for nome in a[2:]:
            ids.update(BLOB_RE.findall(ler(a[1], nome)))
        print("\n".join(sorted(ids)))
    elif a and a[0] == "render" and len(a) >= 5:
        render(a[1], a[2], a[3], a[4:])
    else:
        print(__doc__)
        sys.exit(1)

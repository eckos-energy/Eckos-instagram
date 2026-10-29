"""Publica no site (WordPress, eckos.energy) os artigos aprovados da pasta site/fila/.

Cada artigo fica em site/fila/<CÓDIGO>/ (mesmo código do post do Instagram) com:
  artigo.json -> {
      "titulo", "slug", "conteudo" (Markdown), "resumo",
      "seo_titulo", "meta_descricao", "palavra_chave",
      "categoria" (ex.: "Notícias"), "tags": [...],
      "alt_capa", "publicar_em": "2026-11-03T18:07:00-03:00",
      "aprovado": true, "status_wp": "publish" | "draft"
  }
  capa.jpg (ou capa.png) -> imagem destacada (opcional)

Sai quando aprovado == true e publicar_em já passou. Depois, a pasta vai para
site/publicados/<CÓDIGO>/ com resultado.json (id e link). Se der erro, a pasta
ganha erro.json; para tentar de novo, apague o erro.json.

Credenciais nos segredos WP_URL, WP_USER e WP_APP_PASSWORD (senha de aplicativo
do WordPress). Nunca são impressas.
"""
import base64, html, json, mimetypes, os, re, shutil, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(ROOT, "site", "fila")
PUB = os.path.join(ROOT, "site", "publicados")
WP_URL = os.environ.get("WP_URL", "").strip().rstrip("/")
WP_USER = os.environ.get("WP_USER", "").strip()
WP_PASS = os.environ.get("WP_APP_PASSWORD", "").strip()
UA = "Mozilla/5.0 (compatible; EckosBot/1.0; +https://eckos.energy)"


def auth_header():
    tok = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    return {"Authorization": f"Basic {tok}", "User-Agent": UA, "Accept": "application/json"}


def wp(method, path, body=None, raw=None, headers=None, params=None):
    url = f"{WP_URL}/wp-json/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    h = auth_header()
    data = None
    if raw is not None:
        data = raw
        h.update(headers or {})
    elif body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="replace")[:600]
        for s in (WP_PASS, WP_PASS.replace(" ", "")):
            if s:
                txt = txt.replace(s, "***")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {txt}") from None


# ---------- Markdown simples -> blocos do Gutenberg ----------
def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)",
               lambda m: f'<a href="{m.group(2)}"' + ('' if m.group(2).startswith(('/', WP_URL or '§')) else ' target="_blank" rel="noopener"') + f'>{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    return t


def md_to_blocks(md):
    out, para, lst, lst_tag = [], [], [], None

    def flush_para():
        if para:
            out.append(f"<!-- wp:paragraph -->\n<p>{inline(' '.join(para))}</p>\n<!-- /wp:paragraph -->")
            para.clear()

    def flush_list():
        nonlocal lst_tag
        if lst:
            ordered = lst_tag == "ol"
            attrs = ' {"ordered":true}' if ordered else ""
            items = "".join(f"<!-- wp:list-item -->\n<li>{inline(i)}</li>\n<!-- /wp:list-item -->" for i in lst)
            out.append(f"<!-- wp:list{attrs} -->\n<{lst_tag} class=\"wp-block-list\">{items}</{lst_tag}>\n<!-- /wp:list -->")
            lst.clear()
        lst_tag = None

    for line in md.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if not s:
            flush_para(); flush_list(); continue
        m = re.match(r"^(#{2,4})\s+(.*)$", s)
        if m:
            flush_para(); flush_list()
            lvl = len(m.group(1))
            attrs = "" if lvl == 2 else f' {{"level":{lvl}}}'
            out.append(f"<!-- wp:heading{attrs} -->\n<h{lvl} class=\"wp-block-heading\">{inline(m.group(2))}</h{lvl}>\n<!-- /wp:heading -->")
            continue
        m = re.match(r"^[-*]\s+(.*)$", s) or re.match(r"^\d+[.)]\s+(.*)$", s)
        if m:
            flush_para()
            tag = "ul" if re.match(r"^[-*]\s", s) else "ol"
            if lst_tag and lst_tag != tag:
                flush_list()
            lst_tag = tag
            lst.append(m.group(1))
            continue
        if s.startswith("# "):  # H1 é o título do post; ignora
            continue
        flush_list()
        para.append(s)
    flush_para(); flush_list()
    return "\n\n".join(out)


# ---------- termos (categoria e tags) ----------
def term_id(tax, name):
    found = wp("GET", f"wp/v2/{tax}", params={"search": name, "per_page": 100})
    for t in found or []:
        if html.unescape(t.get("name", "")).strip().lower() == name.strip().lower():
            return t["id"]
    try:
        return wp("POST", f"wp/v2/{tax}", {"name": name})["id"]
    except RuntimeError as e:
        m = re.search(r'"term_id":(\d+)', str(e))  # já existe com outro slug
        if m:
            return int(m.group(1))
        raise


def upload_capa(folder, alt, titulo):
    for nome in ("capa.jpg", "capa.jpeg", "capa.png", "capa.webp"):
        p = os.path.join(folder, nome)
        if os.path.isfile(p):
            break
    else:
        return None
    ctype = mimetypes.guess_type(p)[0] or "image/jpeg"
    slug = re.sub(r"[^a-z0-9-]+", "-", (titulo or "capa").lower()).strip("-")[:60] or "capa"
    ext = os.path.splitext(p)[1]
    media = wp("POST", "wp/v2/media", raw=open(p, "rb").read(), headers={
        "Content-Type": ctype,
        "Content-Disposition": f'attachment; filename="{slug}{ext}"',
    })
    if alt:
        wp("POST", f"wp/v2/media/{media['id']}", {"alt_text": alt, "title": titulo or ""})
    return media["id"]


def set_rank_math(post_id, a):
    meta = {}
    if a.get("seo_titulo"):
        meta["rank_math_title"] = a["seo_titulo"]
    if a.get("meta_descricao"):
        meta["rank_math_description"] = a["meta_descricao"]
    if a.get("palavra_chave"):
        meta["rank_math_focus_keyword"] = a["palavra_chave"]
    if not meta:
        return "sem dados de SEO"
    try:
        wp("POST", "rankmath/v1/updateMeta", {"objectType": "post", "objectID": post_id, "meta": meta})
        return "ok"
    except RuntimeError as e:
        return f"falhou: {e}"


def publish(code, folder, a):
    titulo = a.get("titulo", "").strip()
    if not titulo or not a.get("conteudo", "").strip():
        raise RuntimeError("artigo sem título ou sem conteúdo")
    status = "draft" if a.get("status_wp") == "draft" else "publish"
    capa_id = (a.get("rascunho") or {}).get("capa_id") or upload_capa(folder, a.get("alt_capa", ""), titulo)
    body = {
        "title": titulo,
        "content": md_to_blocks(a["conteudo"]),
        "status": status,
        "excerpt": a.get("resumo", ""),
    }
    if a.get("slug"):
        body["slug"] = a["slug"]
    if capa_id:
        body["featured_media"] = capa_id
    if a.get("categoria"):
        body["categories"] = [term_id("categories", a["categoria"])]
    if a.get("tags"):
        body["tags"] = [term_id("tags", t) for t in a["tags"] if t.strip()]
    if a.get("wp_id"):  # já criado antes (ex.: rascunho), atualiza o mesmo post
        post = wp("POST", f"wp/v2/posts/{a['wp_id']}", body)
    else:
        post = wp("POST", "wp/v2/posts", body)
    seo = set_rank_math(post["id"], a)
    return {
        "codigo": code,
        "id": post["id"],
        "status": post.get("status"),
        "link": post.get("link"),
        "capa_id": capa_id,
        "rank_math": seo,
        "publicado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main():
    if not (WP_URL and WP_USER and WP_PASS):
        print("Segredos WP_URL, WP_USER ou WP_APP_PASSWORD ausentes.")
        sys.exit(1)
    if not os.path.isdir(FILA):
        print("Nada na fila do site.")
        return
    agora = datetime.now(timezone.utc)
    falhas = 0
    for code in sorted(os.listdir(FILA)):
        folder = os.path.join(FILA, code)
        aj = os.path.join(folder, "artigo.json")
        if not os.path.isfile(aj) or os.path.isfile(os.path.join(folder, "erro.json")):
            continue
        a = json.load(open(aj, encoding="utf-8"))
        if not a.get("aprovado"):
            continue
        quando = a.get("publicar_em")
        if quando and datetime.fromisoformat(quando) > agora:
            continue
        try:
            res = publish(code, folder, a)
        except Exception as e:  # registra e segue para o próximo
            falhas += 1
            json.dump({"erro": str(e)[:900], "em": agora.isoformat(timespec="seconds")},
                      open(os.path.join(folder, "erro.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"{code}: ERRO {str(e)[:300]}")
            continue
        if res["status"] == "draft":
            # rascunho fica na fila, sem aprovação, guardando o id do post para a publicação final
            a["wp_id"] = res["id"]; a["aprovado"] = False; a["rascunho"] = res
            json.dump(a, open(aj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"{code}: rascunho criado (id {res['id']}), SEO {res['rank_math']}")
            continue
        os.makedirs(PUB, exist_ok=True)
        dest = os.path.join(PUB, code)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.move(folder, dest)
        json.dump(res, open(os.path.join(dest, "resultado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"{code}: publicado {res['link']} (SEO {res['rank_math']})")
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()

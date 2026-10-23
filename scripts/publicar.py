"""Publica no Instagram os posts aprovados da pasta fila/.

Cada post fica em fila/<CODIGO>/ com:
  post.json  -> {"titulo", "legenda", "alt": [...], "publicar_em": "2026-10-21T18:00:00-03:00", "aprovado": true}
  01.jpg, 02.jpg, ...  (JPEG, na ordem do carrossel)

O post sai quando aprovado == true e publicar_em já passou. Depois de publicado,
a pasta vai para publicados/<CODIGO>/ com resultado.json (id e link do post).
O token fica no segredo IG_TOKEN do repositório e nunca é impresso.
"""
import json, os, sys, time, shutil, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone

API = "https://graph.instagram.com"
TOKEN = os.environ.get("IG_TOKEN", "").strip()
REPO = os.environ["GITHUB_REPOSITORY"]
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(ROOT, "fila")
PUBLICADOS = os.path.join(ROOT, "publicados")


def call(method, path, params=None):
    params = dict(params or {})
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(f"{API}/{path}?{data.decode()}")
    else:
        req = urllib.request.Request(f"{API}/{path}", data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {body.replace(TOKEN, '***')}") from None


def wait_ready(container_id, limit=60):
    for _ in range(limit):
        st = call("GET", container_id, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id}: {st}")
        time.sleep(5)
    raise RuntimeError(f"container {container_id} não ficou pronto a tempo")


def publish(user_id, code, folder, post):
    imgs = sorted(f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg")))
    if not imgs:
        raise RuntimeError("nenhuma imagem .jpg na pasta")
    if len(imgs) > 20:
        raise RuntimeError("carrossel aceita no máximo 20 imagens")
    alts = post.get("alt") or []
    caption = post.get("legenda", "")
    url = lambda f: f"{RAW}/fila/{urllib.parse.quote(code)}/{urllib.parse.quote(f)}"

    if len(imgs) == 1:
        p = {"image_url": url(imgs[0]), "caption": caption}
        if alts:
            p["alt_text"] = alts[0]
        creation = call("POST", f"{user_id}/media", p)["id"]
    else:
        children = []
        for i, f in enumerate(imgs):
            p = {"image_url": url(f), "is_carousel_item": "true"}
            if i < len(alts) and alts[i]:
                p["alt_text"] = alts[i]
            cid = call("POST", f"{user_id}/media", p)["id"]
            wait_ready(cid)
            children.append(cid)
        creation = call("POST", f"{user_id}/media", {
            "media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})["id"]
    wait_ready(creation)
    media_id = call("POST", f"{user_id}/media_publish", {"creation_id": creation})["id"]
    info = call("GET", media_id, {"fields": "permalink,timestamp"})
    return {"media_id": media_id, "permalink": info.get("permalink"), "timestamp": info.get("timestamp")}


def main():
    now = datetime.now(timezone.utc)
    due = []
    for code in sorted(os.listdir(FILA)) if os.path.isdir(FILA) else []:
        folder = os.path.join(FILA, code)
        pj = os.path.join(folder, "post.json")
        if not os.path.isfile(pj):
            continue
        post = json.load(open(pj, encoding="utf-8"))
        if post.get("aprovado") is not True or os.path.exists(os.path.join(folder, "erro.json")):
            continue
        when = datetime.fromisoformat(post["publicar_em"])
        if when.tzinfo is None:
            raise SystemExit(f"{code}: publicar_em precisa ter fuso (ex.: -03:00)")
        if when <= now:
            due.append((code, folder, post))
    if not due:
        print("Nada para publicar agora.")
        return
    if not TOKEN:
        sys.exit("Segredo IG_TOKEN não configurado no repositório.")
    me = call("GET", "me", {"fields": "user_id,username"})
    user_id = me["user_id"]
    print(f"Conta: @{me.get('username')}")
    failed = False
    os.makedirs(PUBLICADOS, exist_ok=True)
    for code, folder, post in due:
        try:
            res = publish(user_id, code, folder, post)
            res["codigo"] = code
            res["publicado_em"] = datetime.now(timezone.utc).isoformat()
            dest = os.path.join(PUBLICADOS, code)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.move(folder, dest)
            json.dump(res, open(os.path.join(dest, "resultado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"Publicado {code}: {res['permalink']}")
        except Exception as e:
            failed = True
            json.dump({"erro": str(e), "em": datetime.now(timezone.utc).isoformat()},
                      open(os.path.join(folder, "erro.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"ERRO em {code}: {e}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

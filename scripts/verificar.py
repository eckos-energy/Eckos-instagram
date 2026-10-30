"""Confere se o token do Instagram funciona e se tem permissão de publicar. Não publica nada."""
import json, os, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
T = os.environ.get("IG_TOKEN", "").strip()
out = {"em": datetime.now(timezone.utc).isoformat()}
def get(path, **p):
    p["access_token"] = T
    try:
        with urllib.request.urlopen(f"https://graph.instagram.com/{path}?" + urllib.parse.urlencode(p), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"erro": e.read().decode(errors="replace").replace(T, "***")}
if not T:
    out["ok"] = False; out["erro"] = "IG_TOKEN vazio"
else:
    me = get("me", fields="user_id,username,account_type")
    out["conta"] = {k: me.get(k) for k in ("username", "account_type")} if "erro" not in me else me
    lim = get(f"{me.get('user_id')}/content_publishing_limit", fields="quota_usage,config") if "erro" not in me else {}
    out["limite_publicacao"] = lim
    out["ok"] = "erro" not in me and "erro" not in lim
# Teste de localização (não publica nada): para cada id em testar_local.txt, cria um contêiner de imagem
# com location_id e confere se a API aceita. Contêineres não publicados expiram sozinhos em 24 h.
def post(path, **p):
    p["access_token"] = T
    req = urllib.request.Request(f"https://graph.instagram.com/{path}", data=urllib.parse.urlencode(p).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"erro": e.read().decode(errors="replace").replace(T, "***")}
if T and out.get("ok") and os.path.isfile("testar_local.txt"):
    import time
    repo = os.environ.get("GITHUB_REPOSITORY", "eckos-energy/Eckos-instagram")
    img = f"https://raw.githubusercontent.com/{repo}/main/publicados/O07/01.jpg"
    res = {}
    for lid in [l.strip() for l in open("testar_local.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]:
        c = post(f"{me.get('user_id')}/media", image_url=img, location_id=lid)
        if "erro" in c:
            res[lid] = {"aceito": False, "erro": c["erro"]}; continue
        st = {}
        for _ in range(12):
            st = get(c["id"], fields="status_code,status")
            if st.get("status_code") in ("FINISHED", "ERROR", "EXPIRED"): break
            time.sleep(5)
        res[lid] = {"aceito": st.get("status_code") == "FINISHED", "status": st}
    out["teste_localizacao"] = res
json.dump(out, open("verificacao.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False))

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
json.dump(out, open("verificacao.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False))

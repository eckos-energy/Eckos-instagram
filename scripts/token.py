"""Confere o token do Instagram e renova por mais 60 dias.

Se o segredo GH_PAT existir (token do GitHub com permissão de escrever segredos
neste repositório), o novo token é gravado em IG_TOKEN automaticamente.
Sem GH_PAT, o script só confere e avisa quantos dias faltam.
O token nunca é impresso.
"""
import json, os, subprocess, sys, urllib.parse, urllib.request, urllib.error

TOKEN = os.environ.get("IG_TOKEN", "").strip()
if not TOKEN:
    sys.exit("Segredo IG_TOKEN não configurado.")


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace').replace(TOKEN, '***')}")


me = get("https://graph.instagram.com/me?" + urllib.parse.urlencode({"fields": "user_id,username", "access_token": TOKEN}))
print(f"Token válido para @{me.get('username')}")

new = get("https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": TOKEN}))
days = int(new.get("expires_in", 0)) // 86400
print(f"Token renovado: vale por mais {days} dias.")

if os.environ.get("GH_TOKEN"):
    subprocess.run(["gh", "secret", "set", "IG_TOKEN", "--repo", os.environ["GITHUB_REPOSITORY"]],
                   input=new["access_token"].encode(), check=True)
    print("Segredo IG_TOKEN atualizado.")
else:
    print("Sem GH_PAT: gere um novo token no painel da Meta antes de 60 dias e atualize o segredo IG_TOKEN.")

"""Sincroniza a fila do GitHub com o calendário de posts da Eckos.

Uso: python scripts/sincronizar.py <pasta_com_os_json_do_calendario>
A pasta tem um <CÓDIGO>.json por post (como sai do ArtifactData com out_dir).

Regras:
- status "aprovado" ou "agendado", com data, e pasta fila/<CÓDIGO>/ existente
  -> post.json recebe legenda, texto alternativo, publicar_em (data + hora, -03:00) e aprovado = true.
- qualquer outro status -> aprovado = false (o post fica parado na fila).
- Não mexe em posts já publicados (pasta publicados/<CÓDIGO>/).

Imprime um resumo em JSON:
  liberados      -> códigos que ficaram aprovados nesta rodada (o calendário deve virar "agendado")
  segurados      -> códigos que voltaram para aprovado = false
  sem_pasta      -> aprovados no calendário sem imagens na fila (precisa renderizar e subir)
  publicados     -> {código: {permalink, publicado_em}} de publicados/
  erros          -> {código: mensagem} de fila/<CÓDIGO>/erro.json
"""
import json, os, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(ROOT, "fila")
PUB = os.path.join(ROOT, "publicados")
APROVA = ("aprovado", "agendado")


def main(src):
    posts = {}
    for f in glob.glob(os.path.join(src, "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        d = d.get("data", d) if isinstance(d.get("data"), dict) else d
        posts[os.path.basename(f)[:-5]] = d
    res = {"liberados": [], "segurados": [], "sem_pasta": [], "publicados": {}, "erros": {}}
    for code, p in sorted(posts.items()):
        folder = os.path.join(FILA, code)
        if os.path.isdir(os.path.join(PUB, code)):
            continue
        quer = p.get("status") in APROVA and bool(p.get("data"))
        if not os.path.isdir(folder):
            if quer:
                res["sem_pasta"].append(code)
            continue
        pj = os.path.join(folder, "post.json")
        atual = json.load(open(pj, encoding="utf-8")) if os.path.isfile(pj) else {}
        novo = dict(atual)
        if quer:
            hora = (p.get("hora") or "18:07").strip()
            novo.update({
                "titulo": p.get("titulo", code),
                "legenda": p.get("legenda", ""),
                "alt": p.get("alt") or [],
                "publicar_em": f"{p['data']}T{hora}:00-03:00",
                "aprovado": True,
            })
            if not novo["legenda"]:
                res["erros"][code] = "aprovado sem legenda no calendário"
                novo["aprovado"] = False
        else:
            novo["aprovado"] = False
        if novo != atual:
            json.dump(novo, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            if novo.get("aprovado") and not atual.get("aprovado"):
                res["liberados"].append(code)
            elif atual.get("aprovado") and not novo.get("aprovado"):
                res["segurados"].append(code)
            elif novo.get("aprovado"):
                res["liberados"].append(code)
    for r in glob.glob(os.path.join(PUB, "*", "resultado.json")):
        d = json.load(open(r, encoding="utf-8"))
        res["publicados"][os.path.basename(os.path.dirname(r))] = {"permalink": d.get("permalink"), "publicado_em": d.get("publicado_em")}
    for e in glob.glob(os.path.join(FILA, "*", "erro.json")):
        res["erros"][os.path.basename(os.path.dirname(e))] = json.load(open(e, encoding="utf-8")).get("erro")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])

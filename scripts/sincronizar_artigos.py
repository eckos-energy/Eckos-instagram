"""Sincroniza os artigos do site com a coleção `artigos` do calendário da Eckos.

Uso: python scripts/sincronizar_artigos.py <pasta_com_os_json_da_colecao_artigos>
A pasta tem um <CÓDIGO>.json por artigo (como sai do ArtifactData com out_dir).
O código é o mesmo do post do Instagram de onde o artigo saiu (ex.: N02).

Campos lidos do calendário: titulo, slug, conteudo (Markdown), resumo, seoTitulo,
metaDescricao, palavraChave, categoria, tags, altCapa, data, hora, status.

Regras:
- status "aprovado" ou "agendado", com data -> site/fila/<CÓDIGO>/artigo.json com
  aprovado = true e publicar_em = data + hora (-03:00). Cria a pasta se faltar.
- status "rascunho" -> aprovado = true e status_wp = "draft" (cria rascunho no WordPress
  para o Gabriel revisar lá; depois o artigo volta a esperar aprovação).
- qualquer outro status -> aprovado = false (fica parado).
- Capa: se a pasta não tem capa.*, copia a 01.jpg do post (fila/ ou publicados/<CÓDIGO>/).
- Não mexe em artigos já publicados (site/publicados/<CÓDIGO>/).

Imprime um resumo em JSON:
  liberados   -> códigos aprovados nesta rodada (o calendário deve virar "agendado")
  rascunhos   -> códigos que vão virar rascunho no WordPress
  segurados   -> códigos que voltaram para aprovado = false
  publicados  -> {código: {link, publicado_em}} de site/publicados/
  rascunhos_criados -> {código: link} de rascunhos já criados no WordPress
  erros       -> {código: mensagem}
"""
import glob, json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILA = os.path.join(ROOT, "site", "fila")
PUB = os.path.join(ROOT, "site", "publicados")
APROVA = ("aprovado", "agendado")


def capa_existente(folder):
    return any(os.path.isfile(os.path.join(folder, f"capa.{e}")) for e in ("jpg", "jpeg", "png", "webp"))


def copia_capa(code, folder):
    for base in ("fila", "publicados"):
        src = os.path.join(ROOT, base, code, "01.jpg")
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(folder, "capa.jpg"))
            return True
    return False


def main(src):
    arts = {}
    for f in glob.glob(os.path.join(src, "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        d = d.get("data", d) if isinstance(d.get("data"), dict) else d
        arts[os.path.basename(f)[:-5]] = d
    res = {"liberados": [], "rascunhos": [], "segurados": [], "publicados": {}, "rascunhos_criados": {}, "erros": {}}
    for code, c in sorted(arts.items()):
        if os.path.isdir(os.path.join(PUB, code)):
            continue
        st = (c.get("status") or "").lower()
        quer_pub = st in APROVA and bool(c.get("data"))
        quer_rasc = st == "rascunho"
        folder = os.path.join(FILA, code)
        aj = os.path.join(folder, "artigo.json")
        atual = json.load(open(aj, encoding="utf-8")) if os.path.isfile(aj) else None
        if atual is None and not (quer_pub or quer_rasc):
            continue
        novo = dict(atual or {})
        novo.update({
            "titulo": c.get("titulo", ""),
            "slug": c.get("slug", ""),
            "conteudo": c.get("conteudo", ""),
            "resumo": c.get("resumo", ""),
            "seo_titulo": c.get("seoTitulo", ""),
            "meta_descricao": c.get("metaDescricao", ""),
            "palavra_chave": c.get("palavraChave", ""),
            "categoria": c.get("categoria") or "Notícias",
            "tags": c.get("tags") or [],
            "alt_capa": c.get("altCapa", ""),
        })
        if quer_pub:
            hora = (c.get("hora") or "18:07").strip()
            novo.update({"publicar_em": f"{c['data']}T{hora}:00-03:00", "aprovado": True, "status_wp": "publish"})
        elif quer_rasc and not (atual or {}).get("wp_id"):
            novo.update({"publicar_em": None, "aprovado": True, "status_wp": "draft"})
        else:
            novo["aprovado"] = False
        if novo.get("aprovado") and not (novo["titulo"] and novo["conteudo"]):
            res["erros"][code] = "artigo aprovado sem título ou sem conteúdo no calendário"
            novo["aprovado"] = False
        os.makedirs(folder, exist_ok=True)
        if not capa_existente(folder):
            copia_capa(code, folder)
        if novo != atual:
            json.dump(novo, open(aj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            if novo.get("aprovado"):
                res["rascunhos" if novo.get("status_wp") == "draft" else "liberados"].append(code)
            elif (atual or {}).get("aprovado"):
                res["segurados"].append(code)
    for r in glob.glob(os.path.join(PUB, "*", "resultado.json")):
        d = json.load(open(r, encoding="utf-8"))
        res["publicados"][os.path.basename(os.path.dirname(r))] = {"link": d.get("link"), "publicado_em": d.get("publicado_em")}
    for a in glob.glob(os.path.join(FILA, "*", "artigo.json")):
        d = json.load(open(a, encoding="utf-8"))
        if d.get("rascunho"):
            res["rascunhos_criados"][os.path.basename(os.path.dirname(a))] = d["rascunho"].get("link")
    for e in glob.glob(os.path.join(FILA, "*", "erro.json")):
        res["erros"][os.path.basename(os.path.dirname(e))] = json.load(open(e, encoding="utf-8")).get("erro")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])

# Artigos do site (eckos.energy)

Cada notícia aprovada para o Instagram vira também um artigo original para a seção Artigos do site. O objetivo é ranquear no Google e gerar contatos. O artigo usa o **mesmo código do post** (ex.: N04) e fica na coleção `artigos` do calendário.

## Quem somos (contexto para o texto)
Eckos Energy: soluções em energia (solar on-grid, híbrido e off-grid, baterias, carregadores de veículos elétricos) para casas, sítios e empresas de Atibaia, Bragança Paulista e região. Engenheiro responsável com registro no CREA-SP e cerca de 12 anos de experiência.

## Regras de conteúdo
1. **Nada inventado.** Fatos, números, datas e nomes só da fonte. O que precisar de confirmação vai marcado com `[VERIFICAR]` e listado ao Gabriel. Artigo com `[VERIFICAR]` não pode ser aprovado.
2. **Nada copiado.** Reescrever com palavras próprias, sem frases da notícia original. Citar a fonte com link no corpo do texto.
3. **Ir além da notícia.** Explicar o que ela muda na prática para quem tem casa, sítio ou empresa, com o olhar técnico da Eckos (custo, retorno, regulação, segurança). É o que diferencia o artigo de uma cópia.
4. **Recorte regional** quando fizer sentido (Atibaia, Bragança Paulista e região, concessionária, clima).
5. **Tom:** claro, caloroso, transparente, sem exagero nem tom de vendedor. Simples para residências; um pouco mais técnico para empresas. Apontar a dor e como a Eckos resolve.
6. Credenciais (CREA, ART, normas ABNT) só quando forem naturalmente relevantes.
7. Energia mais cara no horário de ponta: deixar claro que vale para média tensão ou tarifa branca.
8. Empresas e usinas: falar em "exemplos de solução", nunca em clientes atendidos.
9. Sem telefone no texto; o CTA leva ao orçamento do site e ao WhatsApp.

## Estrutura (800 a 1.200 palavras)
- Título com a palavra-chave principal (o título vira o H1; não repetir no conteúdo).
- Introdução de 2 a 3 frases respondendo "o que aconteceu e por que importa".
- Seções `##` e `###`: o que diz a notícia → o que muda na prática → o que fazer agora.
- `## Perguntas frequentes` com 3 a 4 perguntas reais que as pessoas buscam no Google, cada uma como `###` seguida da resposta.
- Fechamento com CTA: simular a economia ou pedir orçamento.
- 2 a 3 links internos, escolhidos entre: [energia solar para casa](/para-sua-casa/), [energia solar para sítio](/para-seu-sitio/), [energia solar para empresas](/para-seu-negocio/), [carregador veicular](/carregador-veicular/), [orçamento](/#orcamento). Confirmar o endereço real das páginas no site antes de usar; se a página não existir, usar só o orçamento.

## Formato no calendário (coleção `artigos`, documento = código do post)
| Campo | Conteúdo |
|---|---|
| `titulo` | Título do artigo (até ~65 caracteres) |
| `slug` | Endereço curto, minúsculo, sem acentos, com hífens |
| `conteudo` | Corpo em Markdown: parágrafos, `##`/`###`, listas com `-`, **negrito** e [links](url) |
| `resumo` | 1 a 2 frases (aparece na lista de artigos) |
| `seoTitulo` | Título para o Google, até 60 caracteres |
| `metaDescricao` | Até 155 caracteres, com chamada para ação |
| `palavraChave` | Palavra-chave principal |
| `palavrasSecundarias` | 3 a 5 secundárias (lista) |
| `categoria` | "Notícias" (guias perenes: "Guias") |
| `tags` | 3 a 5 tags |
| `altCapa` | Texto alternativo da imagem destacada (a capa é a 01.jpg do post) |
| `fonte` / `fonteLink` | Veículo e link da notícia |
| `verificar` | Lista dos pontos `[VERIFICAR]` (vazia quando estiver tudo confirmado) |
| `data` / `hora` | Mesmos do post do Instagram |
| `status` | `aguardando` → (`rascunho`) → `aprovado` → `agendado` → `publicado` |
| `link` / `publicadoEm` | Preenchidos depois da publicação |

## Aprovação e publicação
- O artigo é gravado com status `aguardando` e apresentado ao Gabriel junto com o post.
- `rascunho`: o Gabriel quer ver no WordPress antes; a liberação cria um rascunho e devolve o link.
- `aprovado` só com OK explícito do Gabriel ("pode publicar o artigo N04") ou mudança dele no calendário.
- A liberação (7h e 15h) roda `scripts/sincronizar_artigos.py`, dá push e o GitHub Actions publica no horário (`.github/workflows/publicar-site.yml`).

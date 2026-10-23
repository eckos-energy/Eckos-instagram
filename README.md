# Eckos Energy · publicação no Instagram

Automação que publica no Instagram (@eckos.energy) os posts que o Gabriel aprovou.

- `fila/<CÓDIGO>/`: posts aprovados esperando o horário. Cada pasta tem `post.json` (legenda, texto alternativo, horário) e as imagens `01.jpg`, `02.jpg`…
- `publicados/<CÓDIGO>/`: posts que já foram ao ar, com `resultado.json` (id e link).
- A cada 15 minutos o GitHub Actions confere a fila e publica o que já passou do horário.
- Se algo der errado, a pasta do post ganha um `erro.json` e o GitHub manda e-mail avisando. Para tentar de novo, apague o `erro.json`.

Segredos do repositório (Settings → Secrets and variables → Actions):
- `IG_TOKEN`: token da API do Instagram (obrigatório).
- `GH_PAT`: token do GitHub com permissão de escrever segredos neste repositório (opcional; com ele o token do Instagram é renovado sozinho toda semana).

As imagens ficam públicas neste repositório porque a API do Instagram exige um endereço público para buscá-las.

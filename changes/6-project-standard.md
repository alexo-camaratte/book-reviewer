### Alterado
- PRs de tarefa registram a mudança numa nota `changes/<N>-<slug>.md` e não mexem mais
  no `CHANGELOG.md` nem na versão; um PR de release (`release_version.py cut`) junta as
  notas e muda a versão. Merge de tarefa não publica release (#6).
- O `Required CI` confere o escopo do PR: branch `<tipo>/<N>-<slug>`, `Refs #N` sem
  palavra de fechamento, uma nota da própria issue e linha `Security-Review:` quando o
  PR toca CI, scripts, instruções ou permissões de agente (#6).

### Segurança
- O `Required CI` audita dependências: `pnpm audit --prod` do frontend falha com
  vulnerabilidade moderada ou pior; `pip-audit` do backend falha com qualquer achado,
  pois não informa severidade. Indisponibilidade da fonte do audit só gera aviso (#6).

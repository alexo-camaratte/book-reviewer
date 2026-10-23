# Notas de mudança

Cada PR de tarefa cria **um** arquivo `changes/<N>-<slug>.md`, com `N` = número da
issue da branch, e não edita o `CHANGELOG.md` nem a versão. Assim PRs paralelos não
conflitam.

```md
### Corrigido
- Frase curta em português sobre o que muda para quem usa ou opera (#N).
  Linhas de continuação ficam indentadas.
```

- Linhas aceitas: `- item`, continuação indentada logo depois de um item, linha em
  branco e `### <categoria>`.
- Categorias: `Adicionado`, `Alterado`, `Corrigido`, `Removido`, `Segurança`. O
  cabeçalho é opcional; item sem categoria vai para o topo da versão.
- `python3 scripts/release_version.py check` valida nome e conteúdo; o check de escopo
  do PR (`scripts/check-pr-scope.py`) exige a nota da própria issue e recusa alteração
  no `CHANGELOG.md` ou em nota alheia. PR que só muda o `README.md` dispensa a nota no
  contrato de versão, mas o check de escopo ainda a exige.
- O PR de release roda `python3 scripts/release_version.py cut --bump patch|minor|major`:
  muda `VERSION` e espelhos, junta as notas na nova seção do `CHANGELOG.md`, agrupadas
  por categoria e em ordem de issue, e apaga os arquivos no mesmo commit. Depois do
  merge e do CI verde na `main`, o `Publish version` cria a tag e a release. Merge de
  tarefa (notas pendentes) não publica nada.

Este `README.md` não é nota e permanece.

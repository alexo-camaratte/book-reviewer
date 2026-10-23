# Versões e releases

Modelo adaptado do Xlondz. Em 07/10/2026 Gabriel pediu releases automáticas neste projeto: depois de um merge autorizado na `main` e do CI verde desse commit exato, o workflow `Publish version` cria a tag `vX.Y.Z` e a GitHub Release. Isso não autoriza merge, deploy nem publicação fora deste repositório.

## Fontes

- `VERSION`: versão canônica do aplicativo, `MAJOR.MINOR.PATCH`.
- `frontend/package.json` e `pyproject.toml`: espelhos validados.
- `changes/<N>-<slug>.md`: nota de cada PR de tarefa, até a próxima release ([changes/README.md](changes/README.md)).
- `CHANGELOG.md`: notas publicadas, em português, com data UTC. `[Unreleased]` fica vazio; muda só no PR de release. Notas publicadas não são reescritas; correções entram em nova versão.
- Tag `vX.Y.Z` e GitHub Release: commit exato aprovado pelo CI, notas, SHA e link do run. Tags e releases nunca são movidas nem sobrescritas.

A primeira versão formal é `0.2.0`, publicada como pré-release (todas as `0.x` são pré-release).

## Escolha da versão

| Alteração | Incremento |
| --- | --- |
| Correção compatível, segurança, dependências, tooling | patch |
| Funcionalidade compatível | minor |
| Quebra de contrato em 0.x | minor, com seção de incompatibilidade |
| Quebra de contrato após 1.0.0 | major |
| Somente README.md | sem nota no contrato de versão |

Instruções de agentes, runbooks e `design/` são contratos: mudança exige nota.

## Fluxo

1. PR de tarefa: branch `<tipo>/<N>-<slug>` a partir de `origin/main`, uma nota `changes/<N>-<slug>.md`, descrição com `Refs #N`. Não toque `CHANGELOG.md` nem a versão. O merge na `main` não publica release (`NOT_A_RELEASE`).
2. PR de release, quando Gabriel pedir uma versão: escolha o incremento pela tabela acima e rode

   ```bash
   python3 scripts/release_version.py cut --bump patch
   python3 scripts/release_version.py check --base origin/main
   ```

   `cut` junta todas as notas na nova seção do `CHANGELOG.md`, atualiza `VERSION` e os espelhos e apaga as notas; não commita nem publica.
3. O CI (`Required CI`) roda uma vez por PR (branch de tarefa não dispara run de push; o push só roda na `main`, que o `Publish version` espera) e valida escopo do PR, notas, fontes consistentes, histórico preservado e um único incremento sobre a base; o ruleset da `main` exige esse check verde.
4. Após o merge autorizado (squash) do PR de release e o CI verde na `main`, confira a release em https://github.com/alexo-camaratte/book-reviewer/releases. Falha de publicação é pendência, não sucesso; reconcilie tag e release antes de repetir. Um commit com notas pendentes nunca recebe tag: se o run da release falhar, corrija antes de novos merges de tarefa ou corte uma nova versão.

`scripts/verify-release-workflow.py` fixa o hash do `release.yml` revisado; alterá-lo exige revisão e atualização do hash.

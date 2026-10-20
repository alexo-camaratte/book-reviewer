# Revisor e tradutor — orientações

Responda em pt-BR. O produto é um aplicativo local para revisão editorial em português e tradução para espanhol. Preserve a voz do autor. A interface segue o design descrito em `design/`.

## Arquitetura e escopo

Leia README.md, ARCHITECTURE.md e TASKS.md antes de trabalho relevante. Há uma interface React e um pacote Python em backend/revisor. A API local opera os livros em `.books/`; regras editoriais ficam no núcleo e modelos no adaptador provider.py. Não reintroduza páginas HTML, dashboards paralelos, monorepo de pacotes vazios ou canais futuros sem necessidade explícita.

O manuscrito, segmentação e registros editoriais são dados do usuário. Preserve `.books/` durante refactors. Revisão aplicada grava estado consolidado e auditoria, nunca sobrescreve o original. Não regenere índices ou normalize aprovações reais durante testes.

## Editorial e modelos

Separe correção objetiva, polimento opcional e tradução. Corrija com mínima intervenção; preserve nomes, termos, repetições intencionais e estilo. A tradução definitiva parte de português estabilizado. Prévia não é aprovação. O usuário autorizou um modo automático: validação separada antes de autoaprovação registrada, revisão bilíngue antes da entrega, sem escore de confiança inventado. Modo manual permanece disponível. Persistir sugestão, motivo e proveniência é obrigatório.

Jev fornece julgamentos, não gera traduções. Avaliação de qualidade e limiares exigem exemplos reais rotulados; testes com runners controlados comprovam software, não qualidade literária. Não envie o manuscrito real em experimentos por consequência de um refactor.

## Desenvolvimento

- Neste projeto, mantenha somente `main` e o checkout principal, conforme pedido do usuário. Não deixe branches ou worktrees auxiliares após concluir tarefas. Preserve processos ativos e trabalho desconhecido; não faça reset/stash/clean indiscriminado.
- Planeje mudanças estruturais e registre evidências em REFACTOR.md quando pertinente.
- Para comportamento novo/corrigido, escreva primeiro a prova de regressão; mantenha testes do núcleo. Testes de funcionalidades explicitamente aposentadas podem ser removidos junto com elas.
- Use scripts/jail.sh quando viável para validação isolada. Não copie credenciais para containers.
- Gates: scripts/ci.sh e Bandit no backend. UI deve ter smoke isolado e inspeção visual proporcionais.
- README, arquitetura, operação, tarefas e changelog devem refletir a mesma revisão.
- Commits Conventional Commits após verificação; push, merge, deploy e publicação só com autorização específica.
- Toda mudança de comportamento, configuração, tooling, contrato ou `design/` prepara uma versão e a nota no CHANGELOG no mesmo commit, conforme [RELEASES.md](RELEASES.md). A publicação da tag e da release após CI verde na `main` é automática e foi autorizada em 07/10/2026; ela não autoriza push. Confira a release antes de relatar conclusão.

## Frontend

O design do app está em `design/`. Leia `design/README.md` antes de qualquer mudança de interface; `design/IMPLEMENTACAO.md` registra a migração, concluída em 0.12.0. Cores, espaços, raios, tamanhos e estilos de texto vêm de `design/tokens.json`; não escreva valores soltos no código. As telas de referência ficam em `design/screens/` e as regras de cada componente em `design/components/`. Quando o design mudar, atualize `design/` na mesma revisão que o código.

Use as skills instaladas relevantes: vercel-react-best-practices para React; frontend-design para apresentação; web-design-guidelines para auditoria de UI. Os estilos vêm só de `design/tokens.css` e `design/components.css`, sem Tailwind nem gerador de componentes; cada componente de `design/components/` tem um arquivo em `frontend/src/components/ui/`. Não crie um segundo design system nem acrescente dependência que o app não use.

## Skills compartilhadas

Use as skills `gabriel-*` instaladas a partir do repositório canônico `my-skills`, carregando só a necessária: diagnóstico de issue ou bug → `gabriel-iss-audit`; implementação de correção aprovada → `gabriel-github-resolution`; revisão do diff final antes do push → `gabriel-pr-audit`; preparação de versão → `gabriel-release`, seguindo [RELEASES.md](RELEASES.md). Como o projeto usa só `main`, etapas de PR viram revisão do commit local antes do push. Disponibilidade não obriga a executar todas; as skills apoiam esta política e não ampliam escopo nem autoridade.

Não copie skills compartilhadas nem crie symlinks locais duplicados. A instalação pertence ao ambiente pessoal; uma skill ausente não autoriza buscá-la ou configurá-la. Siga os procedimentos documentados e relate a limitação. Plugins continuam gerenciados por seus instaladores.

# Changelog

Mudanças relevantes do Revisor, em português. Datas em UTC. `VERSION` identifica o
aplicativo inteiro (interface e backend). Fluxo em [RELEASES.md](RELEASES.md).

## [Unreleased]

## [0.23.5] - 2026-10-23

### Alterado

- O CI roda uma vez por PR: o evento de push só dispara na `main` (de onde o `Publish version` parte), um novo push no mesmo PR cancela o run anterior e o job declara só leitura do repositório.

## [0.23.4] - 2026-10-23

### Alterado

- `scripts/fast-check.sh` é o núcleo rápido do agente e do `Required CI` (compilação, testes Python e de frontend, lint e build); `scripts/ci.sh` vira atalho para ele. Fora do CI, os testes de frontend rodam com no máximo 2 workers e o build espera um lock da máquina (`scripts/share-machine.sh`), para sessões de vários projetos não disputarem CPU.

## [0.23.3] - 2026-10-21

### Corrigido

- Publica a release que a 0.23.2 não teve: o merge dela na `main` não gerou o run de CI do push, então o workflow de publicação não rodou e a 0.23.2 ficou sem tag nem GitHub Release. O código da 0.23.2 está incluído nesta versão.

## [0.23.2] - 2026-10-21

### Alterado

- O repositório mudou para `alexo-camaratte/book-reviewer`; README, fluxo de versões e teste de publicação usam o endereço novo.
- A `main` passa a receber mudanças só por PR com `Required CI` verde (squash, branch apagada no merge). Instruções do agente, tarefas e fluxo de versões descrevem esse fluxo; o projeto continua sem `staging`.

## [0.23.1] - 2026-10-16

### Alterado

- Instruções do agente sem a seção "Ferramentas pessoais" (Siftr, Pruner e Jev Browser foram desligados) e sem a skill `gabriel-verification-planning`, que foi fundida na `gabriel-github-resolution`.

### Corrigido

- Baixar um livro pronto usa o Word já gerado da revisão atual, sem refazer a exportação. No modo manual, o download começa assim que o arquivo é gerado, sem esperar recarregar o detalhe e a lista de livros.

## [0.23.0] - 2026-10-08

### Alterado

- Toda tradução pode recusar parágrafos de forma explícita, em vez de escrever uma recusa no lugar do espanhol. Um trecho com recusas passa sozinho para você, só com os parágrafos recusados; o resto fica com a tradução do modelo.
- Depois das quatro etapas, enquanto os arquivos Word são gerados e conferidos, a tela mostra "Preparando os arquivos Word" com o tempo de trabalho, em vez de "Concluído" sem sinal de atividade.

## [0.22.1] - 2026-10-08

### Corrigido

- Depois de escrever o espanhol de um trecho, ele continuava na lista de pendências até o processamento rodar de novo. Agora sai da lista na hora; sem pendências abertas, a tela mostra "Pendências resolvidas" e o botão "Gerar os arquivos Word".

## [0.22.0] - 2026-10-08

### Adicionado

- "Escrever o espanhol à mão" nos trechos já traduzidos em que a revisão do espanhol encontra uma recusa do modelo no lugar da tradução. O trecho passa para você, o processamento continua, o modelo traduz os parágrafos que aceita e você escreve só os que ele recusa. Nova operação `author-take-spanish`.

## [0.21.1] - 2026-10-08

### Corrigido

- As traduções que o modelo escolhia num trecho viravam regra para o livro inteiro: "traição" → "infidelidad" ou "sinal" → "lunar" passavam a ser exigidos em todo lugar, gerando centenas de alertas falsos e pendências na revisão do espanhol. Agora só o glossário que você escreve é regra e gera alertas. As escolhas do modelo seguem como dicas de consistência, enviadas só aos trechos que usam o termo e seguidas apenas quando o sentido é o mesmo. A revisão do espanhol roda de novo nos trechos já traduzidos, sem retraduzir.

## [0.21.0] - 2026-10-08

### Alterado

- Num trecho revisado à mão, o espanhol não é mais todo da pessoa. O processamento automático pede ao modelo a tradução dos parágrafos que ele aceita; os recusados ficam marcados e, se a resposta vier inválida, o grupo é dividido até isolar cada parágrafo recusado. "Escrever o espanhol" pede só esses parágrafos e mostra ao lado o espanhol do modelo para os demais. Mudar o português do trecho descarta essa tradução parcial.

## [0.20.0] - 2026-10-08

### Adicionado

- "Revisar manualmente" nos trechos que precisam de atenção, para quando o modelo não processa um trecho: a pessoa vê o original e a proposta, se houver, e aprova as correções, mantém o original ou ajusta o texto; depois escreve o espanhol. O trecho fica com quem escreveu: o processamento automático não o envia mais ao modelo, e o livro é entregue com ele como foi escrito. Novas operações `author-approve` e `author-translate`.

### Corrigido

- Abrir um trecho que já estava na tela agora fixa a escolha; antes, depois de uma ação, a tela podia passar a mostrar outro trecho.

## [0.19.1] - 2026-10-07

### Corrigido

- O destaque das grafias lê as propriedades do Word com o leitor XML seguro do projeto, que recusa DTD e entidades. A 0.19.0 não foi publicada porque o CI barrou essa leitura.

## [0.19.0] - 2026-10-07

### Adicionado

- O destaque das grafias protegidas vale para todas as ocorrências: se o original marca a letra incomum (o "X" vermelho de eXilados, o "TT" roxo de CamaraTTe) na maioria das vezes, os dois Word gerados usam esse destaque em todas, inclusive onde o original veio sem cor e na forma em espanhol ("eXiliados"). No Livro 2, isso corrigiu 18 letras em cada arquivo.
- O cartão "Grafias de quem escreveu" mostra cada palavra com o destaque aprendido.

## [0.18.0] - 2026-10-07

### Adicionado

- Instalar como aplicativo (PWA) no computador: manifesto com nome, cores e ícones gerados de `design/` no build e no servidor de desenvolvimento, e marcações para Chrome, Edge e Safari. O servidor entrega `/manifest.webmanifest`.
- Ícone de 192px em `design/assets/brand/`, gerado do SVG original.

## [0.17.1] - 2026-10-07

### Alterado

- Acompanhar mostra que o trabalho está andando: o arco gira na etapa em curso e, logo abaixo do nome dela, aparecem os trechos concluídos ("31 de 301 trechos") e há quanto tempo o processamento começou, atualizados a cada trecho e a cada segundo.

## [0.17.0] - 2026-10-07

### Alterado

- Processamento bem mais rápido. Na revisão e nas duas conferências, o modelo devolve só os parágrafos que alterou e lista os demais em `unchanged`; o app confere que cada parágrafo aparece uma vez. Medido com texto fictício: 32 parágrafos em 12,6 s em vez de 41,5 s, com as mesmas correções.
- Trechos de até 32 parágrafos (9.000 caracteres) em vez de 8, para livros novos ou recomeçados; livros em andamento mantêm a divisão que já têm.
- Até 8 chamadas simultâneas em vez de 4; medido: 8 juntas levam o mesmo tempo de uma.
- Livro fictício de 96 parágrafos processado de ponta a ponta em 110 s, sem repetições.

### Investigado

- Jev como filtro das conferências, testado com 1.284 casos reais do Livro 2: para não perder nenhuma correção do modelo grande, dispensaria só 15% das conferências do português e 31% das do espanhol. Não adotado.

## [0.16.0] - 2026-10-07

### Adicionado

- "Recomeçar do zero" em Mais opções: todos os trechos voltam ao início e as configurações ficam livres para mudar de novo. O arquivo original, as grafias protegidas e o glossário são mantidos, e o estado anterior fica guardado em `history/` dentro da pasta do livro.
- "Remover este livro": o livro sai de Meus livros e a pasta dele vai para `.books/.removidos/`, de onde pode ser recuperada à mão.
- Ambas pedem confirmação e não ficam disponíveis enquanto o livro está sendo processado. Novas operações `reset` e `remove`.

## [0.15.0] - 2026-10-07

### Adicionado

- Grafias de quem escreveu: palavras com maiúsculas incomuns que se repetem no original (eXilados, CamaraTTe) são encontradas e protegidas automaticamente. Se o modelo mexer nelas, o app desfaz só essa mudança e mantém as outras correções do parágrafo, na revisão e na conferência do português. A lista também vai para o modelo, inclusive na tradução.
- Cartão "Grafias de quem escreveu" em Mais opções: palavras protegidas com contagem, "Deixar de proteger", sugestões (palavras que aparecem uma vez) e campo para acrescentar, a qualquer momento. Nova operação `POST /api/books/<id>/spellings`.
- Trechos já revisados voltam à grafia original sem nova chamada ao modelo; só esses são traduzidos de novo. Com um processamento em andamento, isso acontece antes de gerar os Word, sem interromper trechos em curso.

## [0.14.0] - 2026-10-07

### Adicionado

- Ajustar o português de um trecho aprovado, a partir de "Conferir" ou direto de uma observação: o texto continua aprovado, as correções do parágrafo passam a dizer "Ajustado por você.", o que havia antes fica na auditoria e só a tradução desse trecho é refeita ao continuar. Nova operação `POST /api/books/<id>/edit-portuguese`.
- Botões e links mostram o carregamento do design enquanto a ação acontece: marcar observação, salvar, aprovar, trocar de trecho, abrir um trecho da lista.

### Corrigido

- Abrir um livro com glossário grande ficou cerca de 10 vezes mais rápido (de 1,5 s para 0,13 s no caso medido): as buscas dos termos são montadas uma vez por glossário, com um filtro rápido antes da expressão regular, e os alertas de consistência são calculados uma vez por abertura. Os resultados são idênticos aos anteriores.
- Trocar de trecho só muda a tela quando o texto do novo trecho chegou.

## [0.13.0] - 2026-10-07

### Adicionado

- Observações podem ser marcadas como lidas, uma por uma ou todas de uma vez, e desmarcadas depois. A leitura fica guardada no livro (`notes_read` em `state.json`, com auditoria) e não muda o texto, a revisão nem os arquivos entregues. Nova operação `POST /api/books/<id>/notes`.
- A tela de observações agrupa por trecho, separa "Para ler" e "Lidas", mostra quantas faltam e pagina os trechos. O livro pronto mostra quantas faltam ler ou "Observações lidas".

### Alterado

- Quando todas as correções de um parágrafo têm o mesmo motivo, ele aparece uma vez, embaixo dos pares antes → depois, em vez de repetido em cada correção.

## [0.12.1] - 2026-10-07

### Removido

- Tailwind, `tailwind-merge`, `clsx` e a configuração do gerador shadcn: o app não usava mais nenhum deles. A caixa de confirmação e os botões de navegação ganharam as poucas regras que vinham deles em `design/components.css`.

### Corrigido

- No celular, o filtro da lista de trechos ocupa a largura toda em vez de quebrar em duas linhas.

## [0.12.0] - 2026-10-07

### Removido

- Área de trabalho anterior, componentes `book-*` e o CSS da interface antiga. O app usa só os tokens e componentes de `design/`, com 26 kB de CSS em vez de 56 kB.

### Alterado

- Documentação do frontend, da arquitetura e do `design/` descreve a estrutura nova; a migração para o design está concluída.

## [0.11.0] - 2026-10-07

### Adicionado

- Telas do novo design para aprovar à mão: as três etapas do livro, conferir um trecho esperando aprovação, aprovar, ajustar o texto antes de aprovar, recusar com o pedido registrado, pedir nova revisão, trecho ainda não revisado, reabrir um trecho aprovado e aprovar vários de uma vez com confirmação. Os dois Word ficam disponíveis no mesmo lugar quando prontos.

### Alterado

- Todas as telas seguem o novo design; a área de trabalho anterior não aparece mais.

## [0.10.0] - 2026-10-07

### Adicionado

- Telas do novo design para conferir o texto: o que mudou (correções junto de cada parágrafo, fechadas no celular), texto original com as palavras corrigidas sublinhadas, português e espanhol lado a lado, ajustar o espanhol e escolher um trecho numa lista paginada, com filtro de observações.

### Alterado

- Correções aparecem por palavra inteira ("estavam → estava"), não pelo trecho de letras que mudou.
- Um livro concluído abre a conferência pelo primeiro trecho.

## [0.9.0] - 2026-10-07

### Adicionado

- Telas do novo design para preparar e ajustar o livro: escolher capítulos, orientações para a revisão, glossário com dois campos por termo e aviso de campo faltando, Mais opções, alertas de consistência e observações para quem escreveu.
- Aparência em Mais opções: tema Escuro, Claro ou Igual ao do aparelho, e tamanho do texto Normal, Grande ou Muito grande, guardados no navegador.
- Aprovação à mão ligada ou desligada por livro.

### Alterado

- "Meus livros" atualiza a lista ao abrir.
- `design/` deixa de mostrar o botão "Abrir a revisão anterior", retirado em 0.3.0.

## [0.8.0] - 2026-10-07

### Adicionado

- Telas do novo design para quando o trabalho sai do caminho: pausado, parou no meio (computador desligado ou servidor reiniciado) e trechos que precisam de atenção, cada uma com o que está salvo, as etapas e a ação para continuar.

## [0.7.0] - 2026-10-07

### Adicionado

- Telas do novo design para começar e acompanhar um livro: início, Meus livros, novo livro (com a opção de Word em espanhol), pronto para começar, livro na fila (outro em processamento), acompanhar as quatro etapas e livro pronto com os dois downloads.

### Alterado

- Importar valida tipo e tamanho do Word antes do envio e explica o problema numa frase.
- "Pausar" mostra "Pausando…" enquanto termina o que já começou.

## [0.6.0] - 2026-10-07

### Adicionado

- Estrutura do novo design: cabeçalho com "Meus livros", "Mais opções" e o tema no computador; barra inferior "Livro", "Meus livros" e "Opções" no celular; link para pular ao conteúdo.
- Escolha da tela pelo estado do livro (carregando, erro, início, outro livro, pronto para começar, acompanhar, pausado, parou no meio, precisa de atenção, livro pronto, aprovar à mão), com testes em `node --test` no CI.
- Telas de carregando e de erro do servidor no novo design.
- Classes de layout das páginas em `design/components.css`.

### Alterado

- A lista de livros sai da barra lateral e vai para "Meus livros". Até o passo 4, o livro aberto ainda mostra a área de trabalho anterior dentro da estrutura nova.

## [0.5.0] - 2026-10-07

### Adicionado

- Componentes base do novo design em `frontend/src/components/ui/`: Button, TextLink, Card, Field, FilePicker, SegmentedControl, Choice, ProgressBar, Steps, Notice, Spinner, SummaryRows, ListItem, CorrectedParagraph, ConfirmDialog, AppHeader e TabBar, todos sobre as classes `rv-` de `design/components.css`.
- Seletor de tema Escuro/Claro pronto no AppHeader, para a estrutura nova.

### Alterado

- Telas atuais usam os botões, a barra de progresso e a caixa de confirmação do design. O botão de atualizar a lista ganhou texto.
- Celular é abaixo de 768px, registrado em `design/README.md`.

### Removido

- Primitivas shadcn sem uso (empty, hover-card, scroll-area, separator, label) e as dependências `class-variance-authority` e `tw-animate-css`.

## [0.4.0] - 2026-10-07

### Alterado

- Interface passa a usar os tokens de `design/tokens.css` (cores, espaços, raios, tamanhos e tipos), sem paleta própria no frontend. Primeiro passo da migração para o novo design.
- Tema escuro e claro: segue o sistema por padrão e guarda a escolha da pessoa no navegador, aplicado antes da primeira pintura.
- Newsreader substitui Fraunces nos títulos e no texto do livro; Manrope continua na interface.
- Favicon, ícone SVG e ícone de atalho do celular vêm de `design/assets/brand/`.

### Removido

- Regras de `.gitignore` e `.dockerignore` das pastas do acervo anterior, já fora do projeto.

## [0.3.0] - 2026-10-07

### Adicionado

- A lista de trechos em `/api/books/<id>` informa `corrections`, a quantidade de correções de cada trecho, para a tela de trechos do novo design.

### Removido

- Fluxo editorial anterior: tela "Revisão anterior", CLI `revisor.cli`, rotas `/api/simple-home`, `/api/translate`, `/api/export`, `/api/rollback`, `/downloads/ptbr` e `/downloads/es`, e o núcleo `core/`, `prompts/`, `schemas/` e `docx/writer.py` que só ele usava.
- `/api/books` deixa de informar `legacy_available`. O CI não procura mais o acervo `manuscript/`.

### Incompatibilidades

- `create_server` recebe a pasta raiz em vez de um `ReviewService`. Livros em `.books/` não mudam.

## [0.2.1] - 2026-10-07

### Alterado

- AGENTS.md referencia as skills `gabriel-*` do repositório canônico `my-skills`, com a skill de cada etapa adaptada ao fluxo só com `main`.

## [0.2.0] - 2026-10-07

Primeira versão formal: consolida o histórico anterior como pré-release.

### Design e versões

- Releases versionadas: `VERSION` é a fonte canônica, espelhada em `frontend/package.json` e `pyproject.toml`; o CI valida versão e changelog e a publicação da tag e da GitHub Release ocorre automaticamente após CI verde na `main`.
- Referência de design em `design/` passa a ser versionada: tokens, componentes, 35 telas, ícones e marca. AGENTS.md aponta para ela como fonte das decisões de interface.

### Distribuição em main

- Consolidação local e remota em uma única branch `main` e um checkout principal; branches antigas e arquivos exclusivos são arquivados antes da limpeza.
- Mantidas autoria a partir do criador do Word e exportações com o nome original + REVISADO, inclusive acentos e entregas já concluídas.

- Código atual publicado com histórico próprio, sem manuscritos, Word, resultados editoriais, credenciais ou registros pessoais.
- Instalação em outra máquina com caminhos relativos; novos clones começam sem livros.
- CI funciona sem acervo pessoal e mantém a validação de índices quando o acervo local existe.
- Regras de exclusão protegem dados e documentos pessoais no Git e no contexto Docker.

### Processamento completo

- Painéis de critérios e glossário recebem chaves React distintas, eliminando avisos repetidos e colisão de identidade em livros já revisados.

- Consistência usa palavras inteiras, expressões com prioridade, singular/plural e contrações del/al. Elimina alertas de ego/emprego e grama/programadores. Escolhas duplicadas por maiúsculas compartilham um glossário efetivo; override do autor prevalece.
- Revisão bilíngue recebe alertas de terminologia explicitamente, separando feedback de consistência de rejeição de formato.
- Sidebar mostra espanhol revisado quando a geração já terminou, mantendo visível a última etapa pendente.


- Observações do original preservado separadas de falhas nas correções/traduções: lacunas e termos possivelmente inventados ficam registrados sem inferir fatos. Falhas remanescentes continuam bloqueando. Recibo JSON e navegação por trecho para o autor.
- Mudanças no contrato de revisão invalidam a indicação automática de conclusão quando receipts espanhóis estão desatualizados.


- Respostas automáticas por parágrafo completo, com motivos e diferenças calculadas pelo código; elimina sobreposições propostas pelo modelo. Modo manual preserva seus contratos.
- Trechos com respostas inválidas ou pendências não impedem processamento independente; estado precisa de atenção, lista navegável e retomada preservam resultados válidos. Tradução e entrega mantêm barreiras de cobertura/validação completas.
- Quatro contagens cumulativas de parágrafos, tempo da execução e progresso por etapa; correções finais destacadas pela posição correta e motivos acessíveis após autoaprovação.


- Recuperação unificada de respostas inválidas: inclui tentativa de apagar parágrafo, âncora/formato/JSON incorretos, tradução incompleta e quebras alteradas. Mantidos limite de duas chamadas por operação, auditoria, bloqueio de resposta inválida e preservação do trabalho salvo.

- Correções sobrepostas: regras explícitas no prompt, recuperação automática com uma segunda tentativa apenas do trecho inválido e auditoria; falha persistente aponta o trecho e preserva as propostas já salvas. Modo manual, pendências editoriais, transporte e conflitos de estado não são repetidos automaticamente.

- Fluxo principal automático: revisão pt-BR, segunda validação e autoaprovação registrada, tradução es-419, revisão bilíngue e geração/verificação dos dois Word. Modo manual preservado.
- Até quatro chamadas simultâneas por fase, salvamento por assinatura de trecho, parada com drenagem e retomada sem repetir fases válidas.
- Pendências, cobertura incompleta e alertas de consistência impedem entrega automática. Alterações manuais invalidam os checks/resultados afetados.


### Fluxo de livros

- Desconexões durante respostas HTTP encerram somente a requisição, sem traceback ou segunda resposta de erro; regressão com reset TCP real e resposta seguinte válida.

- Trabalhos independentes com importação Word, escopo integral ou por seções e estado durável.
- Revisão conservadora pt-BR com motivos, aprovação versionada, recusa, ajustes e reabertura.
- Tradução es-419 de todo o escopo aprovado, incluindo títulos, com glossário persistente editável e alertas.
- Background com progresso, limite, parada após o trecho atual, recuperação e retomada.
- Exportação sobre o Word original e inserção em cópia espanhola, preservando conteúdo fora do escopo, imagens e estilos.
- Interface para desktop/celular e acesso preservado à revisão anterior.
- Padrão explícito GPT 6.1 SOL low no Codex exec.
- Regressões de cobertura, mutações inválidas, bloqueio concorrente, seleção sumário/corpo e estrutura DOCX.

### Consolidação (05/10/2026)

- Uma interface React e um pacote Python, substituindo interfaces duplicadas e seis workspaces separados.
- API local e CLI única compartilham revisão, aprovação, recusa, tradução em lote, rollback e exportação.
- Removidos dashboard avançado, busca/curadoria web, polimento obrigatório, canais futuros e preview remoto.
- Mantidos dados, IDs, trilha editorial, glossário, consistência baseada em regras e exportação com manifestos.
- Corrigidos aprovação de revisão sem alterações, progresso real e proteção contra aprovação de tela desatualizada.
- Aprovação completa inclui parágrafos sem correções; prévia e aplicação usam a mesma ordem de substituições.
- Modelo usa a configuração atual do Codex por padrão, com override, timeout, sessão efêmera e diretório isolado em sandbox de leitura.
- Leitura e exportação de Word rejeitam DTDs; interface compilada independe da pasta de dados do livro.
- Startup único com portas configuráveis, proxy correto e encerramento de ambos os processos.
- Removidos componentes, assets e dependências não usados; CI inclui frontend e backend.

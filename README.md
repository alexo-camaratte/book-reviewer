# Revisor e tradutor de livros

Aplicativo local para revisar livros em português brasileiro, validar e aplicar as correções automaticamente, traduzir para espanhol da América Latina e revisar a tradução antes da entrega. O modo manual continua disponível. Importe Word, escolha livro inteiro ou seções e receba novas cópias em DOCX. O original permanece intacto.

## Versões

A versão atual fica em [VERSION](VERSION). Veja o [changelog](CHANGELOG.md), as [releases](https://github.com/alexo-camaratte/book-reviewer/releases) e o [fluxo de versões](RELEASES.md).

## Executar

Requisitos: Python 3.11+, Node 22+, pnpm 10.18.1 e Codex CLI instalado e autenticado.

```bash
pnpm --dir frontend install --frozen-lockfile
./scripts/dev.sh
```

Abra http://127.0.0.1:4173. A API usa 8766. `Ctrl+C` encerra os dois processos. Portas alternativas, sem encerrar outros aplicativos:

```bash
BACKEND_PORT=8786 FRONTEND_PORT=4193 ./scripts/dev.sh
```

Para servir a interface compilada com um processo:

```bash
pnpm --dir frontend build
./scripts/workspace-python.sh -m revisor.server
```

Abra http://127.0.0.1:8766. O servidor aceita somente conexões locais. `REVIEW_ROOT=/pasta/dados ./scripts/dev.sh` muda a pasta dos trabalhos; a interface continua vindo deste checkout.

## Instalar como aplicativo

Com o Revisor aberto em http://127.0.0.1:4173 (ou 8766), use "Instalar Revisor" no Chrome ou no Edge: o ícone de instalar fica na barra de endereço, ou no menu ⋮ → "Transmitir, salvar e compartilhar" → "Instalar página como app". O Revisor ganha janela própria, ícone e atalho no menu do sistema. O servidor local (`./scripts/dev.sh`) continua precisando estar rodando; o aplicativo instalado é a janela dele.

## Trabalhar com um livro

O cabeçalho identifica o autor pelo campo criador dos metadados do Word. Os downloads conservam o nome original e acrescentam ` REVISADO` antes de `.docx`; quando há um destino espanhol, a versão espanhola usa o nome desse arquivo. Livros concluídos recebem esses nomes sem repetir o processamento editorial.

1. **Novo livro**: selecione o manuscrito português `.docx` (até 32 MB). Para substituir seções em uma versão espanhola existente, indique também esse Word.
2. Confira **Escopo e critérios editoriais**. Livro inteiro inclui abertura, títulos, corpo, notas, cabeçalhos e rodapés com texto. Seções usam as ocorrências do corpo, preservando os demais capítulos. Salve as escolhas antes de começar.
3. **Processar livro completo** (ou **Processar seções selecionadas**) executa revisão pt-BR, segunda revisão comparando proposta/original, aplicação e aprovação automática registrada, tradução es-419 e revisão bilíngue comparando o espanhol com o português estabilizado. Até quatro chamadas simultâneas por etapa; só o glossário que você escreve é regra; as escolhas que o modelo faz ao traduzir viram dicas de consistência para os trechos que usam o mesmo termo, sem gerar alertas. Maiúsculas não criam escolhas duplicadas; expressões completas prevalecem sobre palavras contidas nelas e flexões de número/contrações são respeitadas.
4. Acompanhe as quatro contagens de parágrafos salvos: propostas em português, português aprovado, tradução e espanhol revisado. Parar aguarda as operações em andamento; continuar pula as fases válidas. O modo automático recebe uma versão completa por parágrafo, com motivos, e o código calcula as diferenças sem correções sobrepostas.
   Resposta inválida gera uma segunda tentativa daquele trecho com feedback e auditoria. Se continuar inválida, ou a segunda revisão encontrar uma pendência editorial, os outros trechos continuam. A tela lista cada pendência com um botão para conferir. A tradução aguarda todo o português aprovado; a entrega aguarda todo o espanhol revisado e os alertas resolvidos. Ambiguidades que já existem no original são preservadas, sem completar informações por inferência, e aparecem em Observações para o autor; falhas remanescentes das correções/traduções continuam bloqueando a entrega. Falhas do provedor e conflitos de dados interrompem a fila, preservando resultados já salvos.
5. Quando o processamento completo terminar, baixe **Word revisado em português** e **Word em espanhol**. Os dois arquivos já foram gerados e tiveram ZIP/XML verificados. Com destino espanhol, o app substitui as seções numa cópia desse destino.

Baixar uma entrega pronta usa o arquivo existente da revisão atual, sem gerar o Word novamente nem aguardar recarregar os dados da tela. O servidor continua recusando arquivos de uma revisão antiga.

**Modo manual** permite revisar pendentes ou um trecho, conferir/aprovar/recusar propostas, ajustar textos e gerar a tradução. Suas exportações continuam possíveis após aprovação/cobertura completas; a revisão bilíngue adicional pertence ao processamento completo. A interface distingue aprovação manual de aprovação automática após validação.
Os lotes rodam em background. Você acompanha o progresso, limita a quantidade de trechos e pode parar após o trecho atual. Reiniciar o servidor preserva o que já foi salvo; retomar pula os trechos concluídos. Mudanças no glossário liberam apenas as traduções afetadas para nova geração. Reabrir uma revisão invalida sua tradução.

Cada trabalho fica isolado em `.books/`, com originais, propostas, aprovações, ajustes, auditoria, progresso e manifestos.

## Modelo e limites

Padrão explícito: **GPT 6.1 SOL, esforço low**, inclusive no `codex exec`. `REVIEW_MODEL=nome ./scripts/dev.sh` permite override. Sessões efêmeras usam sandbox de leitura, JSON Schema e timeout de 300 segundos por trecho. Texto enviado ao Codex usa o provedor configurado nele.

O DOCX é editado sobre a estrutura original, preservando propriedades, imagens e tabelas. O novo texto pode alterar paginação. A inserção de seções com notas vinculadas é bloqueada com orientação para exportar separadamente; a revisão/tradução do livro inteiro mantém suas notas. A preservação de estrutura não equivale a uma garantia de diagramação idêntica em todos os editores Word.

A revisão é objetiva e conservadora. A segunda passagem da IA não é uma certificação de perfeição literária; a aprovação automática tem proveniência própria e não representa aceite humano. Glossário e contexto melhoram consistência, mas não substituem o aceite editorial do autor. Comece por um lote pequeno e confira o resultado antes do livro inteiro.

## Verificar

```bash
./scripts/test.sh
./scripts/ci.sh
./scripts/jail.sh ./scripts/test.sh
```

Os livros em `.books/` são operados pela interface e pela API local. Não regenere aprovações reais durante testes.

[Arquitetura](ARCHITECTURE.md) · [Operação](RUNBOOK.md) · [Próximos passos](TASKS.md) · [Evidências desta entrega](WORKFLOWS.md)

## Clonar em outra máquina

```bash
git clone --single-branch --branch main https://github.com/alexo-camaratte/book-reviewer.git
cd book-reviewer
pnpm --dir frontend install --frozen-lockfile
./scripts/dev.sh
```

A aplicação começa sem livros. Manuscritos, revisões, traduções, arquivos exportados, credenciais e registros pessoais não fazem parte desta distribuição. Importe seus Word pela interface. Para retomar um trabalho existente, transfira `.books` por um meio privado com os aplicativos encerrados; o Git não sincroniza esse andamento.

O endereço `127.0.0.1` pertence à máquina que executa o app. Estar na mesma rede não torna o servidor local acessível em outro computador.

A publicação em `main` tem histórico próprio de código. Não depende das branches usadas no desenvolvimento nem de caminhos pessoais. [Validação e distribuição](PUBLICATION.md).

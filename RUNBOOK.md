# Operação local

## Iniciar

Requisitos: Python 3.11+, Node 22+, pnpm 10.18.1 e Codex CLI instalado e autenticado.

```bash
pnpm --dir frontend install --frozen-lockfile
./scripts/dev.sh
```

Abra http://127.0.0.1:4173. Ctrl+C encerra API e Vite. Portas alternativas: `BACKEND_PORT=8786 FRONTEND_PORT=4193 ./scripts/dev.sh`. O servidor aceita conexões locais; cada computador precisa iniciar sua própria instância.

`REVIEW_ROOT=/pasta/privada ./scripts/dev.sh` escolhe a pasta dos dados. O código continua vindo do checkout atual. Não inicie dois servidores sobre a mesma `.books`.

## Processar

Importe o Word português e um destino espanhol opcional. Escolha livro inteiro ou seções, confira os critérios e salve. Processar livro completo ou Processar seções selecionadas executa as quatro fases e prepara ambos Word. Nenhum processamento começa apenas por iniciar o servidor.

As quatro barras representam o estado salvo. Parar aguarda operações em andamento. Continuar processamento ou Tentar os trechos pendentes reaproveita resultados válidos. O modo manual permite conferir propostas, ajustar textos e decidir aprovações.

Respostas inválidas têm no máximo duas tentativas por operação. Pendências mostram número/título/fase/motivo e deixam os demais trechos avançar. Português incompleto impede tradução; espanhol incompleto ou alertas remanescentes impedem entrega automática. Autenticação/transporte e conflitos de estado exigem atenção.

Observações para o autor registram ambiguidades preservadas do original; não autorizam inventar fatos. Correções e traduções com falhas remanescentes continuam bloqueando. As observações ficam na tela e no recibo junto aos Word.

## Dados e outra máquina

`.books/<uuid>/` contém cópias dos originais, estado, auditoria, checkpoints e entregáveis. Faça backup privado com o app encerrado. Para retomar em outro computador, transfira essa pasta por um meio privado e escolha o mesmo REVIEW_ROOT. Não publique dados ou credenciais no Git. Outra opção é importar novamente os Word e iniciar um trabalho novo.

Não altere JSON durante processamento, não regenere aprovações reais durante testes e não apague o lock para contornar outro servidor. Reabrir revisão invalida tradução/checks afetados. Alterar glossário ou contrato exige nova checagem. Downloads antigos são bloqueados quando a revisão mudou.

## Word

Os downloads são novas cópias. Inserção em destino espanhol preserva o conteúdo fora das seções escolhidas. A paginação pode variar. Inserção com notas vinculadas exige exportar as seções separadamente; livro inteiro mantém notas na estrutura original.

Na tela de livro pronto, baixar reutiliza o Word já gerado da revisão atual. No modo manual, a primeira exportação ainda prepara o Word; o download começa assim que ela termina, sem recarregar os dados da tela antes.

Testes e instalação pública usam documentos fictícios, sem dados pessoais.

## Verificar

```bash
./scripts/fast-check.sh
```

`fast-check.sh` (o mesmo do CI; `ci.sh` é atalho) verifica Python, testes unitários/HTTP, lint e build. Fora do CI, limita os workers de teste a 2 (`SHARE_WORKERS`) e espera o lock `~/.cache/gabriel-heavy.lock` antes do build, para não disputar a máquina com outros projetos. Bandit e o audit de dependências complementam os gates: `python3 scripts/dependency-audit.py` (precisa de `pip-audit` no Python usado e de rede) imprime um veredito por fonte (`ok`, `vulnerable`, `unavailable`, `failed`); vulnerabilidade ou audit quebrado falha, fonte fora do ar só avisa no CI. CI não publica nem processa manuscritos reais.

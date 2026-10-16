# Fluxos de livros

Importe um Word português e selecione livro inteiro ou seções. Para inserir as seções traduzidas em um Word espanhol existente, indique esse destino na importação. Ocorrências no sumário não substituem os títulos do corpo.

O processamento completo revisa e valida o português, registra aprovação automática, traduz e revisa o espanhol e gera novas cópias Word. O modo manual permite conferir propostas e decidir aprovações/exportações.

Cada importação cria um trabalho independente em `.books/<uuid>/`. O original fica preservado e a inserção mantém o conteúdo fora do escopo.

A interface mostra propostas, português aprovado, tradução e espanhol revisado em contagens separadas. Pendências indicam trecho e motivo. Retomar reaproveita resultados válidos; o startup não processa livros por conta própria.

Os dados são privados e locais. Clonar este repositório fornece código e testes fictícios, sem livros ou andamento. [Operação](RUNBOOK.md).

## Download sem nova exportação — 0.23.1

Os dois downloads prontos seguem diretamente para os arquivos da revisão atual. Quatro regressões de frontend cobrem português/espanhol sem nova exportação, geração sem entrega atual e erro de exportação; as duas primeiras falharam antes da correção. `scripts/ci.sh`: 123 testes Python, 15 testes de frontend, lint e build aprovados; os 123 testes Python também passaram em Python 3.11 no container existente, sem rede e com o checkout somente para leitura. Bandit 1.9.4 no backend sem achados.

Jev Browser oficial confirmou os dois downloads em fixture isolada com `workspace.export` configurado para falhar se fosse chamado novamente. Inspeção visual aprovada. Comandos nativos não chamaram modelo; Pruner dispensado porque o histórico inclui dados privados. Busca por caminhos e símbolos conhecidos usou `rg`; a referência `tool-routing.md` não existe na instalação das skills aplicadas. Dados, ambiente Python e sessão de smoke temporários foram removidos; mantidos somente o build atual e um recibo/screenshot pequenos fora do repositório. Nenhum push ou publicação realizado.

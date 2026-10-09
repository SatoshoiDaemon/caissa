# Regras de xadrez

Este documento descreve o estado atual das regras do xadrez no motor de Caissa.

Ele serve como referência para futuras explorações do projeto. Uma regra marcada
como não implementada é apenas uma lacuna conhecida do motor; não representa um
backlog obrigatório nem uma promessa de conclusão.

## Movimentos implementados

O motor já reconhece os movimentos normais de:

- rei;
- dama;
- torre;
- bispo;
- cavalo;
- peão.

Também estão implementados:

- capturas;
- bloqueio de peças deslizantes por outras peças;
- movimento inicial de duas casas do peão;
- promoção do peão para dama, torre, bispo ou cavalo;
- captura en passant;
- roque pequeno e grande;
- alternância de turnos;
- rejeição de movimentos que deixam o próprio rei em xeque.

## Estados e finais implementados

- xeque;
- xeque-mate;
- afogamento;
- desistência;
- empate por oferta e aceitação;
- derrota por tempo;
- abandono por desconexão prolongada.

O serviço de partidas também persiste o resultado e o vencedor quando uma
partida termina.

## Regras de empate implementadas

### Material insuficiente

O motor detecta automaticamente posições em que nenhum dos jogadores pode dar
xeque-mate por material disponível. Os casos cobertos são:

- rei contra rei;
- rei e bispo contra rei;
- rei e cavalo contra rei;
- posições com bispos que não podem criar um xeque-mate.

Essa análise é conservadora: posições mais complexas com múltiplas peças
menores continuam sendo tratadas como partidas ativas.

### Repetição de posição

O motor identifica a terceira ocorrência de uma mesma posição e encerra a
partida automaticamente.

Para comparar posições corretamente, não basta comparar o desenho do tabuleiro.
Também precisam ser considerados:

- o jogador que deve mover;
- os direitos de roque;
- o alvo de en passant, quando ele for relevante para uma captura possível.

O histórico persistido mantém chaves de posição para que a contagem sobreviva a
reinícios.

### Regra dos 50 movimentos

O campo `halfmove_clock` já é mantido no estado e no FEN. Ele é zerado depois
de um movimento de peão ou de uma captura e incrementado nos demais casos.

O serviço encerra automaticamente a partida quando o contador chega a 100
meio-movimentos.

### Regra dos 75 movimentos

O contador existente poderia servir de base para a regra automática dos 75
movimentos de cada lado, mas esse encerramento ainda não existe no serviço de
partidas.

### Cinco repetições

O motor ainda não possui contagem de posições repetidas para reconhecer o
encerramento automático causado por cinco ocorrências da mesma posição.

## Validação de posições

O carregamento de FEN já valida:

- os seis campos;
- o tabuleiro com oito fileiras;
- oito casas por fileira;
- peças válidas;
- exatamente um rei de cada cor;
- jogador ativo;
- direitos de roque sem caracteres duplicados ou desconhecidos;
- alvo de en passant com formato válido;
- contadores numéricos válidos.

Ainda não há validação semântica completa para situações como:

- reis adjacentes;
- direitos de roque incompatíveis com a presença do rei ou da torre;
- peões na primeira ou na última fileira;
- posições em que os dois reis estão simultaneamente em xeque;
- coerência histórica do alvo de en passant;
- posições impossíveis de alcançar a partir de uma partida legal.

Nem toda posição FEN estruturalmente válida precisa ser uma posição alcançável
em uma partida real. Essa distinção pode ser útil caso o projeto explore um
validador mais rigoroso.

## Recursos relacionados implementados

Estes itens não são movimentos adicionais, mas se relacionam diretamente com o
histórico e a representação das partidas:

- notação algébrica (SAN), como `Nf3`, `O-O`, `exd6+` e `a8=Q#`;

## Recursos relacionados ainda ausentes

- exportação e importação de PGN pela interface visual;
- desfazer e refazer movimentos;
- edição de uma partida existente a partir de PGN;
- reivindicação manual de empate;
- comparação e restauração de posições históricas.

## Fora do xadrez clássico atual

Não fazem parte das regras clássicas que o motor tenta representar hoje:

- Chess960;
- antichess;
- chess boxing ou outras variantes externas;
- peças fairy;
- tabuleiros diferentes de 8x8;
- posições com mais de uma dama promovida por lado como caso especial — o motor
  pode representar essas peças, mas ainda não oferece uma interface específica
  para administrá-las.

## Referências no código

- Regras de movimento e estado: `src/backend/chess_logic/chess_game.py`.
- Decisão de xeque-mate e afogamento: `src/backend/services/game_service.py`.
- Casos cobertos diretamente: `tests/unit/test_chess_logic.py`.

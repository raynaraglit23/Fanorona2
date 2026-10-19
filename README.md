# Fanorona - Projeto RPC (Python)

Projeto da disciplina de Programação Paralela e Distribuída (IFCE) — Projeto de RMI/RPC.
Toda a comunicação entre os tabuleiros é feita por **chamada de procedimento remoto (RPC)**
com o módulo `xmlrpc` da biblioteca padrão do Python. O código do jogo não usa sockets
nem monta mensagens: chama funções.

## Arquivos

| Arquivo | Papel |
|---|---|
| `interface.py` | **Interfaces remotas** = contrato cliente/servidor. `FanoronaInterface` (o que o servidor oferece: `registrar`, `mover`, `desistir`, `enviar_chat`, `obter_estado`, `sair`) e `ClienteInterface` (callbacks: `receber_estado`, `receber_chat`) |
| `servidor.py` | `FanoronaServico` implementa o contrato e é publicado via RPC (porta 9090) |
| `cliente.py` | Tabuleiro (Tkinter). Faz `servidor.mover(...)` direto e implementa os callbacks |
| `jogo.py` | Regras do Fanorona (a mesma lógica da versão com sockets, sem alterações) |
| `teste_jogo.py`, `teste_rpc.py` | Testes da lógica e de integração via RPC |

## Fluxo

1. O servidor publica o objeto `FanoronaServico`. Cada método público dele é um procedimento remoto.
2. O cliente sobe um pequeno servidor RPC próprio (callbacks) e chama `servidor.registrar(url)`; recebe o número do jogador (1 ou 2).
3. Quando um jogador clica, o cliente executa `servidor.mover(jogador, origem, destino)`.
   O servidor valida com `Jogo` e chama `receber_estado(...)` no tabuleiro **dos dois jogadores**.
4. Chat e desistência seguem o mesmo padrão (`enviar_chat`, `desistir`).

## Como executar

Requer Python 3 com Tkinter (macOS: `brew install python` e `brew install python-tk@3.14`).
Nenhuma biblioteca extra.

```bash
python3 servidor.py      # terminal 1
python3 cliente.py       # terminal 2 (jogador 1)
python3 cliente.py       # terminal 3 (jogador 2)
```

Em computadores diferentes, informe o IP do servidor e o IP da própria máquina do cliente
(o servidor precisa dele para fazer o callback):

```bash
python3 cliente.py 192.168.0.10 192.168.0.20
#                  ip do servidor  ip deste cliente
```

Libere a porta 9090 (servidor) e portas TCP de entrada no cliente se houver firewall.

## Testes

```bash
python3 teste_jogo.py
python3 servidor.py &     # em outro terminal
python3 teste_rpc.py
```

## Funcionalidades

- Controle de turno (Jogador 1 começa; a partida só inicia com os dois conectados)
- Movimentação, captura por aproximação/afastamento e sequência de capturas
- Desistência (fechar a janela no meio da partida também conta como desistência)
- Chat durante toda a partida
- Indicação de vencedor

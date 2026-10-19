# -*- coding: utf-8 -*-
"""
INTERFACES REMOTAS (contrato entre cliente e servidor).

Aqui só ficam as ASSINATURAS dos procedimentos remotos. O servidor implementa
FanoronaInterface; o cliente implementa ClienteInterface (callbacks).
Quem chama um procedimento remoto usa o nome do método como se fosse uma função
local; o RPC leva a chamada até a outra máquina e devolve o resultado.
"""
from abc import ABC, abstractmethod

PORTA_SERVIDOR = 9090


class FanoronaInterface(ABC):
    """Procedimentos que o SERVIDOR oferece aos clientes."""

    @abstractmethod
    def registrar(self, url_cliente):
        """Entra na partida informando a URL dos callbacks do cliente.
        Retorna 1 ou 2 (número do jogador) ou 0 se a partida estiver cheia."""

    @abstractmethod
    def mover(self, jogador, origem, destino):
        """Move uma peça de origem [linha, coluna] para destino [linha, coluna].
        Retorna {"ok": bool, "mensagem": str}."""

    @abstractmethod
    def desistir(self, jogador):
        """O jogador desiste. Retorna {"ok": bool, "mensagem": str}."""

    @abstractmethod
    def enviar_chat(self, jogador, mensagem):
        """Envia uma mensagem de chat para os dois jogadores."""

    @abstractmethod
    def obter_estado(self):
        """Retorna o estado atual da partida (dict)."""

    @abstractmethod
    def sair(self, jogador):
        """O jogador saiu (fechou a janela)."""


class ClienteInterface(ABC):
    """Procedimentos que o CLIENTE oferece ao servidor (callbacks)."""

    @abstractmethod
    def receber_estado(self, estado, aviso):
        """O servidor avisa que o estado da partida mudou."""

    @abstractmethod
    def receber_chat(self, jogador, mensagem):
        """O servidor entrega uma mensagem de chat."""

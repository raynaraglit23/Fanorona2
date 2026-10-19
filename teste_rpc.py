# -*- coding: utf-8 -*-
"""Teste de integração: dois 'clientes' sem interface chamando o servidor por RPC.
Execute com o servidor já rodando:  python3 teste_rpc.py"""
import threading
import time
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn

from interface import ClienteInterface, PORTA_SERVIDOR


class Srv(ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True


class Cli(ClienteInterface):
    def __init__(self):
        self.ultimo = None
        self.chats = []
        self.srv = Srv(("127.0.0.1", 0), allow_none=True, logRequests=False)
        self.srv.register_instance(self)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def receber_estado(self, estado, aviso):
        self.ultimo = estado
        return True

    def receber_chat(self, jogador, mensagem):
        self.chats.append((jogador, mensagem))
        return True


def main():
    s = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{PORTA_SERVIDOR}", allow_none=True)
    a, b, c = Cli(), Cli(), Cli()

    assert s.registrar(a.url) == 1, "primeiro vira jogador 1"
    assert not s.mover(1, [2, 3], [2, 4])["ok"], "não pode mover antes do adversário entrar"
    assert s.registrar(b.url) == 2, "segundo vira jogador 2"
    assert s.registrar(c.url) == 0, "terceiro é recusado"
    assert s.obter_estado()["iniciado"]

    assert not s.mover(2, [2, 5], [2, 4])["ok"], "jogador 2 fora de turno"
    r = s.mover(1, [2, 3], [2, 4])
    assert r["ok"], r["mensagem"]

    time.sleep(0.5)
    assert b.ultimo and b.ultimo["turno"] == 2 and b.ultimo["pecas2"] == 18, "callback de estado"

    s.enviar_chat(1, "oi!")
    time.sleep(0.5)
    assert (1, "oi!") in b.chats, "chat entregue ao jogador 2"

    assert s.desistir(2)["ok"]
    fim = s.obter_estado()
    assert fim["finalizado"] and fim["vencedor"] == 1, "vencedor = jogador 1"

    s.sair(1); s.sair(2)
    novo = s.obter_estado()
    assert not novo["finalizado"] and novo["pecas1"] == 22, "nova partida preparada"
    print("Teste RPC OK")


if __name__ == "__main__":
    main()

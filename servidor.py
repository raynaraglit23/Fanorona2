# -*- coding: utf-8 -*-
"""
Servidor Fanorona via RPC (XML-RPC da biblioteca padrão do Python).

Uso:  python3 servidor.py
"""
import queue
import threading
import xmlrpc.client
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer

from interface import FanoronaInterface, PORTA_SERVIDOR
from jogo import Jogo, JOGADOR_1, JOGADOR_2


class TransporteComTimeout(xmlrpc.client.Transport):
    """Evita que um cliente travado prenda o servidor."""
    def __init__(self, timeout=3):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conexao = super().make_connection(host)
        conexao.timeout = self._timeout
        return conexao


class FanoronaServico(FanoronaInterface):
    """Objeto remoto: implementa o contrato. Cada método público é um procedimento remoto."""

    def __init__(self):
        self.jogo = Jogo()
        self.clientes = {}              # jogador -> url dos callbacks
        self.lock = threading.RLock()   # o servidor atende cada chamada em uma thread
        self.fila = queue.Queue()       # notificações saem em ordem, fora do lock
        threading.Thread(target=self._notificador, daemon=True).start()

    # ---------------------------------------------------------- uso interno (não exposto)
    def _iniciada(self):
        return len(self.clientes) == 2

    def _estado(self):
        estado = self.jogo.estado()
        estado["iniciado"] = self._iniciada()
        return estado

    def _notificador(self):
        while True:
            url, metodo, args = self.fila.get()
            try:
                proxy = xmlrpc.client.ServerProxy(
                    url, allow_none=True, transport=TransporteComTimeout())
                getattr(proxy, metodo)(*args)       # chamada remota no cliente (callback)
            except Exception as e:
                print(f"Falha ao notificar {url}: {e}")

    def _notificar_estado(self, aviso=""):
        estado = self._estado()
        for url in list(self.clientes.values()):
            self.fila.put((url, "receber_estado", (estado, aviso)))

    # ---------------------------------------------------------- procedimentos remotos
    def registrar(self, url_cliente):
        with self.lock:
            if len(self.clientes) >= 2:
                return 0
            jogador = JOGADOR_1 if JOGADOR_1 not in self.clientes else JOGADOR_2
            self.clientes[jogador] = url_cliente
            print(f"Jogador {jogador} conectado: {url_cliente}")

            if self._iniciada():
                print("Dois jogadores conectados. Partida iniciada.")
                self._notificar_estado("Os dois jogadores estão conectados. Jogador 1 começa. Bom jogo!")
            else:
                self._notificar_estado("Aguardando o adversário se conectar...")
            return jogador

    def mover(self, jogador, origem, destino):
        with self.lock:
            if not self._iniciada():
                return {"ok": False, "mensagem": "Aguardando o adversário se conectar."}

            ok, texto, _ = self.jogo.mover(jogador, tuple(origem), tuple(destino))
            if ok:
                self._notificar_estado(texto)
            return {"ok": ok, "mensagem": texto}

    def desistir(self, jogador):
        with self.lock:
            if not self._iniciada():
                return {"ok": False, "mensagem": "Aguardando o adversário se conectar."}

            ok, texto, _ = self.jogo.desistir(jogador)
            if ok:
                self._notificar_estado(texto)
            return {"ok": ok, "mensagem": texto}

    def enviar_chat(self, jogador, mensagem):
        texto = str(mensagem).strip()
        if not texto:
            return True
        with self.lock:
            for url in list(self.clientes.values()):
                self.fila.put((url, "receber_chat", (jogador, texto)))
        return True

    def obter_estado(self):
        with self.lock:
            return self._estado()

    def sair(self, jogador):
        with self.lock:
            if self.clientes.pop(jogador, None) is None:
                return True
            print(f"Jogador {jogador} saiu.")

            # Sair no meio da partida conta como desistência.
            if not self.jogo.finalizado and len(self.clientes) == 1:
                self.jogo.desistir(jogador)
                self._notificar_estado(f"Jogador {jogador} saiu da partida.")

            # Sem ninguém conectado, prepara uma nova partida.
            if not self.clientes:
                self.jogo = Jogo()
                print("Nova partida preparada.")
            return True


class ServidorRPC(ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    servidor = ServidorRPC(("0.0.0.0", PORTA_SERVIDOR), allow_none=True, logRequests=False)
    servidor.register_instance(FanoronaServico())

    print("=" * 50)
    print("        SERVIDOR FANORONA (RPC)")
    print("=" * 50)
    print(f"Servidor registrado na porta {PORTA_SERVIDOR}. Aguardando jogadores...")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()

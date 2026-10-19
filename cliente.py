# -*- coding: utf-8 -*-
"""
Cliente (tabuleiro) do Fanorona via RPC.

Não há sockets nem mensagens montadas à mão: o cliente chama os procedimentos
do servidor como funções (servidor.mover(...)) e implementa ClienteInterface
para receber os avisos do servidor (callbacks).

Uso:  python3 cliente.py [ip-do-servidor] [ip-desta-maquina]
"""
import queue
import sys
import threading
import xmlrpc.client
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer
import tkinter as tk
from tkinter import messagebox

from interface import ClienteInterface, PORTA_SERVIDOR


class ServidorCallback(ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True
    allow_reuse_address = True


class ClienteFanorona(ClienteInterface):
    def __init__(self, root, host, meu_ip):
        self.root = root
        self.jogador = None
        self.estado = None
        self.selecionada = None
        self.fim_mostrado = False
        # Threads do RPC não mexem na interface: deixam eventos nesta fila,
        # que é lida pela thread do Tkinter.
        self.eventos = queue.Queue()

        self.root.title("Fanorona - Cliente")
        self.root.geometry("1050x700")
        self.root.minsize(900, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.fechar)

        self.montar_interface()
        self.root.after(50, self.processar_eventos)

        try:
            self.conectar(host, meu_ip)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível conectar ao servidor.\n\n{e}")
            self.root.destroy()

    # ------------------------------------------------------------------ conexão (RPC)
    def conectar(self, host, meu_ip):
        # 1) Oferece os callbacks que o servidor poderá chamar neste cliente.
        self.callbacks = ServidorCallback(("0.0.0.0", 0), allow_none=True, logRequests=False)
        self.callbacks.register_instance(self)
        porta = self.callbacks.server_address[1]
        threading.Thread(target=self.callbacks.serve_forever, daemon=True).start()
        url_callback = f"http://{meu_ip}:{porta}"

        # 2) Obtém o "stub" do servidor: a partir daqui, é só chamar as funções.
        self.url_servidor = f"http://{host}:{PORTA_SERVIDOR}"
        self.servidor = xmlrpc.client.ServerProxy(self.url_servidor, allow_none=True)

        self.jogador = self.servidor.registrar(url_callback)       # procedimento remoto
        if self.jogador == 0:
            messagebox.showerror("Erro", "A partida já está cheia.")
            self.root.destroy()
            return

        self.root.title(f"Fanorona - Jogador {self.jogador}")
        self.adicionar_chat(f"Sistema: Você é o Jogador {self.jogador}.")
        self.estado = self.servidor.obter_estado()                  # procedimento remoto
        self.atualizar_interface()

    def agendar(self, funcao, *args):
        """Pode ser chamado de qualquer thread."""
        self.eventos.put((funcao, args))

    def processar_eventos(self):
        try:
            while True:
                funcao, args = self.eventos.get_nowait()
                funcao(*args)
        except queue.Empty:
            pass
        self.root.after(50, self.processar_eventos)

    def chamar(self, funcao, *args, ao_terminar=None):
        """Faz a chamada remota fora da thread da interface para não travar a janela."""
        def tarefa():
            try:
                # Um proxy por thread: ServerProxy não é thread-safe.
                proxy = xmlrpc.client.ServerProxy(self.url_servidor, allow_none=True)
                resultado = getattr(proxy, funcao)(*args)
                if ao_terminar:
                    self.agendar(ao_terminar, resultado)
            except Exception as e:
                self.agendar(self.adicionar_chat,
                             f"Sistema: erro de comunicação com o servidor ({e})")
        threading.Thread(target=tarefa, daemon=True).start()

    # ------------------------------------------------------------------ callbacks (servidor -> cliente)
    def receber_estado(self, estado, aviso):
        self.agendar(self._aplicar_estado, estado, aviso)
        return True

    def receber_chat(self, jogador, mensagem):
        self.agendar(self.adicionar_chat, f"Jogador {jogador}: {mensagem}")
        return True

    def _aplicar_estado(self, estado, aviso):
        self.estado = estado
        self.selecionada = None
        self.atualizar_interface()

        if aviso:
            self.adicionar_chat("Sistema: " + aviso)

        if estado["finalizado"] and not self.fim_mostrado:
            self.fim_mostrado = True
            vencedor = estado["vencedor"]
            texto = "Você venceu!" if vencedor == self.jogador else f"Jogador {vencedor} venceu!"
            messagebox.showinfo("Fim de jogo", texto)

    # ------------------------------------------------------------------ interface
    def montar_interface(self):
        topo = tk.Frame(self.root, padx=15, pady=12)
        topo.pack(fill="x")

        tk.Label(topo, text="FANORONA", font=("Helvetica", 24, "bold")).pack(side="left")
        self.status = tk.Label(topo, text="Conectando...", font=("Helvetica", 13, "bold"))
        self.status.pack(side="right")

        principal = tk.Frame(self.root, padx=15, pady=5)
        principal.pack(fill="both", expand=True)

        esquerda = tk.Frame(principal)
        esquerda.pack(side="left", fill="both", expand=True)

        direita = tk.Frame(principal, width=300)
        direita.pack(side="right", fill="y")
        direita.pack_propagate(False)

        self.canvas = tk.Canvas(esquerda, bg="#ead7b7", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.clicar_tabuleiro)
        self.canvas.bind("<Configure>", lambda e: self.desenhar_tabuleiro())

        tk.Label(direita, text="CHAT", font=("Helvetica", 16, "bold")).pack(pady=(0, 8))

        self.chat = tk.Text(direita, state="disabled", wrap="word", height=20)
        self.chat.pack(fill="both", expand=True)

        entrada = tk.Frame(direita, pady=8)
        entrada.pack(fill="x")

        self.entrada_chat = tk.Entry(entrada)
        self.entrada_chat.pack(side="left", fill="x", expand=True)
        self.entrada_chat.bind("<Return>", lambda e: self.enviar_chat())
        tk.Button(entrada, text="Enviar", command=self.enviar_chat).pack(side="right", padx=(5, 0))

        self.info = tk.Label(direita, text="", justify="left", anchor="w", font=("Helvetica", 11))
        self.info.pack(fill="x", pady=8)

        self.btn_desistir = tk.Button(direita, text="DESISTIR", command=self.desistir, height=2)
        self.btn_desistir.pack(fill="x", pady=(5, 0))

        tk.Label(self.root, text="Clique em uma peça e depois no destino.", pady=7).pack(fill="x")

    def atualizar_interface(self):
        self.desenhar_tabuleiro()
        if not self.estado:
            return

        turno = self.estado["turno"]
        if self.estado["finalizado"]:
            self.status.config(text="PARTIDA ENCERRADA")
        elif not self.estado.get("iniciado"):
            self.status.config(text="AGUARDANDO ADVERSÁRIO")
        elif turno == self.jogador:
            self.status.config(text="SUA VEZ")
        else:
            self.status.config(text=f"VEZ DO JOGADOR {turno}")

        self.info.config(text=(
            f"Você: Jogador {self.jogador}\n"
            f"Peças - J1: {self.estado['pecas1']} | J2: {self.estado['pecas2']}\n"
            f"Turno: Jogador {turno}"
        ))

    def geometria(self):
        tab = self.estado["tabuleiro"]
        linhas, colunas = len(tab), len(tab[0])
        w = max(self.canvas.winfo_width(), 500)
        h = max(self.canvas.winfo_height(), 400)
        margem = 45
        espacox = (w - 2 * margem) / (colunas - 1)
        espacoy = (h - 2 * margem) / (linhas - 1)
        return linhas, colunas, margem, espacox, espacoy

    def peca_em_sequencia(self):
        """Peça que deve continuar capturando (turno ainda não terminou), se houver."""
        e = self.estado
        if e["finalizado"] or not e["capturas_no_turno"]:
            return None
        return tuple(e["capturas_no_turno"][-1]["destino"])

    def desenhar_tabuleiro(self):
        self.canvas.delete("all")
        if not self.estado:
            return

        tab = self.estado["tabuleiro"]
        linhas, colunas, margem, espacox, espacoy = self.geometria()

        def ponto(l, c):
            return margem + c * espacox, margem + l * espacoy

        for l in range(linhas):
            for c in range(colunas - 1):
                x1, y1 = ponto(l, c); x2, y2 = ponto(l, c + 1)
                self.canvas.create_line(x1, y1, x2, y2, width=2)
        for c in range(colunas):
            for l in range(linhas - 1):
                x1, y1 = ponto(l, c); x2, y2 = ponto(l + 1, c)
                self.canvas.create_line(x1, y1, x2, y2, width=2)
        for l in range(linhas - 1):
            for c in range(colunas - 1):
                x1, y1 = ponto(l, c); x2, y2 = ponto(l + 1, c + 1)
                self.canvas.create_line(x1, y1, x2, y2, width=1)
                x1, y1 = ponto(l, c + 1); x2, y2 = ponto(l + 1, c)
                self.canvas.create_line(x1, y1, x2, y2, width=1)

        seq = self.peca_em_sequencia()
        raio = 14
        for l in range(linhas):
            for c in range(colunas):
                x, y = ponto(l, c)

                if self.selecionada == (l, c) or seq == (l, c):
                    self.canvas.create_oval(x - 21, y - 21, x + 21, y + 21,
                                            outline="#d4a72c", width=4)

                self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#3f3f3f", outline="")

                peca = tab[l][c]
                if peca != 0:
                    self.canvas.create_oval(
                        x - raio, y - raio, x + raio, y + raio,
                        fill="#f7f1df" if peca == 1 else "#333333",
                        outline="#333333" if peca == 1 else "#111111", width=2)

    def clicar_tabuleiro(self, event):
        e = self.estado
        if not e or e["finalizado"] or not e.get("iniciado") or e["turno"] != self.jogador:
            return

        linhas, colunas, margem, espacox, espacoy = self.geometria()
        c = round((event.x - margem) / espacox)
        l = round((event.y - margem) / espacoy)

        if not (0 <= l < linhas and 0 <= c < colunas):
            return
        if abs(event.x - (margem + c * espacox)) > 25 or abs(event.y - (margem + l * espacoy)) > 25:
            return

        if self.selecionada is None:
            if e["tabuleiro"][l][c] == self.jogador:
                self.selecionada = (l, c)
                self.desenhar_tabuleiro()
        else:
            origem, destino = self.selecionada, (l, c)
            self.selecionada = None
            self.desenhar_tabuleiro()
            if origem == destino:
                return
            # Procedimento remoto: o servidor valida a jogada com a classe Jogo.
            self.chamar("mover", self.jogador, list(origem), list(destino),
                        ao_terminar=self.mostrar_se_erro)

    def mostrar_se_erro(self, resultado):
        if not resultado["ok"]:
            self.adicionar_chat("Sistema: " + resultado["mensagem"])

    def enviar_chat(self):
        texto = self.entrada_chat.get().strip()
        if not texto:
            return
        self.entrada_chat.delete(0, "end")
        self.chamar("enviar_chat", self.jogador, texto)

    def adicionar_chat(self, texto):
        self.chat.config(state="normal")
        self.chat.insert("end", texto + "\n")
        self.chat.see("end")
        self.chat.config(state="disabled")

    def desistir(self):
        if not self.estado or self.estado["finalizado"]:
            return
        if messagebox.askyesno("Desistir", "Tem certeza que deseja desistir?"):
            self.chamar("desistir", self.jogador, ao_terminar=self.mostrar_se_erro)

    def fechar(self):
        try:
            if self.jogador:
                self.servidor.sair(self.jogador)       # procedimento remoto
        except Exception:
            pass
        self.root.destroy()


def main():
    host = sys.argv[1] if len(sys.argv) >= 2 else "127.0.0.1"
    meu_ip = sys.argv[2] if len(sys.argv) >= 3 else "127.0.0.1"

    root = tk.Tk()
    ClienteFanorona(root, host, meu_ip)
    root.mainloop()


if __name__ == "__main__":
    main()

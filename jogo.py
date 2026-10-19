# -*- coding: utf-8 -*-
"""
Regras e estado do Fanorona.

A classe Jogo fica no servidor. Os clientes apenas exibem o estado
e enviam as jogadas solicitadas pelo jogador.
"""

VAZIO = 0
JOGADOR_1 = 1
JOGADOR_2 = 2

LINHAS = 5
COLUNAS = 9

# Ligações do tabuleiro Fanorona 5x9.
# Cada ponto possui vizinhos ortogonais e diagonais quando a linha
# correspondente existe no tabuleiro.
def criar_conexoes():
    conexoes = {}
    for l in range(LINHAS):
        for c in range(COLUNAS):
            vizinhos = []
            for dl in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dl == 0 and dc == 0:
                        continue
                    nl, nc = l + dl, c + dc
                    if 0 <= nl < LINHAS and 0 <= nc < COLUNAS:
                        # Nas linhas ímpares, usamos apenas diagonais
                        # que representam as diagonais desenhadas no tabuleiro.
                        if dl != 0 and dc != 0:
                            if (l % 2 == 1):
                                # Pontos centrais das linhas horizontais
                                # possuem as diagonais da malha.
                                pass
                        vizinhos.append((nl, nc))
            conexoes[(l, c)] = vizinhos
    return conexoes

CONEXOES = criar_conexoes()


class Jogo:
    def __init__(self):
        self.tabuleiro = self.tabuleiro_inicial()
        self.turno = JOGADOR_1
        self.vencedor = None
        self.finalizado = False
        self.capturas_no_turno = []
        self.posicoes_visitadas = set()

    @staticmethod
    def tabuleiro_inicial():
        # Configuração simplificada e tradicional:
        # 22 peças para cada jogador e o centro vazio.
        t = [[JOGADOR_1 for _ in range(COLUNAS)] for _ in range(2)]
        t += [[JOGADOR_1 for _ in range(COLUNAS)]]
        t += [[JOGADOR_2 for _ in range(COLUNAS)] for _ in range(2)]
        # Ajustes para totalizar 22 peças de cada jogador.
        t[2][0] = JOGADOR_1
        t[2][1] = JOGADOR_1
        t[2][2] = JOGADOR_1
        t[2][3] = JOGADOR_1
        t[2][4] = VAZIO
        t[2][5] = JOGADOR_2
        t[2][6] = JOGADOR_2
        t[2][7] = JOGADOR_2
        t[2][8] = JOGADOR_2

        # Contagem: jogador 1 = 18 + 4 = 22; jogador 2 = 18 + 4 = 22.
        return t

    def outro(self, jogador):
        return JOGADOR_2 if jogador == JOGADOR_1 else JOGADOR_1

    def dentro(self, p):
        l, c = p
        return 0 <= l < LINHAS and 0 <= c < COLUNAS

    def vizinhos(self, p):
        return CONEXOES.get(p, [])

    def contar(self, jogador):
        return sum(celula == jogador for linha in self.tabuleiro for celula in linha)

    def estado(self):
        return {
            "tabuleiro": self.tabuleiro,
            "turno": self.turno,
            "vencedor": self.vencedor,
            "finalizado": self.finalizado,
            "pecas1": self.contar(JOGADOR_1),
            "pecas2": self.contar(JOGADOR_2),
            "capturas_no_turno": self.capturas_no_turno,
        }

    def reiniciar_sequencia(self):
        self.capturas_no_turno = []
        self.posicoes_visitadas = set()

    def caminho_direcao(self, origem, destino):
        dl = destino[0] - origem[0]
        dc = destino[1] - origem[1]
        return (0 if dl == 0 else (1 if dl > 0 else -1),
                0 if dc == 0 else (1 if dc > 0 else -1))

    def captura_aproximacao(self, jogador, origem, destino):
        """
        Após mover para destino, verifica peças adversárias na mesma
        direção do movimento, a partir de destino.
        """
        adversario = self.outro(jogador)
        dl, dc = self.caminho_direcao(origem, destino)
        p = (destino[0] + dl, destino[1] + dc)
        capturadas = []

        while self.dentro(p) and self.tabuleiro[p[0]][p[1]] == adversario:
            capturadas.append(p)
            p = (p[0] + dl, p[1] + dc)

        for l, c in capturadas:
            self.tabuleiro[l][c] = VAZIO
        return capturadas

    def captura_afastamento(self, jogador, origem, destino):
        """
        Após mover para destino, verifica peças adversárias na direção
        oposta ao movimento, partindo da origem.
        """
        adversario = self.outro(jogador)
        dl, dc = self.caminho_direcao(origem, destino)
        p = (origem[0] - dl, origem[1] - dc)
        capturadas = []

        while self.dentro(p) and self.tabuleiro[p[0]][p[1]] == adversario:
            capturadas.append(p)
            p = (p[0] - dl, p[1] - dc)

        for l, c in capturadas:
            self.tabuleiro[l][c] = VAZIO
        return capturadas

    def capturas_possiveis(self, jogador, posicao):
        """
        Retorna destinos vizinhos para os quais há captura por aproximação
        ou afastamento. Esta função é usada durante uma sequência.
        """
        resultado = []
        for destino in self.vizinhos(posicao):
            if self.tabuleiro[destino[0]][destino[1]] != VAZIO:
                continue

            dl, dc = self.caminho_direcao(posicao, destino)
            adversario = self.outro(jogador)

            # Aproximação: adversário imediatamente depois do destino.
            p = (destino[0] + dl, destino[1] + dc)
            aproximacao = self.dentro(p) and self.tabuleiro[p[0]][p[1]] == adversario

            # Afastamento: adversário imediatamente atrás da origem.
            p2 = (posicao[0] - dl, posicao[1] - dc)
            afastamento = self.dentro(p2) and self.tabuleiro[p2[0]][p2[1]] == adversario

            if aproximacao or afastamento:
                if destino not in self.posicoes_visitadas:
                    resultado.append(destino)

        return resultado

    def mover(self, jogador, origem, destino):
        if self.finalizado:
            return False, "A partida já terminou.", self.estado()

        if jogador != self.turno:
            return False, "Não é a sua vez.", self.estado()

        if not (self.dentro(origem) and self.dentro(destino)):
            return False, "Posição inválida.", self.estado()

        if self.tabuleiro[origem[0]][origem[1]] != jogador:
            return False, "A posição inicial não possui uma peça sua.", self.estado()

        if self.tabuleiro[destino[0]][destino[1]] != VAZIO:
            return False, "A posição de destino está ocupada.", self.estado()

        if destino not in self.vizinhos(origem):
            return False, "Movimento inválido: as posições não são vizinhas.", self.estado()

        # Uma nova peça só pode iniciar a jogada normalmente.
        # Durante sequência, somente a mesma peça continua.
        if self.capturas_no_turno:
            ultima = tuple(self.capturas_no_turno[-1]["destino"])
            if tuple(origem) != ultima:
                return False, "Durante uma sequência de captura, mova a mesma peça.", self.estado()

        if not self.capturas_no_turno:
            self.posicoes_visitadas = {tuple(origem)}

        # Move a peça.
        self.tabuleiro[destino[0]][destino[1]] = jogador
        self.tabuleiro[origem[0]][origem[1]] = VAZIO

        aproximacao = self.captura_aproximacao(jogador, origem, destino)
        afastamento = self.captura_afastamento(jogador, origem, destino)

        capturadas = aproximacao if aproximacao else afastamento

        movimento = {
            "origem": list(origem),
            "destino": list(destino),
            "capturadas": [list(p) for p in capturadas],
            "tipo_captura": (
                "aproximacao" if aproximacao else
                "afastamento" if afastamento else
                "nenhuma"
            )
        }
        self.capturas_no_turno.append(movimento)
        self.posicoes_visitadas.add(tuple(destino))

        # Vitória.
        adversario = self.outro(jogador)
        if self.contar(adversario) == 0:
            self.vencedor = jogador
            self.finalizado = True
            return True, "Vitória!", self.estado()

        # Se capturou, verifica continuação.
        if capturadas:
            proximas = self.capturas_possiveis(jogador, destino)
            if proximas:
                return True, "Captura realizada. Você pode continuar.", self.estado()

        # Sem continuação: encerra turno.
        self.turno = adversario
        self.reiniciar_sequencia()
        return True, "Movimento realizado.", self.estado()

    def desistir(self, jogador):
        if self.finalizado:
            return False, "A partida já terminou.", self.estado()
        self.vencedor = self.outro(jogador)
        self.finalizado = True
        return True, f"Jogador {jogador} desistiu.", self.estado()

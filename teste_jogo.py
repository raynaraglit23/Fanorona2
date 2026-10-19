from jogo import Jogo, JOGADOR_1, JOGADOR_2

j = Jogo()
assert j.contar(JOGADOR_1) == 22
assert j.contar(JOGADOR_2) == 22
assert j.turno == JOGADOR_1
print("Teste básico OK")

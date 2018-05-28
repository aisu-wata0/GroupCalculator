# -*- coding: utf-8 -*-
import socket
import os
import sys
import time
import numpy
import json
import random

shipSize = 3
mapSize = 5
enderecos = (('localhost', 4969), ('localhost', 4970), ('localhost', 4972), ('localhost', 4978))
atual = int(sys.argv[1])
destino = (atual + 1) % len(enderecos)


def initialize_mapa():
    mapa = numpy.chararray((mapSize, mapSize))
    mapa[:] = "~"
    return mapa


def initialize_navios():
    return [[0 for x in range(3)] for y in range(2)]


def imprime_mapa(mapa):
    os.system('clear')
    print('\x1b[6;97;44m' + ' Meu mapa: ' + '\x1b[0m')
    for row in mapa:
        print(
            '\x1b[6;97;44m' + ' ' + ((((' '.join(map(str, row))).replace('b', '')).replace("'", ""))) + ' ' + '\x1b[0m')


def makeShip(mapa, pos, navio):
    pos0 = int(pos[0])
    pos1 = int(pos[1])
    if pos[2].lower() == "h":
        if pos1 + shipSize < mapSize:
            for i in range(3):
                mapa[pos0, pos1 + i] = '@'
                navio[i] = str(pos0) + str(pos1 + i)
        else:
            for i in range(3):
                mapa[pos0, pos1 - i] = '@'
                navio[i] = str(pos0) + str(pos1 - i)
    else:
        if pos0 + shipSize < mapSize:
            for i in range(3):
                mapa[pos0 + i, pos1] = '@'
                navio[i] = str(pos0 + i) + str(pos1)
        else:
            for i in range(3):
                mapa[pos0 - i, pos1] = '@'
                navio[i] = str(pos0 - i) + str(pos1)
    return mapa, navio


def play_game():
    mapa = initialize_mapa()
    navios = initialize_navios()
    imprime_mapa(mapa)
    pos1 = input("Digite a posicao do 1o navio. Linha(0..4), coluna(0..4) e orientacao(h/v). Ex: 12V --> ")
    while True:
        try:
            if not int(pos1[0]) in range(0, 5) or not int(pos1[1]) in range(0, 5) or pos1[2] not in ["V", "v", "h",
                                                                                                     "H"]:
                print("Erro!")
                pos1 = input("Digite a posicao do 1o navio. Linha(0..4), coluna(0..4) e orientacao(h/v). Ex: 12V --> ")
            else:
                break
        except Exception as e:
            print("Erro!")
            pos1 = input("Digite a posicao do 1o navio. Linha(0..4), coluna(0..4) e orientacao(h/v). Ex: 12V --> ")

    mapa, navios[0] = makeShip(mapa, pos1, navios[0])

    pos2 = input("Digite a posicao do 2o navio. Linha(0..4), coluna(0..4) e orientacao(h/v). Ex: 12V --> ")
    while True:
        try:
            if not int(pos2[0]) in range(0, 5) or not int(pos2[1]) in range(0, 5) or pos2[2] not in ["V", "v", "h",
                                                                                                     "H"]:
                print("Erro!")
                pos2 = input("Digite a posicao do 2o navio. Linha(0..4), coluna(0..4) e orientacao(h/v). Ex: 12V --> ")
            else:
                break
        except Exception as e:
            print("Erro!")
            pos2 = input("Digite a posicao do 2o navio. Linha(0..4), coluna(0..4) e orientacao(h/v). Ex: 12V --> ")

    mapa, navios[1] = makeShip(mapa, pos2, navios[1])
    imprime_mapa(mapa)
    return mapa, navios


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socke = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (enderecos[atual])
server_address2 = (enderecos[destino])
sock.bind(server_address)

print('comecando em %s, porta %s' % server_address)


class Mensagem:
    def __init__(self, id, origem, destino, prioridade, acao, coord, resp, end):
        self.id = id
        self.origem = origem
        self.destino = destino
        self.prioridade = prioridade
        self.acao = acao
        self.coord = coord
        self.resp = resp
        self.end = end


def decodifica(mensagem):
    return Mensagem(**json.loads(mensagem.decode()))


def codifica(mensagem):
    return json.dumps(mensagem.__dict__).encode()


def escuta():
    while True:
        try:
            sock.settimeout(1.0)
            dat, address = sock.recvfrom(4096)
            data = (decodifica(dat).__dict__)
            if data:
                return decodifica(dat)
        except socket.timeout:
            return 0


def envia(mensagem):
    sent = socke.sendto(codifica(mensagem), server_address2)


def gera_bastao():
    return Mensagem('2', str(atual), str(destino), '2', 'bastao', "", "", "")


def gera_ataque(alvos):
    destino = str(atual)
    alvos[atual] = 0
    while destino == str(atual) and alvos[int(destino)] == 0:
        print("Voce é o jogador: " + str(atual) + ". Insira o jogador a ser atacado dentre:")
        alv = []
        for alvo in range(len(alvos)):
            if alvo != atual and alvos[alvo] != 0:
                alv.append(str(alvo))
        print(','.join(alv))
        destino = input()

        while True:
            try:
                if not int(destino) in range(len(alvos)) or int(destino) is atual:
                    print("Erro!")
                    destino = input("Insira o jogador a ser atacado: ")
                else:
                    break
            except Exception as e:
                print("Erro!")
                destino = input("Insira o jogador a ser atacado: ")

        if destino == str(atual):
            print("Esperto, você não pode atacar a si mesmo.")
        elif alvos[int(destino)] == 0:
            print("Este alvo já foi derrotado")

    alvos[atual] = 1
    coord = input("Digite a posição a ser atacada: ")
    while True:
        try:
            if not int(coord[0]) in range(0, 5) or not int(coord[1]) in range(0, 5):
                print("Erro!")
                coord = input("Digite a posição a ser atacada: ")
            else:
                break
        except Exception as e:
            print("Erro!")
            coord = input("Digite a posição a ser atacada: ")

    origem = str(atual)
    prioridade = '1'
    acao = 'ataque'
    mensagem = Mensagem('0', origem, destino, prioridade, acao, coord, "", "")
    return mensagem


def processa_ataque(atq, mapa, navios, alvos):
    x = int(atq.coord[0])
    y = int(atq.coord[1])
    caract = (str(mapa[x, y])).replace("'", "").replace("b", "")
    if (caract == "~"):
        mapa[x, y] = "%"
        atq.resp = "Você atingiu água na posição " + atq.coord + ", do jogador " + str(atual) + "."
    elif (caract == "@"):
        mapa[x, y] = "X"
        atq.resp = "Parabéns! Você atingiu um navio na posição " + atq.coord + ", do jogador " + str(atual) + "."
    elif (caract == "X"):
        atq.resp = "O navio já foi atingido nesta posição " + atq.coord + ", do jogador " + str(atual) + "."
    elif (caract == "%"):
        atq.resp = "Água já foi atingida nesta posição " + atq.coord + ", do jogador " + str(atual) + "."
    else:
        print("Erro, contate os desenvolvedores, ou reze.")
    atq.prioridade = "2"
    navios[0] = afunda(navios[0], atq.coord)
    navios[1] = afunda(navios[1], atq.coord)

    if (afundou(navios[0]) == 1):
        navios[0][:] = '1'
        atq.prioridade = "3"
        atq.resp += "\nO navio 1 do jogador " + atq.destino + " foi afundado."
    if (afundou(navios[1]) == 1):
        navios[1][:] = '1'
        atq.prioridade = "3"
        atq.resp += "\nO navio 2 do jogador " + atq.destino + " foi afundado."
    if (afundou(navios[1]) == 2 and afundou(navios[0]) == 2):
        atq.end = '1'
        alvos[atual] = 0
    return atq


def afunda(navio, pos):
    for x in range(len(navio)):
        if navio[x] == pos:
            navio[x] = '0'
    return navio


def afundou(navio):
    cont = [x for x in navio if x == '0']
    if len(cont) == 3:
        return 1
    if navio[0] == '1':
        return 2
    return 0


def naoacabou(vet):
    tot = 0
    for i in vet:
        tot += i
    return tot


def venceu(vet):
    tot = 0
    for i in vet:
        tot += i
    if (tot > 1):
        return -1
    if (tot == 1 and vet[atual] == 1):
        return 1
    return 0


alvos = [1] * len(enderecos)

mensagem = mes = bastao = 0
mapa, navios = play_game()

if (atual == 0):
    bastao = gera_bastao()
jaimprimiu = 0
while True:
    mes = 0
    if (bastao != 0):

        if (mensagem == 0):
            if (naoacabou(alvos)):
                mensagem = gera_ataque(alvos)
            else:
                exit()
        while (mes == 0):
            envia(mensagem)
            mes = escuta()
        if (mes):
            if (mes.prioridade == '2'):
                print(mes.resp)
                envia(bastao)
                bastao = 0
                mensagem = 0
                mes = escuta()
            else:
                if (mes.prioridade == '3'):
                    print(mes.resp.split('\n')[0])
                    mes.prioridade = '4'
                    mes.acao = mes.resp.split('\n', 1)[-1]
                    envia(mes)

                if (mes.prioridade == '4'):
                    print(mes.acao)
                    envia(bastao)
                    bastao = 0
                    mensagem = 0
                    if (mes.end == "1"):
                        alvos[int(mes.destino)] = 0

                    mes = escuta()
                    if (venceu(alvos) == 1):
                        print("Parabens, você venceu!")
                        exit()

            mes = 0
    else:
        mes = 0
        mes = escuta()
        if (venceu(alvos) == 1 and mes == 0):
            print("Parabens, você venceu!")
            exit()
        if (naoacabou(alvos) == 1 and mes == 0):
            if jaimprimiu == 1:
                exit()
            else:
                print("Game Over, você perdeu")
                exit()
        if (mes != 0):
            if (mes.prioridade == '4'):
                print(mes.acao)
                if (mes.end == "1"):
                    alvos[int(mes.destino)] = 0
                envia(mes)
                mes = 0
            elif (mes.destino != str(atual)):
                envia(mes)
            else:
                if (venceu(alvos) == 1):
                    exit()
                if (mes.acao == 'bastao'):
                    bastao = gera_bastao()
                    mes = 0

                    if (alvos[atual] == 0):
                        envia(bastao)
                        bastao = 0
                else:
                    mes = processa_ataque(mes, mapa, navios, alvos)
                    envia(mes)
                    imprime_mapa(mapa)
                    if (alvos[atual] == 0):
                        print("Game over. Você Perdeu")
                        jaimprimiu = 1

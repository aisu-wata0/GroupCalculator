#!python

import socket


# recebe uma porta e o nome local, verifica se
# pertence a lista do servers.txt, cria uma lista com base nela
# e verifica qual é o número do servidor (se for algum). Retorna
# o valor da remote_list e o valor do server_id, que será usado
# no servidor (mas não no cliente)
def create_remote_list(my_port=-1, my_name=""):
    # valores começam inicialmente sem valor
    remote_list = []
    index = 0
    server_id = 0

    file = open("servers.txt", "r")
    for line in file:
        # exemplo de execução: "macalan 1111" => ["macalan", 1111]
        line_split = line.split(" ")

        # separa a primeira parte da linha
        addr = line_split[0]

        # separa a segunda parte da linha
        port = int(line_split[1])

        # remote_list recebe os valores do endereço e da porta
        remote_list.append((addr, port))
        print("Registered remote %s:%d" % (addr, port))

        # caso seja o servidor, verifica qual número ele é
        if socket.gethostbyname(addr) == my_name and port == my_port:
            server_id = index
            print("I am server #%d" % server_id)
        index += 1

    # retorna a lista com endereços e portas, e o index do servidor
    return remote_list, server_id

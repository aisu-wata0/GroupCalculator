#!python
import socket
import remotes
import sys

# tamanho do buffer
BUFSIZ = 1024


# função para criar o socket. Será chamada a cada iteração do main.
def create_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    return sock


# Essa função recebe o host e a porta, cria um socket e tenta fazer uma conexão.
# Caso a conexão ocorra, a função retorna True e o socket (que será usado posteriormente).
# Caso ocorra uma exceção durante a conexão, fecha o socket
# e retorna False e o socket fechado, que não será mais usado.
def connect_server(remote):
    is_connected = False

    # Antes de cada execução, é necessário criar o socket.
    sock = create_socket()

    # Os valores do host e da porta são passados por parâmetro dentros do remote.
    host = remote[0]
    port = remote[1]

    try:
        # consegue o endereço IP do host.
        host = socket.gethostbyname(host)

        # Tenta criar a conexão. Caso seja recusada, o socket
        # irá produzir a exceção ConnectionRefusedError.
        # Caso ocorra outra exceção, o socket irá produzir uma Exception.
        sock.connect((host, port))
        print("[Client] Connected: server %s:%d" % (host, port))

        # Se não houve nenhuma exceção, a conexão foi bem sucedida.
        # A variável então is_connected recebe o valor True, que será
        # utilizado no main.
        is_connected = True
    except ConnectionRefusedError:
        # se a conexão for recusada, imprime o log mostrando isso.
        print("[Client] Refused: server %s:%d" % (host, port))
        pass
    except Exception as e:
        # se outro problema ocorrer, imprime o log mostrando isso.
        print("[Client] Exception: " + e.__str__() + " for server %s:%d" % (host, port))
    finally:
        # caso o socket não tenha conseguido realizar a conexão, será fechado.
        if not is_connected:
            print("[Client] Closing socket")
            sock.close()

        # Retorna dois atributos, o valor que indica se o socket conseguiu
        # se conectar, e o próprio socket, que será usado caso tenha ocorrido
        # a conexão.
        return is_connected, sock


def main(argv):
    # remote_list recebe a lista de endereços locais para o nosso multicast funcionar.
    remote_list, _ = remotes.create_remote_list()

    while True:
        # recebe a expressão aritmética do usuário.
        expression = input("Type an arithmetic expression. Example: 1+1, (13+1)*2, 5^3\n")

        # para cada endereço local do remote_list, iremos iterar.
        for idx, remote in enumerate(remote_list):
            print("[Client] Requesting server #%d" % idx)

            # tenta conectar no servidor. Se for um sucesso, ele envia a expressão
            # e aguarda o recebimento da resposta. Caso contrário, procede para a
            # próxima iteração.
            is_connected, sock = connect_server(remote)

            # caso não esteja conectado, não faz nada e procede para a próxima
            # iteração. Nesse caso, o socket já foi fechado pelo connect_server().
            if is_connected:

                # mensagem é codificada em ascii
                msg = expression.encode('ascii')
                print("[Client] Sending expression " + expression)

                # mensagem é enviada ao servidor de menor número
                sock.send(msg)
                print("[Client] Waiting server result")

                # outra mensagem é recebida com a resolução da primeira e decodificada
                result = sock.recv(BUFSIZ).decode('ascii')
                print("[Client] Closing socket")

                # socket é fechado
                sock.close()
                print("result = " + result)

                # não precisamos continuar iterando pelos próximos servidores, se
                # encontramos o de menor número, que é o líder, e ele já nos devolveu
                # a resposta. Logo, break irá retornar para o While que irá pedir
                # outra expressão aritmética para o usuário.
                break


if __name__ == "__main__":
    main(sys.argv[0:])

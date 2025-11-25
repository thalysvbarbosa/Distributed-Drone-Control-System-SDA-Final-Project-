import opcua
import threading
import socket
import queue
import time
import sys


def thread_opcua(stop_event: threading.Event, pos_queue: queue.Queue, tgt_queue: queue.Queue):
    # Definir o cliente OPC UA
    cliente = opcua.Client("opc.tcp://localhost:53530/OPCUA/SimulationServer")

    # Define tempo de timeout da sessão
    cliente.session_timeout = 2000

    # Tentar conectar ao servidor OPC UA
    try:
        cliente.connect()
    except Exception as e:
        print("[OPC] Erro ao conectar ao servidor OPC UA:", e)
        return
    print("[OPC] Conectado ao servidor OPC UA")

    # Tentar acessar o nó "Drone"
    try:
        root = cliente.get_objects_node()
        drone_node = root.get_child(["3:Drone"])
    except Exception as e:
        print("[OPC] Erro ao acessar o nó 'Drone':", e)
        cliente.disconnect()
        return
    print("[OPC] Nó 'Drone' acessado com sucesso")

    # Mapeamento dos nós esperados
    try:
        tX = drone_node.get_child(["3:TargetX"])
        tY = drone_node.get_child(["3:TargetY"])
        tZ = drone_node.get_child(["3:TargetZ"])
        dX = drone_node.get_child(["3:DroneX"])
        dY = drone_node.get_child(["3:DroneY"])
        dZ = drone_node.get_child(["3:DroneZ"])
    except Exception as e:
        print("[OPC] Erro ao mapear os nós esperados:", e)
        cliente.disconnect()
        return
    print("[OPC] Nós mapeados com sucesso")
    
    # Loop principal da thread
    while not stop_event.is_set():
        # Verificar se há novos comandos na fila tgt_queue
        try:
            target = tgt_queue.get(timeout=0.2)     # Obtem o próximo comando
            
            # Atualizar os valores no servidor OPC UA
            tX.set_value(target['x'])
            tY.set_value(target['y'])
            tZ.set_value(target['z'])
        
        except queue.Empty:
            pass    # Nenhum comando novo, continue

        # Ler a posição atual do drone e colocar na fila pos_queue
        try:
            position = {
                'x': dX.get_value(),
                'y': dY.get_value(),
                'z': dZ.get_value(),
                'timestamp': time.time()
            }
            pos_queue.put(position)
        except Exception as e:
            print("[OPC] Erro ao ler a posição do drone:", e)
            break

        time.sleep(0.5)  # Pequena pausa para evitar uso excessivo de CPU
    print("[OPC] Encerrando conexão com o servidor OPC UA")
    cliente.disconnect()


def thread_tcp(stop_event: threading.Event, pos_queue: queue.Queue, tgt_queue: queue.Queue):
    HOST = 'localhost'
    PORT = 65432

    # Criando o socket do servidor, que permanecerá aberto
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        
        # Adiciona um timeout ao socket do servidor para que o s.accept() não
        # bloqueie indefinidamente, permitindo que o loop verifique o stop_event.
        s.settimeout(1.0) 
        print(f"[TCP] Servidor escutando em {HOST}:{PORT}")

        # Este loop garante que o servidor continue rodando e aceitando novas
        # conexões mesmo depois que um cliente se desconectar.
        while not stop_event.is_set():
            try:
                # Espera por uma nova conexão.
                # Se nenhuma conexão chegar em 1.0s, um socket.timeout será lançado.
                conn, addr = s.accept()
            except socket.timeout:
                # Nenhuma conexão foi feita, simplesmente continue para a próxima
                # iteração do loop, onde o stop_event será verificado novamente.
                continue
            
            # Se uma conexão for bem-sucedida:
            with conn:
                print(f"[TCP] Conectado por {addr}")
                conn.settimeout(0.5)

                # Loop de comunicação com o cliente conectado
                while not stop_event.is_set():
                    # Obter novas posições e enviar via TCP
                    try:
                        position = pos_queue.get(block=False)
                        msg = f"{position['x']},{position['y']},{position['z']},{position['timestamp']}\n"
                        conn.sendall(msg.encode('utf-8'))
                    except queue.Empty:
                        pass
                    except (ConnectionResetError, BrokenPipeError) as e:
                        print(f"[TCP] Erro ao enviar dados: {e}")
                        break # Encerra o loop de comunicação

                    # Receber novos comandos via TCP
                    try:
                        data = conn.recv(1024)
                        if not data:
                            print("[TCP] Conexão encerrada pelo cliente")
                            break # Encerra o loop de comunicação
                        
                        msg = data.decode('utf-8').strip()
                        parts = msg.split(',')
                        if len(parts) == 3:
                            try:
                                target = {'x': float(parts[0]), 'y': float(parts[1]), 'z': float(parts[2])}
                                tgt_queue.put(target)
                            except ValueError:
                                print("[TCP] Dados inválidos recebidos:", msg)
                        else:
                            print("[TCP] Formato de dados inválido:", msg)
                    
                    except socket.timeout:
                        pass
                    except (ConnectionResetError, BrokenPipeError) as e:
                        print(f"[TCP] Erro ao receber dados: {e}")
                        break # Encerra o loop de comunicação
            # Esta mensagem é exibida quando o loop de comunicação com o cliente
            # termina, e o servidor volta a aguardar uma nova conexão.
            print(f"[TCP] Cliente {addr} desconectado. Aguardando nova conexão...")

    print("[TCP] Servidor TCP encerrado.")

        
def main():
    # Definir evento que encerra as threads
    encerrar = threading.Event()

    # Definir filas para comunicação entre threads
    pos_queue = queue.Queue(128)
    tgt_queue = queue.Queue(128)
    
    # Iniciar a thread OPC UA
    t_opc = threading.Thread(target=thread_opcua, args=(encerrar, pos_queue, tgt_queue))
    t_opc.start()

    # Iniciar a thread TCP
    t_tcp = threading.Thread(target=thread_tcp, args=(encerrar, pos_queue, tgt_queue))
    t_tcp.start()

    print("Pressione Ctrl+C para encerrar...\n")
    try:
        # Mantém a thread principal viva, esperando pelas outras
        while t_opc.is_alive() and t_tcp.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nEncerrando...\n")
        encerrar.set()
    
    # Aguardar as threads finalizarem
    t_opc.join()
    t_tcp.join()

    print("Programa encerrado.")
    sys.exit(0)


if __name__ == "__main__":
    main()
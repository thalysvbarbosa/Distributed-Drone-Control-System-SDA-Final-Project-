import time
from opcua import Client, Server


def main():
    # --- CONFIGURAÇÃO DO SERVIDOR LOCAL (CHAINED) ---
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4841/freeopcua/server/")

    # Configura o namespace do nosso servidor
    uri = "http://meu.gateway.com"
    idx = server.register_namespace(uri)

    # Cria a estrutura de objetos e variáveis do nosso servidor
    objects = server.get_objects_node()
    drone_obj = objects.add_object(idx, "DroneMirror")

    # Cria variáveis que serão 'espelhos' das originais
    my_drone_x = drone_obj.add_variable(idx, "DroneX", 0.0)
    my_drone_y = drone_obj.add_variable(idx, "DroneY", 0.0)
    my_drone_z = drone_obj.add_variable(idx, "DroneZ", 0.0)
    my_target_x = drone_obj.add_variable(idx, "TargetX", 0.0)
    my_target_y = drone_obj.add_variable(idx, "TargetY", 0.0)
    my_target_z = drone_obj.add_variable(idx, "TargetZ", 0.0)

    my_drone_x.set_writable()
    my_drone_y.set_writable()
    my_drone_z.set_writable()
    my_target_x.set_writable()
    my_target_y.set_writable()
    my_target_z.set_writable()

    server.start()
    print("[SERVER] Gateway MES rodando em opc.tcp//0.0.0.0:4841")

    # --- CONFIGURAÇÃO DO CLIENTE ---
    cliente = Client("opc.tcp://localhost:53530/OPCUA/SimulationServer")

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

    try:
        while True:
            # 1. Ler do Prosys (Original)
            drone_x = dX.get_value()
            drone_y = dY.get_value()
            drone_z = dZ.get_value()
            target_x = tX.get_value()
            target_y = tY.get_value()
            target_z = tZ.get_value()

            # 2. Escreve no Servidor Local (Espelho)
            my_drone_x.set_value(drone_x)
            my_drone_y.set_value(drone_y)
            my_drone_z.set_value(drone_z)
            my_target_x.set_value(target_x)
            my_target_y.set_value(target_y)
            my_target_z.set_value(target_z)

            # print(f"[GATEWAY] Replicando: {drone_x:.2f}, {drone_y:.2f}, {drone_z:.2f}")
            time.sleep(0.5)  # Atualiza a cada 500ms
    finally:
        cliente.disconnect()
        server.stop()
        print("[SISTEMA] Encerrado.")


if __name__ == "__main__":
    main()

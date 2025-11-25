import time
from datetime import datetime
from opcua import Client

# Mesma configuração do sinotico.py para identificar os locais
STATIONS = {
    "Estacao 1": {"x": 2.0, "y": 0.0, "z": 1.0},
    "Estacao 2": {"x": 0.0, "y": 2.0, "z": 1.0},
    "Estacao 3": {"x": -2.0, "y": 0.0, "z": 1.0},
    "Estacao 4": {"x": 0.0, "y": -2.0, "z": 1.0},
}


def identify_location(tx, ty, tz):
    """Tenta identificar se o drone está indo para uma estação conhecida."""
    # Pequena tolerância para comparação de float
    tol = 0.1
    for name, coords in STATIONS.items():
        if (
            abs(tx - coords["x"]) < tol
            and abs(ty - coords["y"]) < tol
            and abs(tz - coords["z"]) < tol
        ):
            return f"({name})"
    return "(Manual)"


def main():
    # Conecta no Gateway (Chained Server)
    url = "opc.tcp://localhost:4841/freeopcua/server/"
    client = Client(url)

    try:
        client.connect()
        print(f"[MES] Conectado ao Gateway em {url}")

        # Setup de namespace e nós
        uri = "http://meu.gateway.com"
        idx = client.get_namespace_index(uri)
        objects = client.get_objects_node()
        drone_mirror = objects.get_child([f"{idx}:DroneMirror"])

        # Variáveis
        var_dx = drone_mirror.get_child([f"{idx}:DroneX"])
        var_dy = drone_mirror.get_child([f"{idx}:DroneY"])
        var_dz = drone_mirror.get_child([f"{idx}:DroneZ"])
        var_tx = drone_mirror.get_child([f"{idx}:TargetX"])
        var_ty = drone_mirror.get_child([f"{idx}:TargetY"])
        var_tz = drone_mirror.get_child([f"{idx}:TargetZ"])

        print("[MES] Monitorando processo...")

        with open("mes.txt", "w", encoding="utf-8") as f:
            # Cabeçalho
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"--- Inicio do Log MES: {start_time} ---\n\n")

            last_target_sig = None  # Para detectar mudança de target

            while True:
                # Leitura dos valores
                dx = var_dx.get_value()
                dy = var_dy.get_value()
                dz = var_dz.get_value()
                tx = var_tx.get_value()
                ty = var_ty.get_value()
                tz = var_tz.get_value()

                # Timestamp legível
                ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                # Registrar Mudança de Target
                current_target_sig = (tx, ty, tz)
                if current_target_sig != last_target_sig:
                    local_name = identify_location(tx, ty, tz)
                    # Formato idêntico ao historiador
                    log_evt = f"[{ts_now}] [TARGET DETECTADO] - {local_name} X={tx}, Y={ty}, Z={tz}\n"
                    f.write(log_evt)
                    print(log_evt.strip())
                    last_target_sig = current_target_sig

                # Registrar Posição

                log_pos = f"[{ts_now}] [POSICAO LIDA] - X={dx}, Y={dy}, Z={dz}\n"

                f.write(log_pos)
                f.flush()

                # Sleep para controlar o tamanho do arquivo
                time.sleep(1.0)

    except Exception as e:
        print(f"[ERRO MES] {e}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()

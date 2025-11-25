import time
import math
from opcua import Client
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

############################
# CONFIG
############################
OPCUA_URL   = "opc.tcp://localhost:53530/OPCUA/SimulationServer"
DRONE_PATH  = "/Quadcopter/base"
TARGET_PATH = "/target"

# velocidade máx. do alvo (m/s) e passo de atualização
TARGET_SPEED = 0.35
DT           = 0.05         # 20 Hz
POS_TOL      = 1e-4         # tolerância para “parado”

############################
# OPC UA helpers
############################
def connect_opc(url=OPCUA_URL):
    client = Client(url)
    client.connect()
    print("[OPC] Connected")

    root = client.get_objects_node()

    # Tente achar a pasta "Drone" no ns=3 (padrão do SimulationServer),
    # e tenha fallback para procurar por nome entre os filhos.
    drone_folder = None
    try:
        drone_folder = root.get_child(["3:Drone"])
    except Exception:
        # fallback: varrer filhos e procurar "Drone"
        for n in root.get_children():
            try:
                name = n.get_browse_name().Name
                if name.lower() == "drone":
                    drone_folder = n
                    break
            except Exception:
                pass
    if drone_folder is None:
        raise RuntimeError("Não encontrei a pasta 'Drone' no servidor OPC UA.")

    # Mapeie variáveis por nome (case-insensitive)
    name_to_node = {}
    for v in drone_folder.get_children():
        try:
            nm = v.get_browse_name().Name
            name_to_node[nm.lower()] = v
        except Exception:
            pass

    # Esperadas (ajuste aqui se seus nomes diferirem)
    tX = name_to_node.get("targetx")
    tY = name_to_node.get("targety")
    tZ = name_to_node.get("targetz")
    dX = name_to_node.get("dronex")
    dY = name_to_node.get("droney")
    dZ = name_to_node.get("dronez")

    if not all([tX, tY, tZ, dX, dY, dZ]):
        found = ", ".join(sorted(name_to_node.keys()))
        raise RuntimeError(
            "Variáveis esperadas não encontradas. "
            "Quero TargetX, TargetY, TargetZ, DroneX, DroneY, DroneZ. "
            f"Encontradas: {found}"
        )

    print("[OPC] Vars bound:",
          "TargetX/TargetY/TargetZ & DroneX/DroneY/DroneZ")
    return client, (tX, tY, tZ, dX, dY, dZ)

############################
# Coppelia helpers
############################
def connect_coppelia():
    client = RemoteAPIClient()   # 127.0.0.1:23000
    sim = client.getObject('sim')

    # garanta sim parada e inicie
    if sim.getSimulationState() != sim.simulation_stopped:
        sim.stopSimulation()
        while sim.getSimulationState() != sim.simulation_stopped:
            time.sleep(0.1)
    sim.startSimulation()
    time.sleep(0.5)

    drone  = sim.getObject(DRONE_PATH)
    target = sim.getObject(TARGET_PATH)
    print("[SIM] Connected; handles ok")
    return sim, drone, target

def get_pos(sim, handle):
    return sim.getObjectPosition(handle, -1)  # world

def set_pos(sim, handle, p):
    sim.setObjectPosition(handle, -1, list(p))

def step_towards(p_now, p_goal, vmax, dt):
    """Dá um passo de p_now -> p_goal, respetando velocidade máxima."""
    dx = [p_goal[i] - p_now[i] for i in range(3)]
    dist = math.dist(p_now, p_goal)
    if dist <= POS_TOL:
        return p_goal
    max_step = vmax * dt
    if dist <= max_step:
        return p_goal
    s = max_step / dist
    return [p_now[i] + s * dx[i] for i in range(3)]

############################
# Main
############################
def main():
    # 1) Conectar
    opc_client, (tX, tY, tZ, dX, dY, dZ) = connect_opc()
    sim, drone, target = connect_coppelia()

    try:
        # 2) Inicial: mantenha alvo na altura mínima (decola suave)
        p_drone = get_pos(sim, drone)
        p_target = get_pos(sim, target)
        alt = max(p_drone[2], 1.2)
        p_target = [p_target[0], p_target[1], alt]
        set_pos(sim, target, p_target)

        # 3) loop
        print("[RUN] Control loop started. Press Ctrl+C to stop.")
        while True:
            # 3.1) ler comandos do Prosys
            try:
                cmd = [float(tX.get_value()), float(tY.get_value()), float(tZ.get_value())]
            except Exception as e:
                print("[OPC] read error:", e)
                time.sleep(DT)
                continue

            # 3.2) avançar o target suavemente até o comando
            p_target = get_pos(sim, target)
            p_next   = step_towards(p_target, cmd, TARGET_SPEED, DT)
            set_pos(sim, target, p_next)

            # 3.3) publicar pose do drone no Prosys
            p_drone = get_pos(sim, drone)
            try:
                dX.set_value(p_drone[0])
                dY.set_value(p_drone[1])
                dZ.set_value(p_drone[2])
            except Exception as e:
                print("[OPC] write error:", e)

            time.sleep(DT)

    except KeyboardInterrupt:
        print("\n[RUN] Stopping...")
    finally:
        try:
            sim.stopSimulation()
        except Exception:
            pass
        try:
            opc_client.disconnect()
        except Exception:
            pass
        print("[CLEAN] Done.")

if __name__ == "__main__":
    main()

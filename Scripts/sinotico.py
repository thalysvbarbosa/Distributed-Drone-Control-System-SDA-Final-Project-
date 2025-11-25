import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import threading
import queue
import time
from datetime import datetime
import unicodedata

# --- Configurações Globais ---
HOST = 'localhost'
PORT = 65432
HISTORIAN_FILE = 'historiador.txt'

STATIONS = {
    "Estação 1": {'x': 2.0, 'y': 0.0, 'z': 1.0},
    "Estação 2": {'x': 0.0, 'y': 2.0, 'z': 1.0},
    "Estação 3": {'x': -2.0, 'y': 0.0, 'z': 1.0},
    "Estação 4": {'x': 0.0, 'y': -2.0, 'z': 1.0}
}

#==============================================================================
# 1. CLASSE DE LOGGING (HISTORIADOR)
#==============================================================================
class Historian:
    """
    Gerencia o logging de eventos em um arquivo de texto (historiador).
    """
    def __init__(self, filename: str):
        """
        Inicializa o historiador.

        Args:
            filename (str): O nome do arquivo de log.
        """
        self.filename = filename
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write(f"--- Inicio do Log: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n")
        except IOError as e:
            print(f"Erro de Arquivo: Nao foi possivel iniciar o {self.filename}: {e}")

    def _remove_accents(self, text: str) -> str:
        """Remove acentos de uma string para padronização do log."""
        try:
            nfkd_form = unicodedata.normalize('NFKD', text)
            return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        except TypeError:
            return text

    def log(self, event_type: str, content: str, timestamp: str = None) -> str:
        """
        Cria uma mensagem de log formatada, a escreve no arquivo e a retorna.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        clean_event_type = self._remove_accents(event_type.upper())
        clean_content = self._remove_accents(content)
        
        log_message = f"[{timestamp}] [{clean_event_type}] - {clean_content}\n"
        
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(log_message)
        except IOError as e:
            print(f"Erro ao escrever no historiador: {e}")
            
        return log_message

#==============================================================================
# 2. CLASSE DE COMUNICAÇÃO TCP
#==============================================================================
class TCPClient:
    """
    Gerencia a comunicação TCP (conectar, enviar, receber) em threads separadas.
    """
    def __init__(self, host: str, port: int, receive_queue: queue.Queue):
        self.host = host
        self.port = port
        self.receive_queue = receive_queue
        
        self.sock = None
        self.stop_event = threading.Event()
        self.send_event = threading.Event()
        
        self.target_data_shared = None
        self.data_lock = threading.Lock()

    def connect(self) -> bool:
        """Tenta se conectar ao servidor TCP."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(1.0)
            self.receive_queue.put({'type': 'status', 'payload': 'Conectado'})
            return True
        except Exception as e:
            self.receive_queue.put({'type': 'status', 'payload': 'Erro na conexao', 'error': e})
            return False

    def start_threads(self):
        """Inicia as threads de envio e recebimento."""
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.receive_thread.start()
        self.send_thread.start()

    def _receive_loop(self):
        """Loop para receber dados do servidor e colocar na fila."""
        print("[TCP] Thread receptora iniciada.")
        while not self.stop_event.is_set():
            try:
                data = self.sock.recv(1024)
                if data:
                    decoded_data = data.decode('utf-8').strip()
                    parts = decoded_data.split(',')
                    if len(parts) == 4:
                        position = {'x': parts[0], 'y': parts[1], 'z': parts[2], 'timestamp': parts[3]}
                        self.receive_queue.put({'type': 'position_update', 'payload': position})
                else:
                    self.receive_queue.put({'type': 'status', 'payload': 'Desconectado'})
                    break
            except socket.timeout:
                continue
            except (ConnectionResetError, OSError):
                self.receive_queue.put({'type': 'status', 'payload': 'Desconectado'})
                break
        print("[TCP] Thread receptora encerrada.")

    def _send_loop(self):
        """Loop que aguarda um evento para enviar dados ao servidor."""
        print("[TCP] Thread transmissora iniciada.")
        while not self.stop_event.is_set():
            if self.send_event.wait(timeout=1.0):
                with self.data_lock:
                    target = self.target_data_shared
                
                if target:
                    message = f"{target['x']},{target['y']},{target['z']}"
                    try:
                        self.sock.sendall(message.encode('utf-8'))
                        station_name = target.get('station', 'Manual')
                        log_content = f"({station_name}) X={target['x']}, Y={target['y']}, Z={target['z']}"
                        self.receive_queue.put({'type': 'log', 'event_type': 'Target Enviado', 'content': log_content})
                    except (ConnectionResetError, BrokenPipeError):
                        self.receive_queue.put({'type': 'status', 'payload': 'Desconectado'})
                        break
                self.send_event.clear()
        print("[TCP] Thread transmissora encerrada.")
        
    def send_target(self, target_coords: dict):
        """
        Prepara os dados de target e sinaliza para a thread de envio.
        """
        with self.data_lock:
            self.target_data_shared = target_coords
        self.send_event.set()

    def stop(self):
        """Sinaliza para as threads pararem e fecha o socket."""
        print("[Rede] Encerrando comunicação...")
        self.stop_event.set()
        time.sleep(0.1)
        if self.sock:
            self.sock.close()

#==============================================================================
# 3. CLASSE DA APLICAÇÃO PRINCIPAL (GUI)
#==============================================================================
class SynopticApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Sinótico de Controle v8.1 (Arquivo Único)")
        self.master.geometry("700x550")

        # 1. Instanciar os componentes
        self.historian = Historian(HISTORIAN_FILE)
        self.receive_queue = queue.Queue()
        self.tcp_client = TCPClient(HOST, PORT, self.receive_queue)
        
        # 2. Criar a interface
        self.create_widgets()
        
        # 3. Iniciar a comunicação em uma thread separada
        threading.Thread(target=self.start_communication, daemon=True).start()

        # 4. Iniciar o processamento da fila de eventos
        self.process_receive_queue()
        
        # 5. Configurar o fechamento da janela
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def start_communication(self):
        """Tenta conectar e, se bem-sucedido, inicia as threads do cliente."""
        if self.tcp_client.connect():
            self.tcp_client.start_threads()

    def create_widgets(self):
        tab_control = ttk.Notebook(self.master)
        control_tab = ttk.Frame(tab_control, padding="10")
        history_tab = ttk.Frame(tab_control, padding="10")
        tab_control.add(control_tab, text='Controle')
        tab_control.add(history_tab, text='Histórico')
        tab_control.pack(expand=True, fill="both")

        position_frame = ttk.LabelFrame(control_tab, text="Posição Atual do Drone", padding="10")
        position_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.pos_x_var = tk.StringVar(value="X: --")
        self.pos_y_var = tk.StringVar(value="Y: --")
        self.pos_z_var = tk.StringVar(value="Z: --")
        self.pos_ts_var = tk.StringVar(value="Timestamp: --")
        self.connection_status_var = tk.StringVar(value="Status: Conectando...")

        ttk.Label(position_frame, textvariable=self.pos_x_var, font=("Helvetica", 16)).pack(pady=5)
        ttk.Label(position_frame, textvariable=self.pos_y_var, font=("Helvetica", 16)).pack(pady=5)
        ttk.Label(position_frame, textvariable=self.pos_z_var, font=("Helvetica", 16)).pack(pady=5)
        ttk.Label(position_frame, textvariable=self.pos_ts_var, font=("Helvetica", 10)).pack(pady=10)
        self.status_label = ttk.Label(position_frame, textvariable=self.connection_status_var, foreground="orange")
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        right_frame = ttk.Frame(control_tab)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        command_frame = ttk.LabelFrame(right_frame, text="Enviar Target Manual", padding="10")
        command_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(command_frame, text="Target X:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.target_x_entry = ttk.Entry(command_frame, width=15)
        self.target_x_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(command_frame, text="Target Y:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.target_y_entry = ttk.Entry(command_frame, width=15)
        self.target_y_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(command_frame, text="Target Z:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.target_z_entry = ttk.Entry(command_frame, width=15)
        self.target_z_entry.grid(row=2, column=1, padx=5, pady=5)
        self.send_button = ttk.Button(command_frame, text="Enviar Target Manual", command=self.trigger_send_target_manual, state=tk.DISABLED)
        self.send_button.grid(row=3, column=0, columnspan=2, pady=10)

        stations_frame = ttk.LabelFrame(right_frame, text="Enviar para Estação", padding="10")
        stations_frame.pack(fill="x", padx=5, pady=10)
        
        self.station_buttons = {}
        row, col = 0, 0
        for station_name in STATIONS.keys():
            button = ttk.Button(stations_frame, text=station_name, state=tk.DISABLED,
                                command=lambda name=station_name: self._send_predefined_target(name))
            button.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            self.station_buttons[station_name] = button
            col = (col + 1) % 2
            if col == 0: row += 1

        history_frame = ttk.LabelFrame(history_tab, text="Log de Eventos", padding="10")
        history_frame.pack(fill="both", expand=True)
        self.history_text = scrolledtext.ScrolledText(history_frame, wrap=tk.WORD, state=tk.DISABLED, height=15)
        self.history_text.pack(fill="both", expand=True)

    def _log_to_gui(self, message: str):
        """Escreve uma mensagem na caixa de texto de histórico da GUI."""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(tk.END, message)
        self.history_text.see(tk.END)
        self.history_text.config(state=tk.DISABLED)

    def _send_predefined_target(self, station_name: str):
        """Envia um target pré-definido usando o cliente TCP."""
        target_coords = STATIONS[station_name].copy()
        target_coords['station'] = station_name
        self.tcp_client.send_target(target_coords)

    def trigger_send_target_manual(self):
        """Valida e envia um target manual usando o cliente TCP."""
        try:
            target_coords = {
                'x': float(self.target_x_entry.get()),
                'y': float(self.target_y_entry.get()),
                'z': float(self.target_z_entry.get())
            }
            self.tcp_client.send_target(target_coords)
        except ValueError:
            messagebox.showerror("Valor Invalido", "Os valores de target devem ser numericos.")

    def process_receive_queue(self):
        """Processa mensagens da fila de comunicação para atualizar a GUI."""
        try:
            message = self.receive_queue.get_nowait()
            msg_type = message.get('type')

            if msg_type == 'status':
                payload = message.get('payload')
                self.connection_status_var.set(f"Status: {payload}")
                
                log_msg = self.historian.log('Sistema', f"Status da conexao: {payload}")
                self._log_to_gui(log_msg)
                
                if payload == 'Conectado':
                    self.status_label.config(foreground="green")
                    self.send_button.config(state=tk.NORMAL)
                    for button in self.station_buttons.values():
                        button.config(state=tk.NORMAL)
                else:
                    self.status_label.config(foreground="red")
                    self.send_button.config(state=tk.DISABLED)
                    for button in self.station_buttons.values():
                        button.config(state=tk.DISABLED)

            elif msg_type == 'position_update':
                payload = message.get('payload')
                self.pos_x_var.set(f"X: {payload['x']}")
                self.pos_y_var.set(f"Y: {payload['y']}")
                self.pos_z_var.set(f"Z: {payload['z']}")
                self.pos_ts_var.set(f"Timestamp: {payload['timestamp']}")
                
                log_content = f"X={payload['x']}, Y={payload['y']}, Z={payload['z']}"
                log_msg = self.historian.log('Posicao Recebida', log_content, timestamp=payload['timestamp'])
                self._log_to_gui(log_msg)

            elif msg_type == 'log':
                log_msg = self.historian.log(message['event_type'], message['content'])
                self._log_to_gui(log_msg)

        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_receive_queue)

    def on_closing(self):
        """Lida com o evento de fechamento da janela."""
        print("[GUI] Fechando a aplicacao...")
        self.tcp_client.stop()
        self.master.destroy()

#==============================================================================
# 4. PONTO DE ENTRADA DA APLICAÇÃO
#==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = SynopticApp(root)
    root.mainloop()
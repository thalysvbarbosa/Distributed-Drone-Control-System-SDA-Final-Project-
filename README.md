# Industrial Drone Control System via OPC UA

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![CoppeliaSim](https://img.shields.io/badge/CoppeliaSim-Edu-orange)
![OPC UA](https://img.shields.io/badge/Protocol-OPC%20UA-green)
![Status](https://img.shields.io/badge/Status-Completed-success)

## 📖 Overview

This project implements a distributed control system for an industrial inspection drone simulated in **CoppeliaSim**. It demonstrates the integration of **Industry 4.0** concepts, utilizing **OPC UA** for machine-to-machine communication, **TCP/IP** for SCADA supervision, and a Chained Server architecture for MES (Manufacturing Execution System) data logging.

This software was developed as the final assignment for the **Distributed Systems and Automation (SDA)** course at UFMG.

## 🏗 Architecture

The system consists of five distinct modules communicating over a network:

1.  **Simulation (CoppeliaSim):** Physical simulation of the Quadcopter.
2.  **Bridge (`brigde.py`):** Acts as the interface between the CoppeliaSim ZMQ API and the OPC UA Simulation Server.
3.  **Control Logic (`CLP.py`):** The main controller. It acts as an OPC UA Client to control the drone and a TCP Server to receive commands from the HMI.
4.  **HMI/SCADA (`sinotico.py`):** A Tkinter-based GUI for the operator to send commands (Station 1-4) and view telemetry. Logs to `historiador.txt`.
5.  **Gateway & MES (`gateway.py` & `mes.py`):**
    * **Gateway:** A "Chained Server" that mirrors the main OPC UA server variables to a secondary port (security/segmentation layer).
    * **MES:** Connects to the Gateway to log production events to `mes.txt`.

## ⚙️ Prerequisites

* **Python 3.8+**
* **CoppeliaSim** (Edu or Pro version)
* **Python Libraries:**
    ```bash
    pip install opcua coppeliasim-zmqremoteapi-client
    ```
    *(Note: `tkinter` and `threading` are usually included in standard Python installations).*

## 🚀 How to Run

To ensure the system works correctly, follow this specific execution order. Open separate terminals for each script.

### 1. Simulation Server
Open **CoppeliaSim**, load the scene file `drone.ttt`, and **start the simulation** (Play button).
*Ensure the internal OPC UA server of CoppeliaSim or the external simulation server is listening on port `53530`.*

### 2. Bridge
Connects the physics engine to the OPC UA namespace.
```bash
python brigde.py
```

### 3. Control Logic (PLC)
Starts the main control loop and the TCP server.
```bash
python CLP.py
```

### 4\. Gateway (Chained Server)

Creates the secondary OPC UA server (Port 4841) for the MES system.

```bash
python gateway.py
```

### 5\. MES System

Starts the logger for the execution system.

```bash
python mes.py
```

### 6\. HMI (Synoptic)

Launches the Graphical User Interface for the operator.

```bash
python sinotico.py
```

## 🎮 Usage

1.  On the **Sinotico** interface, click on the buttons ("Estação 1", "Estação 2", etc.).
2.  Observe the Drone moving in the **CoppeliaSim** window.
3.  Telemetry (X, Y, Z) will update in real-time on the GUI.
4.  Check the generated log files for data:
      * `historiador.txt`: Operator commands and telemetry history.
      * `mes.txt`: MES tracking and station arrival events.

## 📂 File Structure

  * `drone.ttt`: CoppeliaSim scene file.
  * `brigde.py`: ZMQ \<-\> OPC UA bridge.
  * `CLP.py`: Main control logic (Threaded TCP/OPC UA).
  * `sinotico.py`: Operator GUI (TCP Client).
  * `gateway.py`: Intermediate OPC UA Server.
  * `mes.py`: Manufacturing Execution System logger.
  * `historiador.txt`: Output log from HMI.
  * `mes.txt`: Output log from MES.

## 👥 Authors

  * **SDA Class 2025/02** - UFMG
  * *Arthur Pires and Thalys Barbosa*

============================================================================
PROJECT: DISTRIBUTED DRONE CONTROL SYSTEM (INDUSTRY 4.0)
VERSION: 1.0.0
DATE:    November 2025
============================================================================

[1] OVERVIEW
----------------------------------------------------------------------------
This project implements a distributed automation system simulating the control
of an inspection drone in an industrial environment. It demonstrates key 
concepts of Industry 4.0, including:
- Real-time physics simulation (CoppeliaSim).
- Industrial Interoperability (OPC UA Protocol).
- Network Segmentation (Chained Server Architecture).
- Distributed Control (TCP/IP Sockets).

The system architecture separates the Operational Level (PLC & HMI) from the
Management Level (MES) using a Gateway (Chained Server), ensuring data 
integrity and modularity.

[2] SYSTEM REQUIREMENTS
----------------------------------------------------------------------------
HARDWARE:
- PC with Windows, Linux, or macOS.
- Minimum 4GB RAM (8GB recommended for running simulators smoothly).

SOFTWARE:
- Python 3.8 or higher.
- CoppeliaSim Edu (Educational Version).
- Prosys OPC UA Simulation Server.

PYTHON LIBRARIES:
To install dependencies, run:
$ pip install opcua
$ pip install tk

[3] FILE STRUCTURE
----------------------------------------------------------------------------
1. bridge.py    : Connects CoppeliaSim (ZeroMQ) to Prosys OPC UA.
2. gateway.py   : Middleware Bridge. Reads from Prosys and republishes to 
                  a local OPC UA server (Chained Server pattern).
3. CLP.py       : Logic Controller. Acts as OPC UA Client (Control) and 
                  TCP Server (Command reception).
4. sinotico.py  : HMI/GUI. Allows operators to send commands/targets and 
                  view real-time telemetry. Logs to 'historiador.txt'.
5. mes.py       : Management Client. Connects to the Gateway to log data 
                  for analysis. Logs to 'mes.txt'.
6. drone.ttt    : CoppeliaSim 3D scene file.

[4] CONFIGURATION & INSTALLATION
----------------------------------------------------------------------------
STEP 1: PROSYS OPC UA SERVER SETUP
1. Open Prosys Simulation Server.
2. Create a new object named "Drone".
3. Inside "Drone", create the following variables (Double type):
   - DroneX, DroneY, DroneZ (Read/Write)
   - TargetX, TargetY, TargetZ (Read/Write)
4. CRITICAL: Set the 'Value' of all variables to 0.0 manually in the 
   Address Space. If left as 'Null', the scripts will fail.
5. Ensure the server is listening on port 53530 (opc.tcp).

STEP 2: COPPELIASIM SETUP
1. Open CoppeliaSim.
2. Load the 'drone.ttt' scene file.

[5] EXECUTION GUIDE (STARTUP ORDER)
----------------------------------------------------------------------------
For the system to work correctly, execute the scripts in the exact order 
below, using separate terminal windows for each:

1. INFRASTRUCTURE LAYER:
   $ python bridge.py
   (Wait for connection confirmation)

   $ python gateway.py
   (Wait for "Server started" message)

2. CONTROL LAYER:
   $ python CLP.py
   (Starts the PLC logic and TCP server)

3. MANAGEMENT & OPERATION LAYER:
   $ python mes.py
   (Starts logging to mes.txt)

   $ python sinotico.py
   (Opens the GUI window)

[6] USAGE INSTRUCTIONS
----------------------------------------------------------------------------
MANUAL CONTROL:
1. In the Synoptic window (GUI), verify status is "Connected" (Green).
2. Enter X, Y, Z coordinates in the "Manual Target" frame.
3. Click "Send".

AUTOMATIC CONTROL:
1. Click on the station buttons (e.g., "Station 1", "Station 2").
2. The drone will autonomously navigate to the preset coordinates.

LOGS:
- Check 'historiador.txt' for operational events (User commands).
- Check 'mes.txt' for process data (Telemetry & Targets).

[7] TROUBLESHOOTING
----------------------------------------------------------------------------
ERROR: "float() argument must be a string or a real number, not 'NoneType'"
SOLUTION: You forgot to set the initial values in Prosys. Go to the Address
Space and set all variables to 0.0.

ERROR: Connection Refused (TCP)
SOLUTION: Ensure CLP.py is running before starting sinotico.py.

ERROR: Connection Refused (OPC UA)
SOLUTION: Ensure Prosys Server is running (Port 53530) and Gateway is 
running (Port 4841) before starting clients.

============================================================================

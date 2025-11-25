============================================================================
PROJETO: SISTEMA DISTRIBUÍDO DE CONTROLE DE DRONE (INDÚSTRIA 4.0)
VERSÃO:  1.0.0
DATA:    Novembro 2025
============================================================================

[1] VISÃO GERAL
----------------------------------------------------------------------------
Este projeto implementa um sistema de automação distribuído simulando o 
controle de um drone de inspeção em ambiente industrial. O sistema demonstra
conceitos chave da Indústria 4.0, incluindo:
- Simulação física em tempo real (CoppeliaSim).
- Interoperabilidade Industrial (Protocolo OPC UA).
- Segmentação de Rede (Arquitetura Chained Server / Servidor Encadeado).
- Controle Distribuído (Sockets TCP/IP).

A arquitetura separa o Nível Operacional (CLP e IHM) do Nível de Gestão (MES)
utilizando um Gateway, garantindo a integridade dos dados e modularidade.

[2] REQUISITOS DO SISTEMA
----------------------------------------------------------------------------
HARDWARE:
- PC com Windows, Linux ou macOS.
- Mínimo 4GB RAM (8GB recomendado para execução fluida dos simuladores).

SOFTWARE:
- Python 3.8 ou superior.
- CoppeliaSim Edu (Versão Educacional).
- Prosys OPC UA Simulation Server.

BIBLIOTECAS PYTHON:
Para instalar as dependências, execute:
$ pip install opcua
$ pip install tk

[3] ESTRUTURA DE ARQUIVOS
----------------------------------------------------------------------------
1. bridge.py    : Conecta o CoppeliaSim (ZeroMQ) ao Prosys OPC UA.
2. gateway.py   : Middleware/Ponte. Lê do Prosys e republica os dados em um
                  servidor OPC UA local (Padrão Chained Server).
3. CLP.py       : Controlador Lógico. Atua como Cliente OPC UA (Controle) e
                  Servidor TCP (Recepção de comandos).
4. sinotico.py  : IHM/GUI. Permite ao operador enviar comandos/targets e
                  visualizar telemetria. Gera log em 'historiador.txt'.
5. mes.py       : Cliente de Gestão. Conecta ao Gateway para registrar dados
                  de processo. Gera log em 'mes.txt'.
6. drone.ttt    : Arquivo de cena 3D do CoppeliaSim.

[4] CONFIGURAÇÃO E INSTALAÇÃO
----------------------------------------------------------------------------
PASSO 1: CONFIGURAÇÃO DO PROSYS OPC UA SERVER
1. Abra o Prosys Simulation Server.
2. Crie um novo objeto chamado "Drone".
3. Dentro de "Drone", crie as seguintes variáveis (tipo Double):
   - DroneX, DroneY, DroneZ (Leitura/Escrita)
   - TargetX, TargetY, TargetZ (Leitura/Escrita)
4. CRÍTICO: Defina o valor ('Value') de todas as variáveis como 0.0 
   manualmente na aba Address Space. Se deixar como 'Null', ocorrerá erro.
5. Garanta que o servidor está rodando na porta 53530 (opc.tcp).

PASSO 2: CONFIGURAÇÃO DO COPPELIASIM
1. Abra o CoppeliaSim.
2. Carregue o arquivo de cena 'drone.ttt'.

[5] GUIA DE EXECUÇÃO (ORDEM DE INICIALIZAÇÃO)
----------------------------------------------------------------------------
Para o funcionamento correto, execute os scripts na ordem exata abaixo,
utilizando terminais separados para cada um:

1. CAMADA DE INFRAESTRUTURA:
   $ python bridge.py
   (Aguarde a confirmação de conexão)

   $ python gateway.py
   (Aguarde a mensagem de servidor iniciado)

2. CAMADA DE CONTROLE:
   $ python CLP.py
   (Inicia a lógica do CLP e o servidor TCP)

3. CAMADA DE GESTÃO E OPERAÇÃO:
   $ python mes.py
   (Inicia o registro de dados no mes.txt)

   $ python sinotico.py
   (Abre a janela da interface gráfica)

[6] INSTRUÇÕES DE USO
----------------------------------------------------------------------------
CONTROLE MANUAL:
1. Na janela do Sinótico (GUI), verifique se o status é "Conectado" (Verde).
2. Digite as coordenadas X, Y, Z no quadro "Enviar Target Manual".
3. Clique em "Enviar".

CONTROLE AUTOMÁTICO:
1. Clique nos botões das estações (ex: "Estação 1", "Estação 2").
2. O drone navegará autonomamente para as coordenadas pré-definidas.

LOGS E REGISTROS:
- Verifique 'historiador.txt' para eventos operacionais (Comandos de usuário).
- Verifique 'mes.txt' para dados de processo (Telemetria e Targets).

[7] RESOLUÇÃO DE PROBLEMAS (TROUBLESHOOTING)
----------------------------------------------------------------------------
ERRO: "float() argument must be a string or a real number, not 'NoneType'"
SOLUÇÃO: Você esqueceu de definir valores iniciais no Prosys. Vá ao Address
Space e defina todas as variáveis criadas como 0.0.

ERRO: Connection Refused (TCP)
SOLUÇÃO: Certifique-se de que o CLP.py está rodando antes do sinotico.py.

ERRO: Connection Refused (OPC UA)
SOLUÇÃO: Certifique-se de que o Prosys (Porta 53530) e o Gateway (Porta 4841)
estão rodando antes de iniciar os clientes.

============================================================================

# Dependencies
import time
import serial
import serial.tools.list_ports
import threading
import os
from datetime import datetime

# Globals
on_Deck = []
com_ports = serial.tools.list_ports.comports()
s_connections = []
logs = ["##########logs for runtime at: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + "############\n"]
time_identifier = []
CLI_closed = []
execution_closed = []

# main function
def main():
    lst = []
    # Detect active ports and determine which query user to determine which COM ports are being used for switches
    print("Yo... \nlooks like you need to wipe some commodity switches.\nThese are the active communications port(s) we've detected for your device:")
    for port in com_ports:
        print(port.device)
    val = input("Will any of these port(s) be used for communication with the commodity switches? (yes/no): ")
    if val != "yes" and val != "no":
        while val != "yes" and val != "no":
            val = input("invalid response, please enter yes/no: ")
    if val == "yes":
        for port in com_ports:
            temp = input("Will you be using " + port.device + "?(yes/no): ")
            if temp != "yes" and temp != "no":
                while temp != "yes" and temp != "no":
                    temp = input("invalid response, please enter yes/no: ")
            elif temp == "no":
                lst.append(port.device)

    # Remove unused com ports
    remove_unused_ports(lst)

    # Open serial connections with com port configurations
    initiate_serial_connections()

    # Begin CLI reading threads
    start_read_threads()

    # Begin command executing threads
    start_command_threads()

    # Write logs to logs.txt file following script completion
    write_logs()
    input()

# Function to remove COM ports not being used by the program
def remove_unused_ports(lst):
    # Remove unused ports from list of ports
    num = 0
    temp = 0
    if len(lst) > 0:
        while num < len(com_ports):
            if lst[temp] == com_ports[num].device:
                com_ports.pop(num)
                num = 0
                temp += 1
                if temp >= len(lst):
                    break
            num += 1


# Function for opening serial connections with each available port
def initiate_serial_connections():
    for port in com_ports:
        s = serial.serial_for_url(port.device, 9600, timeout=1)
        on_Deck.append("")
        s_connections.append(s)
        time_identifier.append(False)
        CLI_closed.append(False)
        execution_closed.append(False)


# Function for threads to run all necessary commands to complete device wipe.
def run_commands(val):
    batch_commands = [
        (b'2', 5),
        (b'12\r', 5),
        (b'11\r', 20),
        (b'\nadmin\r', 1),
        (b'\n\r', 1),
        (b'\nen\r', 1),
        (b'\nterminal length 0\r', 1),
        (b'\ndir\r', 5),
        (b'\ncopy system:running-config nvram:startup-config\r', 1),
        (b'\ny\r', 3),
        (b'\ncopy nvram:startup-config nvram:backup-config\r', 1),
        (b'\nshow startup-config\r', 1),
        (b'\nshow backup-config\r', 1),
    ]
    # Iterate through each command and run it
    for u, cmd in enumerate(batch_commands):
        if u == 0:
            while(not "Select (1, 2):" in on_Deck[val]):
                zz = 0
            time_identifier[val] = True
            print("#######[" + str(com_ports[val].device) + "] running step 1: " + str(cmd[0])[2:3] + " #######")
            s_connections[val].write(cmd[0])
            time.sleep(cmd[1])

        elif u == 1 or u == 2:
            while(not "(options or Q):" in on_Deck[val]):
                zz = 0
            print("#######[" + str(com_ports[val].device) + "] running step " + str(u + 1) + ": " + str(cmd[0])[2:4] + " #######")
            s_connections[val].write(cmd[0])
            time.sleep(cmd[1])

        elif u == 3:
            while(not "User:" in on_Deck[val]):
                s_connections[val].write(b'\n\r')
                time.sleep(1)
            print("#######[" + str(com_ports[val].device) + "] running step 4: " + str(cmd[0]) + " #######")
            s_connections[val].write(cmd[0])
            time.sleep(cmd[1])

        elif u == 5:
            while(not "(Routing) >" in on_Deck[val]):
                s_connections[val].write(b'\n\r')
                time.sleep(1)
            print("#######[" + str(com_ports[val].device) + "] running step 6: " + str(cmd[0]) + " #######")
            s_connections[val].write(cmd[0])
            time.sleep(cmd[1])

        else:
            print("#######[" + str(com_ports[val].device) + "] running step " + str(u + 1) + ": " + str(cmd[0]) + " #######")
            s_connections[val].write(cmd[0])
            time.sleep(cmd[1])
    print("[" + str(com_ports[val].device) + "] has completed all commands, closing execution thread...")
    #s_connections[val].close()
    execution_closed[val] = True

def read_output(val):
    temp = ""
    while True:
            if time_identifier[val]:
                try:
                    line = s_connections[val].readline().decode().strip()
                except:
                    continue
                finally:
                    if line:
                        if on_Deck[val] != line:
                            on_Deck[val] = line
                            logs.append(" [" + com_ports[val].device + "] " + on_Deck[val])
            else:
                try:
                    line = s_connections[val].read(40).decode().strip()
                except:
                    continue
                finally:
                    if line:
                        if on_Deck[val] != line:
                            temp = line
                            on_Deck[val] = line + temp
                            logs.append(" [" + com_ports[val].device + "] " + line)
                            #print("[" + str(com_ports[val].device) + "]" + on_Deck[val])

            if execution_closed[val]:
                while "ipv6 router ospf" not in on_Deck[val]:
                    line = s_connections[val].readline().decode().strip()
                    s_connections[val].write(b'\n\r')
                    if line != on_Deck[val]:
                        on_Deck[val] = line
                        logs.append(" [" + com_ports[val].device + "] " + on_Deck[val])
                        #print(" [" + com_ports[val].device + "] " + "Waiting for CLI to catch up...")
                        print(" [" + com_ports[val].device + "] " + on_Deck[val])
                while "ipv6 router ospf" not in on_Deck[val]:
                    line = s_connections[val].readline().decode().strip()
                    s_connections[val].write(b'\n\r')
                    if line != on_Deck[val]:
                        on_Deck[val] = line
                        logs.append(" [" + com_ports[val].device + "] " + on_Deck[val])
                        #print(" [" + com_ports[val].device + "] " + "Waiting for CLI to catch up...")
                        print(" [" + com_ports[val].device + "] " + on_Deck[val])
                CLI_closed[val] = True
                s_connections[val].close()
                break
    print("[" + str(com_ports[val].device) + "] CLI output thread closing...")


# Function for starting concurrent CLI output reading threads
def start_read_threads():
    for x, com in enumerate(com_ports):
        thread = threading.Thread(target=read_output, args=(x,))
        thread.start()


# Function for stating concurrent batch command threads
def start_command_threads():
    for x, com in enumerate(com_ports):
        thread = threading.Thread(target=run_commands, args=(x,))
        thread.start()


# Function for writing data to logs.txt file
def write_logs():
    # Add logs to log.txt file
    CLI_c = False
    while not CLI_c:
        CLI_c = True
        for cli in CLI_closed:
            if not cli:
                CLI_c = False
    file = open("logs.txt", "w")
    tempstr = logs[0]
    for com in com_ports:
        for log in logs:
            if str(com.device) in log:
                tempstr += (log + "\n")
    file.writelines(tempstr)
    file.close()
    print("log file has been created and filled with CLI output information @logs.txt\nPlease refer"
          " to this document if any issues occurred during script runtime.")
    os.startfile("logs.txt")


# Ensure "main()" is run at runtime
if __name__ == "__main__":
    main()

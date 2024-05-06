import asyncio
import random
from env import load_env, get_env
from machine import Pin, UART, reset
from network import STA_IF, WLAN
from time import sleep

load_env()
ssid = get_env("ssid")
password = get_env("password")
debug = get_env("debug")

# Print variables w/standard length + position for the colon
def print_variable(variable_name, colon_position=0):
    key = variable_name
    val = globals()[variable_name]
    print("{}".format(key) + (" " * max(0, colon_position - len(key))), ":", val)

# Print debug info.
if debug == 1: 
    print("Configuration")
    colon_position = 11
    print_variable("debug", colon_position)
    print_variable("ssid", colon_position)
    print_variable("password", colon_position)

# LED
led = Pin("LED", Pin.OUT)
led.off()

# UART for RS232 
uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
uart.init(bits=8, parity=None, stop=1)

# Connect to WLAN
network = WLAN(STA_IF)
network.active(True)
network.connect(ssid, password)
network.config(pm=0xa11140) # power-saving is default, this sets 'no sleep' mode
max_wait = 10
while max_wait > 0:
    if network.status() < 0 or network.status() >= 3:
        break
    max_wait -= 1
    if debug == 1: print("Connecting to " + str(ssid) + " ...")
    sleep(3)

if network.status() != 3: 
    if debug == 1: print("Unable to connect to " + str(ssid) + "!")    
    sleep(10)
    reset()

def webpage(random_value, state):
    html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pico Web Server</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <h1>Raspberry Pi Pico Web Server</h1>
            <h2>Led Control</h2>
            <form action="./lighton">
                <input type="submit" value="Light on" />
            </form>
            <br>
            <form action="./lightoff">
                <input type="submit" value="Light off" />
            </form>
            <p>LED state: {state}</p>
            <h2>Fetch New Value</h2>
            <form action="./value">
                <input type="submit" value="Fetch value" />
            </form>
            <p>Fetched value: {random_value}</p>
        </body>
        </html>
        """
    return str(html)

async def handle_client(reader, writer):
    global state
    
    print("Client connected")
    request_line = await reader.readline()
    print('Request:', request_line)
    
    # Skip HTTP request headers
    while await reader.readline() != b"\r\n":
        pass
    
    request = str(request_line, 'utf-8').split()[1]
    print('Request:', request)
    
    # Process the request and update variables
    if request == '/lighton?':
        print('LED on')
        state = 'ON'
    elif request == '/lightoff?':
        print('LED off')
        state = 'OFF'
    elif request == '/value?':
        global random_value
        random_value = random.randint(0, 20)

    # Generate HTML response
    response = webpage(random_value, state)  

    # Send the HTTP response and close the connection
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)
    await writer.drain()
    await writer.wait_closed()
    print('Client Disconnected')

async def server():    
    # Start the server and run the event loop
    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)

    while True:
        # Add other tasks that you might need to do in the loop
        await asyncio.sleep(5)
        if debug == 1: print(".")

# Program 

# Create an Event Loop
loop = asyncio.get_event_loop()
loop.create_task(server())

try:
    loop.run_forever()
except Exception as e:
    print('Error occured: ', e)
except KeyboardInterrupt:
    print('Program Interrupted by the user')


# Functions
def projector(command):
    #if debug == 1: print("Command:  " + command)
    if debug == 1: print_variable("command", colon_position)
    if command == "on":
        command = "\x7E\x30\x30\x30\x30\x20\x31\x0D" # on
    elif command == "off":
        command = "\x7E\x30\x30\x30\x30\x20\x32\x0D" # off
    else:
        command = ""

    if command == "":
        if debug == 1: print("Invalid Command!")
    else:
        projector_send(command)

def projector_send(command):
    uart.write(command)
    sleep(1)
    if(debug == 1 and uart.any()): 
        print("Response: " + str(uart.read()))

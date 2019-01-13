import socket

from pythonosc import osc_server, udp_client, dispatcher
from subprocess import call

PORT = 12000
MOVEMENT = ["left", "right", "up", "down"]
FILENAME = "sample Gestures.txt"
fromCentre = True
movementCombi = []
prevArg = 0
count = 0
actualMovement = 0
gestures = [[0]*4 for i in range(4)]
connSocket = socket.socket()
connSocket.connect(("localhost", 8080))

def read_file():
    global gestures
    f = open(FILENAME, 'r')
    for line in f:
        indexStr, text = line.split(' ', 1)
        indexList = [int(s) for s in list(filter(str.isdigit, indexStr))]
        gestures[indexList[0]][indexList[1]] = text.replace('"', "").replace("\n", "")

def input_handler(unused_addr, args):
    global movementCombi, fromCentre, prevArg, count, actualMovement
    if isinstance(args, float):
        args = int(args)
        if args == prevArg:
            count = count + 1
            if count == 4:
                actualMovement = args
        else:
            count = 1
            prevArg = args
        if actualMovement != 1:
            actualMovement = 0
            print(MOVEMENT[args - 2])
            if fromCentre:
                movementCombi += [args - 2]
                movementCombi = handleCommand(movementCombi)
            fromCentre = False
        elif actualMovement == 1:
            fromCentre = True
            actualMovement = 0
            
def handleCommand(movementList):
    global connSocket
    if len(movementList) == 1:
        return movementList
    else:
        print(gestures[movementList[0]][movementList[1]])
        call(["espeak " + "\"HH" + gestures[movementList[0]][movementList[1]] + "\"" + " 2>/dev/null"], shell=True)
        connSocket.send(gestures[movementList[0]][movementList[1]].encode('utf-8'))
        return []   

print("Output File Running")
read_file()
dispatcher = dispatcher.Dispatcher()
dispatcher.map("/wek/outputs", input_handler)

server = osc_server.ThreadingOSCUDPServer(("localhost", PORT), dispatcher)
server.serve_forever()

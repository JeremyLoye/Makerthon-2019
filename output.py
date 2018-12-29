from pythonosc import dispatcher
from pythonosc import osc_server

PORT = 12000
MOVEMENT = ["left", "right", "up", "down"]
FILENAME = "sample Gestures.txt"
fromCentre = True
movementCombi = []
gestures = [[0]*4 for i in range(4)]

def read_file():
    global gestures
    f = open(FILENAME, 'r')
    for line in f:
        indexStr, text = line.split(' ', 1)
        indexList = [int(s) for s in list(filter(str.isdigit, indexStr))]
        gestures[indexList[0]][indexList[1]] = text.replace('"', "").replace("\n", "")

def input_handler(unused_addr, args):
    global movementCombi, fromCentre
    if isinstance(args, float):
        args = int(args)
        if args != 1:
            print(MOVEMENT[args - 2])
            if fromCentre:
                movementCombi += [args - 2]
                movementCombi = handleCommand(movementCombi)
            fromCentre = False
        else:
            fromCentre = True
            
def handleCommand(movementList):
    if len(movementList) == 1:
        return movementList
    else:
        print(gestures[movementList[0]][movementList[1]])
        return []   

read_file()

dispatcher = dispatcher.Dispatcher()
dispatcher.map("/wek/outputs", input_handler)

server = osc_server.ThreadingOSCUDPServer(("localhost", PORT), dispatcher)
server.serve_forever()

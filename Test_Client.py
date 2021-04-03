import socket
from time import sleep
import python_config
import GlobalConstants

    

serverParams = python_config.read_server_config()
host = serverParams.get('host')
port = int(serverParams.get('port'))

HOST = host #'127.0.0.1'  # The server's hostname or IP address
PORT = port #65432        # The port used by the server


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #testJson = '{"sequenceNumber":"2", "timeStamp": "2020-09-21T23:04:59", "messageName": "KEEP_ALIVE", "correlationId": "d9abc8ec-1253-4a1b-9230-6a085babd3bb", "status": "ACK" }'
    #testJson = getSortMessageJson()

    #testMessage = ""

    concatMessage = GlobalConstants.StartTransmissionCharacter + 'testJson' + GlobalConstants.EndTransmissionCharacter
    encodedMessage = concatMessage.encode('ascii')

    s.connect((HOST, PORT))

    while True:
        #data = s.recv(1024)
        #print(data)
        #sleep(5)
        s.sendall(encodedMessage)
        sleep(10)
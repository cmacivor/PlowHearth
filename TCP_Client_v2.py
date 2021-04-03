import socket
import time
import sys
import traceback
import python_config
import GlobalConstants
import datetime
import logging
from logging.handlers import RotatingFileHandler
import Mysql_Connection
import CartonMessageBuilder
import HostLog
import fileinput
import EmailAlert

loggingConfig = python_config.read_logging_config()
logFileLocation = loggingConfig.get('sortclientfilelocation')

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
logFile = logFileLocation 

my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024, 
                                 backupCount=2, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(my_handler)


def multi_split(s, sep):
    stack = [s]
    for char in sep:
        pieces = []
        for substr in stack:
            pieces.extend(substr.split(char))
        stack = pieces
    return stack


def sendMessages(clientSocket):
    response = b''
    while True:
        time.sleep(6)
        messagesToSend = CartonMessageBuilder.getMostRecentMessage()

        sequenceCounter = 0
        originalSequenceCounter = ""
        #get the last sequence number
        with open('SequenceNumber.txt', 'r') as f:
            firstLine = f.readline().strip()
            sequenceCounter = int(firstLine)
            originalSequenceCounter = firstLine


        handshakeCharacer = "H".encode('ascii')
        clientSocket.sendall(handshakeCharacer)
        print('handshake sent.')

        if messagesToSend and len(messagesToSend) > 0:
            
            for message in messagesToSend:
                sequenceCounter = sequenceCounter + 1
                try:

                    constructedMessage = CartonMessageBuilder.constructCartonMessage(sequenceCounter, message)

                    clientSocket.sendall(constructedMessage)

                    response += clientSocket.recv(bufferSize)

                    print(response.decode('ascii'))
                    decodedMessage = response.decode('ascii')

                    #save to the audit table
                    CartonMessageBuilder.saveMessageToAuditTable(decodedMessage)

                    separatedMessages = multi_split(decodedMessage, [GlobalConstants.StartTransmissionCharacter, GlobalConstants.EndTransmissionCharacter])
                    for message in separatedMessages:
                        cartonNumber = CartonMessageBuilder.getCartonNumberFromParsedEchoResponse(message)
                        if cartonNumber != None and cartonNumber != "H" and ".txt" not in cartonNumber:   
                            CartonMessageBuilder.updateCartonAsAcknowledged(cartonNumber)
                    
                    response = b''

                except Exception as e:
                    print(e)
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                    exceptionDetails = ''.join('!! ' + line for line in lines)
                    print(''.join('!! ' + line for line in lines))
                    #app_log.error("error occurred for carton_Id of " + message[1])
                    app_log.error(response.decode('ascii'))
                    app_log.error(exceptionDetails)
                    HostLog.dbLog("TCP_Client", "Error", "carton_id: " +  response.decode('ascii'))
                    EmailAlert.sendErrorMessage(response.decode('ascii') + exceptionDetails)
            
            

            #reset the counter if it's 10000
            if sequenceCounter > 9999:
                sequenceCounter = 1

            #save the number to the file
            fileData = ""
            with open('SequenceNumber.txt') as fUpdate:
                fileData = fUpdate.readline()
                fileData = fileData.replace(originalSequenceCounter, str(sequenceCounter))
            
            with open('SequenceNumber.txt', 'w') as fWrite:
                fWrite.write(fileData)


serverParams = python_config.read_server_config()
host = serverParams.get('remotehost')
port = serverParams.get('port')
bufferSize = int(serverParams.get('buffersize'))

HOST = host  # The server's hostname or IP address
PORT = int(port)  # The port used by the server
connected = True
print("connecting to server..")
counter = 0
reconnectionAttempts = 0
try:

    clientSocket = socket.socket()
    clientSocket.connect((HOST, PORT))
    sendMessages(clientSocket)

except socket.error:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    exceptionDetails = ''.join('!! ' + line for line in lines)
    print(''.join('!! ' + line for line in lines))
    app_log.error(exceptionDetails)

    #set connection status and recreate socket
    connected = False
    clientSocket = socket.socket()
    print("connection lost...reconnecting")
    while not connected:
        reconnectionAttempts = reconnectionAttempts + 1
        print('reconnection attempt number: ' + str(reconnectionAttempts))
        # attempt to reconnect, otherwise sleep for 2 seconds
        try:
            clientSocket.connect((HOST, PORT))
            connected = True
            print("re-connection successful")
        except socket.error:
            time.sleep(2) # this is the pause between reconnection attempt




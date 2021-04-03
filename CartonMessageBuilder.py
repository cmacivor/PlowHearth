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


def getMostRecentMessage():
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        sql = "select * from cartons where divert_flag = 1 and divertACK = 0 order by created_at desc"

        cursor.execute(sql)

        result = cursor.fetchall()

        cursor.close()
        conn.close()

        return result

    except Exception as e:
        print(e)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))
        #app_log.error(exceptionDetails)
        #Logger.log("TCP_SortMessage_Server", "Error", exceptionDetails)

def saveMessageToAuditTable(message):
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        sql = "INSERT INTO audit_log (echo_response, created_at, updated_at) VALUES (%s, %s, %s)"

        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        val = (message, currentTimeStamp, currentTimeStamp)

        cursor.execute(sql, val)

        conn.commit()

        conn.close()

        cursor.close()

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))

def updateCartonAsAcknowledged(cartonId):
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        sql = ""
        #if ".txt" not in cartonId:
        sql = "UPDATE cartons SET divertACK = 1, updated_at = %s where carton_id = %s"
        updateValues = (currentTimeStamp, cartonId)
        #else:
            #sql = "UPDATE cartons SET divertACK = 1, updated_at = %s where file_name = %s and carton_id = %s"
            #updateValues = (currentTimeStamp, cartonId)

        cursor.execute(sql, updateValues)

        conn.commit()

        rowcount = cursor.rowcount

        cursor.close()
        conn.close()

        if rowcount > 0:
            return True
        else:
            return False

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))

def getCartonNumberFromParsedEchoResponse(message):
    #ignore anything doesn't contain a pipe character- could be blank spaces, could be 'HHH" or something
    if "|" in message:
        fields = message.replace("x02", "").replace("x03", "").split("|")

        if (len(fields) != 9 and len(fields) != 6) and (len(fields) == 1 and fields[0] != "H"):
            raise Exception("The field length or format of the message echoed from the server is incorrect.")

        #filter out the 'H'
        if len(fields) > 1: 
            return fields[2] # this is where either the carton ID or file name should be

    
    
def fillInZeros(valueToFill):
    if len(valueToFill) < 2:
        valueToFill = valueToFill.zfill(2)
        return valueToFill
    
    return valueToFill



def constructCartonMessage(counter, message):

    cartonNumberToSend = ""
    actualWeightToSend = ""
    laneAssignToSend = ""
    divertActionToSend = ""

    #carton number
    if message[3]: #the first [] is because it's a tuple
        cartonNumberToSend = message[3]
    else:
        cartonNumberToSend = "00000000000000000000"
    
    #actual weight
    if message[5]:
        actualWeightToSend = message[5]
    else:
        actualWeightToSend = "000000000"
    
    #lane number
    if message[8]:
        laneAssignToSend = str(message[8]).zfill(4)
    else:
        laneAssignToSend = "0000"
    
    #divert action
    if message[7]:
        divertActionToSend = message[7]
    else:
        divertActionToSend = "00"
    
    updatedDate = message[16]
    completeMonthValue = str(updatedDate.month)
    completeDayValue = str(updatedDate.day)
    completeHourValue = str(updatedDate.hour)
    completeMinuteValue =str(updatedDate.minute)
    completeSecondValue = str(updatedDate.second)
    
    completeMonthValue = fillInZeros(completeMonthValue)
    completeDayValue = fillInZeros(completeDayValue)
    completeHourValue = fillInZeros(completeHourValue)
    completeMinuteValue = fillInZeros(completeMinuteValue)
    completeSecondValue = fillInZeros(completeSecondValue)

    dateProcessedToSend = str(updatedDate.year) + completeMonthValue + completeDayValue
    timeProcessedToSend = completeHourValue + completeMinuteValue + completeSecondValue
    
    sequenceNumber = str(counter)
    #the sequence number is always five digits
    if len(sequenceNumber) < 5:
        sequenceNumber = sequenceNumber.zfill(5)


    messageType = ""
    if message[10] and message[14]:  #if the reason_code and file_process_message_type fields have values 
        if message[10] == "01" and message[14] == "01": #if they are both marked as successful, set the message type to 02
            messageType = "01"
    else:
        messageType = "02"


    cartonNumber = cartonNumberToSend #carton_id
    actualWeight = actualWeightToSend 
    laneNumber = laneAssignToSend 
    divertAction = divertActionToSend 
    fileName = message[1] 
    dateProcessed = dateProcessedToSend 
    timeProcessed = timeProcessedToSend 

    messageWithPipes = ""
    if messageType == "01":
        messageWithPipes = GlobalConstants.StartTransmissionCharacter + sequenceNumber + "|" + messageType + "|" + cartonNumber + "|" + actualWeight + "|" + laneNumber + "|" + divertAction + "|" + dateProcessed + "|" + timeProcessed + "|" + GlobalConstants.EndTransmissionCharacter
    else:
        messageWithPipes = GlobalConstants.StartTransmissionCharacter + sequenceNumber + "|" + messageType + "|" + fileName + "|" + dateProcessed + "|" + timeProcessed + "|" +  GlobalConstants.EndTransmissionCharacter

    return messageWithPipes.encode('ascii')




import python_config
import time
import os
import mysql.connector
import requests
import datetime
import sys
import atexit
import Mysql_Connection
import traceback
import HostLog


def addPLCLog(source, logType, message):
    
    conn = Mysql_Connection.get("wphapp")

    cursor = conn.cursor()

    sql = "INSERT INTO wph_app.plc_logs (source, type, message, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)"

    currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    val = (source, logType, message, currentTimeStamp, currentTimeStamp)

    cursor.execute(sql, val)

    conn.commit()

    conn.close()

    cursor.close()



def getWeightToleranceValues():

    conn = Mysql_Connection.get("wphdeploydb")

    cursor = conn.cursor()

    sql = "select * from weight_tolerance"

    cursor.execute(sql)

    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return result


#function to get a carton record by carton_id
def getCartonByCartonId(cartonId):
    
    conn = Mysql_Connection.get("assignmentdb")

    cursor = conn.cursor()

    sql = "select * from cartons where carton_id = %s"

    params = (cartonId,)

    cursor.execute(sql, params)

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result



def getScanLogByBarCode(barcode):
    try:
        conn = Mysql_Connection.get("wphplc")

        cursor = conn.cursor()

        sql = "select * from scanlog where barCode = %s"

        params = (barcode,)

        cursor.execute(sql, params)

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result

    except Exception as e:
        print(e)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))
        HostLog.dbLog("PLC_Helpers", "db error", exceptionDetails)


def addScanLog(triggerId, barcode, laneAssigned):
    try:
        conn = Mysql_Connection.get("wphplc")

        cursor = conn.cursor()

        sql = "INSERT INTO wph_plc.scanlog (triggerID, barCode, laneAssigned, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)"

        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        val = (triggerId, barcode, laneAssigned, currentTimeStamp, currentTimeStamp)

        cursor.execute(sql, val)

        conn.commit()

        conn.close()

        cursor.close()

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))
        HostLog.dbLog("PLC_Helpers", "db error", exceptionDetails)


def updateScanLogLaneAssigned(laneAssigned, cartonId):
    try:
        conn = Mysql_Connection.get("wphplc")

        cursor = conn.cursor()

        sql = "UPDATE wph_plc.scanlog SET laneAssigned = %s, updated_at = %s WHERE barCode = %s"

        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        val = (laneAssigned, currentTimeStamp, cartonId)

        cursor.execute(sql, val)

        conn.commit()

        conn.close()

        cursor.close()

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))
        HostLog.dbLog("PLC_Helpers", "db error", exceptionDetails)


def addDivertConfirm(cartonId, laneActual, area):
    
    conn = Mysql_Connection.get("wphplc")

    cursor = conn.cursor()

    sql = "INSERT IGNORE INTO wph_assignment.divert_confirm(carton_id, lane_actual, area, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)"

    currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    val = (cartonId, laneActual, area, currentTimeStamp, currentTimeStamp)

    cursor.execute(sql, val)

    conn.commit()

    conn.close()

    cursor.close()


def addWeight(data):
    try:
        cartonId = data[1]
        weightAssign = data[2]

        conn = Mysql_Connection.get("wphapp")

        cursor = conn.cursor()

        sql = "INSERT IGNORE INTO wph_app.weights (carton_id, weight_assign, created_at, updated_at) VALUES (%s, %s, %s, %s)"

        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        val = (cartonId, weightAssign, currentTimeStamp, currentTimeStamp)

        cursor.execute(sql, val)

        conn.commit()

        conn.close()

        cursor.close()

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))
        HostLog.dbLog("PLC_Helpers", "db error", exceptionDetails)


def updateWeight(cartonId, sorterId, weightActual, result, over_under):
    
    conn = Mysql_Connection.get("wphplc")

    cursor = conn.cursor()

    sql = "UPDATE wph_app.weights SET sorter_id = %s, weight_actual = %s, result = %s, over_under = %s, updated_at = %s WHERE carton_id = %s"

    currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    val = (sorterId, weightActual, result, over_under, currentTimeStamp, cartonId)

    cursor.execute(sql, val)

    conn.commit()

    conn.close()

    cursor.close()


def updateWeightRecordWithFinalWeight(finalWeight, cartonId):

    conn = Mysql_Connection.get("wphplc")

    cursor = conn.cursor()

    sql = "UPDATE wph_app.weights SET final_weight = %s, updated_at = %s WHERE carton_id = %s"

    currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    val = (finalWeight, currentTimeStamp, cartonId)

    cursor.execute(sql, val)

    conn.commit()

    conn.close()

    cursor.close()




def getWeightRecordByCartonId(cartonId):
   
    conn = Mysql_Connection.get("wphapp")

    cursor = conn.cursor()

    sql = "select * from weights where carton_id = %s"

    params = (cartonId,)

    cursor.execute(sql, params)

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result


def addPlcProcessErrorRecord(cartonId):
    
    conn = Mysql_Connection.get("wphplc")

    cursor = conn.cursor()

    sql = "INSERT IGNORE INTO wph_assignment.plc_processor_error(carton_id, created_at, updated_at) VALUES (%s, %s, %s)"

    currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    val = (cartonId, currentTimeStamp, currentTimeStamp)

    cursor.execute(sql, val)

    conn.commit()

    conn.close()

    cursor.close()


def addShippingSortRecord(cartonId, area, code, triggerId, laneAssigned):
    conn = Mysql_Connection.get("wphplc")

    cursor = conn.cursor()

    sql = "INSERT IGNORE INTO wph_assignment.shipping_sort(carton_id, area, code, trigger_id, lane_assigned, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)"

    currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    val = (cartonId, area, code, triggerId, laneAssigned, currentTimeStamp, currentTimeStamp)

    cursor.execute(sql, val)

    conn.commit()

    conn.close()

    cursor.close()



def getShippingSortRecordByCartonId(cartonId):
   
    conn = Mysql_Connection.get("assignmentdb")

    cursor = conn.cursor()

    sql = "select * from shipping_sort where carton_id = %s"

    params = (cartonId,)

    cursor.execute(sql, params)

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result



def isPackageWeightWithinToleranceFinal(assignedWeight, actualWeight):
    
    toleranceValues = getWeightToleranceValues()

    percentOver = toleranceValues[0][1]
    percentUnder = toleranceValues[0][2]

    valuesDict = {}

    absoluteValueDiff = abs(assignedWeight - actualWeight)
    result = absoluteValueDiff / assignedWeight
    percentDifference = result * 100

    # average = (assignedWeight + actualWeight) / 2
    # percentDifference = (absoluteValueDiff / average) * 100

    valuesDict["actualWeight"] = actualWeight

    if actualWeight > assignedWeight:
        if percentDifference > percentOver:
            valuesDict["didPassWeightCheck"] = False
            valuesDict["weightCode"] = "OVER"
            valuesDict["percentResult"] = "+" + str(round(percentDifference, 2))
        else: #it's actual weight is over the assigned weight, but within tolerance
            valuesDict["didPassWeightCheck"] = True
            valuesDict["weightCode"] = "PASS"
            valuesDict["percentResult"] = "+" + str(round(percentDifference, 2))
    elif actualWeight < assignedWeight:
        if percentDifference > percentUnder:
            valuesDict["didPassWeightCheck"] = False
            valuesDict["weightCode"] = "UNDER"
            valuesDict["percentResult"] = "-" + str(round(percentDifference, 2))
        else: #the actual weight is under the assigned weight, but within tolerance
            valuesDict["didPassWeightCheck"] = True
            valuesDict["weightCode"] = "PASS"
            valuesDict["percentResult"] = "-" + str(round(percentDifference, 2))
    elif actualWeight == assignedWeight:
            valuesDict["didPassWeightCheck"] = True
            valuesDict["weightCode"] = "PASS"
            valuesDict["percentResult"] = str(round(percentDifference, 2))
    
    return valuesDict





def num_after_point(x):
    s = str(x)
    if not '.' in s:
        return 0
    return len(s) - s.index('.') - 1



def formatWeightActual(calculatedWeight):
    roundedWeight = round(calculatedWeight, 2)
    numberDecimalPlaces = num_after_point(roundedWeight)

    convertedWeight = str(round(calculatedWeight, 2)).replace('.', '')
    if numberDecimalPlaces == 1:
        convertedWeight = convertedWeight + "0"

    weightToSave = convertedWeight.zfill(9)
    return weightToSave
    




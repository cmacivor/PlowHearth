import Mysql_Connection
import sys, traceback
import requests
import datetime
import time
import PLC_Helpers
import python_config
import HostLog
from decimal import Decimal


def getUnprocessCartonRecords():
    try:
        serverParams = python_config.read_server_config()
        batchLimit = serverParams.get('process_carton_limit')

        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        #sql = f"select * from cartons where divert_flag = 0 LIMIT {batchLimit}"
        #sql = "select * from cartons where carton_id = '00000000000008350883'"
        sql = f"select * from cartons inner join divert_confirm on cartons.carton_id = divert_confirm.carton_id where divert_flag = 0 order by divert_confirm.created_at desc LIMIT 1000"

        cursor.execute(sql)

        result = cursor.fetchall()

        cursor.close()
        conn.close()

        return result
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))


def getCartonError(cartonId):
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        sql = "select * from plc_processor_error where carton_id = %s"

        params = (cartonId,)

        cursor.execute(sql, params)

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))


def getWeightRecordByCartonId(cartonId):
    try:
        conn = Mysql_Connection.get("wphapp")

        cursor = conn.cursor()

        sql = "select * from wph_app.weights where carton_id = %s"

        params = (cartonId,)

        cursor.execute(sql, params)

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))


def getDivertConfirmRecordByCartonId(cartonId):
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        sql = "select * from wph_assignment.divert_confirm where carton_id = %s "

        params = (cartonId,)

        cursor.execute(sql, params)

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))


def updateCartonAsDiverted(weightActual, laneAssign, laneActual, reasonCode, cartonId):
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        sql = "UPDATE cartons SET divert_flag = 1, weight_actual = %s, lane_assign = %s, lane_actual = %s, reason_code = %s, updated_at = %s where carton_id = %s"
        
        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        updateValues = (weightActual, laneAssign, laneActual, reasonCode, currentTimeStamp, cartonId)

        cursor.execute(sql, updateValues)

        conn.commit()

        #rowcount = cursor.rowcount

        cursor.close()
        conn.close()

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))



def updateErrorCartonAsDiverted(reasonCode, cartonId):
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        sql = "UPDATE cartons SET divert_flag = 1, divertACK = 1, reason_code = %s, updated_at = %s where carton_id = %s"
        
        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        updateValues = (reasonCode, currentTimeStamp, cartonId)

        cursor.execute(sql, updateValues)

        conn.commit()

        #rowcount = cursor.rowcount

        cursor.close()
        conn.close()

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))



    


def process():
    serverParams = python_config.read_server_config()
    sortModuleApiUrl = serverParams.get('sort_api_url')

    unprocessedCartons = getUnprocessCartonRecords()

    if unprocessedCartons is not None:
        for carton in unprocessedCartons:

            try:

                carton_id = carton[3]

                cartonError = getCartonError(carton_id)
                #if cartonError is not None:
                    #update the carton record with an 02, and divert flag to 1
                    #updateCartonAsDiverted(None, None, None, "02", carton_id)
                    #updateErrorCartonAsDiverted("02", carton_id)

                #else:
                    #get the weight record
                weightRecord = getWeightRecordByCartonId(carton_id)

                if weightRecord is None:
                    print("no weight record for carton id: " + str(carton_id))
                    continue

                #get the divert confirm record
                divertConfirm = getDivertConfirmRecordByCartonId(carton_id)

                if divertConfirm is None:
                    print("no divert confirm record for carton id: " + str(carton_id))
                    continue

                formattedFinalWeight = ""
                finalWeight = weightRecord[7]
                if finalWeight is not None:
                    formattedFinalWeight = PLC_Helpers.formatWeightActual(Decimal(finalWeight))
                else:
                    print("no weight value in weight record")
                    continue
                # formattedFinalWeight = ""
                # if finalWeight is not None:
                #     formattedFinalWeight = PLC_Helpers.formatWeightActual(Decimal(finalWeight))
                # else:
                #     formattedFinalWeight = "000000000"


                laneActual = divertConfirm[2]
                if laneActual is None:
                    print("lane actual is missing for carton id: " + str(carton_id))
                    continue

                shippingSortRecord = PLC_Helpers.getShippingSortRecordByCartonId(carton_id)

                laneAssigned = "00"
                if shippingSortRecord is not None:
                    print('getting lane assignment from api...')
                    shipAction = carton[7]
                    shipVia = carton[6]

                    code = shipAction.strip() + shipVia.strip()
                    triggerId = shippingSortRecord[4]

                    time.sleep(0.5)
                    #get the lane assigned
                    response = requests.get(sortModuleApiUrl + f'/api/sorters/lanes/filter?name=Shipping&trigger_id={triggerId}&barcode={code}')
                    if response is not None or response.text != "" or response.text != "[]" or response.status_code == 200:
                    
                       laneAssigned = response.text.replace("[", "").replace("]", "")
               
                print(laneAssigned)
                updateCartonAsDiverted(formattedFinalWeight, laneAssigned, laneActual, "01", carton_id)
                print("carton record id " + str(carton_id) + "updated, sending to SWMS")

            except Exception:
                print(laneAssigned)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                exceptionDetails = ''.join('!! ' + line for line in lines)
                HostLog.dbLog("Carton Record Processor", "Error", "Error occurred while processing. " + exceptionDetails) 







while True:
    time.sleep(5)
    process()



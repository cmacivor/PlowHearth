import python_config
import time
from pylogix import PLC
import os
import mysql.connector
import requests
import datetime
import sys
import atexit
import Mysql_Connection
import traceback
import PLC_Helpers
import HostLog
import requests



# Data Types
STRUCT = 160
BOOL = 193
SINT = 194
INT = 195
DINT = 196
LINT = 197
USINT = 198
UINT = 199
UDINT = 200
LWORD = 201
REAL = 202
LREAL = 203
DWORD = 211
STRING = 218



plc_ip_config = python_config.read_plc_config()
CP3_PLC_IP = plc_ip_config.get("avasort_plc_ip")

serverParams = python_config.read_server_config()
sortModuleApiUrl = serverParams.get('sort_api_url')


def read_Avasort_WXS_ShippingBagSort(comm):

    #with PLC() as comm:
    comm.IPAddress = CP3_PLC_IP

    triggerBit = False
    
    
    ret = comm.Read("WXS_ShippingBagSort.TxTrigger", datatype=BOOL)
    triggerBit = ret.Value

    tagDict = {}

    #if the TxTrigger is true, we'll get the values of TxTriggerID, TxMesssage.Code, TxMessage.Weight
    if triggerBit == True:
        ret = comm.Read("WXS_ShippingBagSort.TxTriggerID",datatype=UDINT)
        TxTriggerID = ret.Value
        
        ret = comm.Read("WXS_ShippingBagSort.TxMessage.Weight")
        TxMessageWeight = ret.Value
    
        ret = comm.Read("WXS_ShippingBagSort.TxMessage.Code",datatype=STRING)
        TxMessageCode = ret.Value
        
        if "noread" in TxMessageCode.lower():
            TxMessageCode = "No Read"
        elif "multilabel" in TxMessageCode.lower():
            TxMessageCode = "Multi-Read"
        elif TxMessageCode.isspace():
            TxMessageCode = "null"
        else:
            TxMessageCode = ret.Value[5:25]

    
        tagDict["TxTrigger"] = triggerBit
        tagDict["TxTriggerID"] = TxTriggerID
        tagDict["TxMessageCode"] = TxMessageCode
        tagDict["TxWeight"] = TxMessageWeight
        
        return tagDict



while True:
    time.sleep(0.5)
    print('reading PLC...')
    try:
         with PLC() as comm:

            avasort_bagDivertConfirmTags = read_Avasort_WXS_ShippingBagSort(comm)

            if avasort_bagDivertConfirmTags is None:
                continue

            triggerBit = avasort_bagDivertConfirmTags["TxTrigger"] 
            if not triggerBit:
                continue

            # Write to plc_logs table with PLC Lane Request
            PLC_Helpers.addPLCLog("Avasort", "Sorted", "Carton ID: " + str(avasort_bagDivertConfirmTags["TxMessageCode"]))

            # Perform lookup/query to get carton record created from file
            cartonRecord = PLC_Helpers.getCartonByCartonId(avasort_bagDivertConfirmTags["TxMessageCode"])
            if cartonRecord is None:
                PLC_Helpers.addPLCLog("Avasort", "No carton", "No carton record found in cartons table. cartonID: " + str(avasort_bagDivertConfirmTags["TxMessageCode"]))
                comm.Write("WXS_ShippingBagSort.TxTrigger", False)
                continue

            #finalWeight = str(round(avasort_bagDivertConfirmTags["TxWeight"], 2))
            convertedWeight = PLC_Helpers.formatWeightActual(avasort_bagDivertConfirmTags["TxWeight"])

            #PLC_Helpers.updateWeightRecordWithFinalWeight(finalWeight, avasort_bagDivertConfirmTags["TxMessageCode"])
            PLC_Helpers.updateWeight(avasort_bagDivertConfirmTags["TxMessageCode"], "Avasort", convertedWeight, "NA", "NA")

            #get the ship action and ship code from the carton record, and concatenate them together
            shipAction = cartonRecord[7]
            if shipAction is None:
                PLC_Helpers.addPLCLog("Avasort", "No ship", "No ship action found in carton record. cartonID: " + str(avasort_bagDivertConfirmTags["TxMessageCode"]))
                comm.Write("WXS_ShippingBagSort.TxTrigger", False)
                continue

            shipVia = cartonRecord[6]
            if shipVia is None:
                PLC_Helpers.addPLCLog("Avasort", "No ship", "No ship via found in carton record. cartonID: " + str(avasort_bagDivertConfirmTags["TxMessageCode"]))
                comm.Write("WXS_ShippingBagSort.TxTrigger", False)
                continue

            code = shipAction.strip() + shipVia.strip()
            triggerId = avasort_bagDivertConfirmTags["TxTriggerID"]

            #get the lane assigned 
            laneAssigned = requests.get(sortModuleApiUrl + f'/api/sorters/lanes/filter?name=Avasort&trigger_id={triggerId}&barcode={code}')
            if laneAssigned is None or laneAssigned.text == "":
                PLC_Helpers.addPLCLog("Avasort", "no lane", "Unable to retrieve lane assigned from sort API. CartonID: " + str(avasort_bagDivertConfirmTags["TxMessageCode"]))
                comm.Write("WXS_ShippingBagSort.TxTrigger", False)
                continue

            formattedLaneAssigned = laneAssigned.text.replace("[", "").replace("]", "")

            #write the values to the shipping_sort table
            PLC_Helpers.addShippingSortRecord(avasort_bagDivertConfirmTags["TxMessageCode"], "Avasort", code, triggerId, formattedLaneAssigned)
            
            #write the lane assigned to the PLC
            comm.Write("WXS_ShippingBagSort.RxMessage.PrimaryLane", int(formattedLaneAssigned))

            comm.Write("WXS_ShippingBagSort.RxTriggerID", triggerId)

            #set trigger bit to false
            comm.Write("WXS_ShippingBagSort.TxTrigger", False)

          


    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines) 
        PLC_Helpers.addPLCLog("Avasort", "Error", exceptionDetails)

        try:
            #set trigger bit back to false
            comm.Write("Avasort_ShippingBagSort.TxTrigger", False)
            PLC_Helpers.addPlcProcessErrorRecord(avasort_bagDivertConfirmTags["TxMessageCode"])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            PLC_Helpers.addPLCLog("Avasort", "Error", "Unable to communicate with the PLC. " + exceptionDetails)
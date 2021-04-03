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
Avasort_PLC_IP = plc_ip_config.get("avasort_plc_ip")


def read_Avasort_BagDivertConfirm(comm):
    #with PLC() as comm:
    comm.IPAddress = Avasort_PLC_IP

    triggerBit = False
    
    ret = comm.Read("WXS_BagDivertConfirm.TxTrigger", datatype=BOOL)
    triggerBit = ret.Value

    tagDict = {}

    #if the TxTrigger is true, we'll get the values of TxTriggerID, TxMesssage.Code, TxMessage.Weight
    if triggerBit == True:
        ret = comm.Read("WXS_BagDivertConfirm.TxTriggerID",datatype=INT)
        TxTriggerID = ret.Value[0]
        
        ret = comm.Read("WXS_BagDivertConfirm.TxMessage.LaneActual",datatype=INT)
        TxMessageLaneActual = ret.Value

        ret = comm.Read("WXS_BagDivertConfirm.TXMessage.Code",datatype=STRING)
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
        tagDict["LaneActual"] = TxMessageLaneActual
        tagDict["TxMessageCode"] = TxMessageCode
        #tagDict["TxWeight"] = TxWeight

        return tagDict
 



while True:
    time.sleep(0.5)
    print('reading from PLC...')
    try:

        with PLC() as comm:

            avasort_bagDivertConfirmTags = read_Avasort_BagDivertConfirm(comm)

            if avasort_bagDivertConfirmTags is None:
                continue

            triggerBit = avasort_bagDivertConfirmTags["TxTrigger"] 
            if not triggerBit:
                continue

            # Write to plc_logs table with PLC Lane Request
            PLC_Helpers.addPLCLog("Avasort", "Diverted", "Carton ID: " + str(avasort_bagDivertConfirmTags["TxMessageCode"]))

            #get the carton record and use it to get the Ship Via value, write that back to WXS_BagDivertConfirm.RxMessage.CarrierInfo
            cartonRecord = PLC_Helpers.getCartonByCartonId(avasort_bagDivertConfirmTags["TxMessageCode"])
            if cartonRecord is None:
                PLC_Helpers.addPLCLog("Avasort", "No carton", "No carton record found in cartons table. cartonID: " + str(avasort_bagDivertConfirmTags["TxMessageCode"]))
                comm.Write("WXS_BagDivertConfirm.TxTrigger", False)
                continue

            # carrier =  cartonRecord[6].strip()

            # comm.Write("WXS_BagDivertConfirm.RxMessage.CarrierInfo", carrier)

            #write a divert confirm record
            PLC_Helpers.addDivertConfirm(avasort_bagDivertConfirmTags["TxMessageCode"], avasort_bagDivertConfirmTags["LaneActual"], "Avasort")

            comm.Write("WXS_BagDivertConfirm.TxTrigger", False)

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines) 
        PLC_Helpers.addPLCLog("Avasort", "PLC Error", exceptionDetails)

        try:
            #set trigger bit back to false
            comm.Write("WXS_BagDivertConfirm.TxTrigger", False)
            PLC_Helpers.addPlcProcessErrorRecord(avasort_bagDivertConfirmTags["TxMessageCode"])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            PLC_Helpers.addPLCLog("Avasort", "PLC Error", "Unable to communicate with the PLC. " + exceptionDetails) 

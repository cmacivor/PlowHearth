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
CP3_PLC_IP = plc_ip_config.get("cc3_plc_ip")


def read_CC3_BoxDivertConfirm(comm):
    #with PLC() as comm:
    comm.IPAddress = CP3_PLC_IP

    triggerBit = False
    
    ret = comm.Read("WXS_BoxDivertConfirm.TXTrigger", datatype=BOOL)
    triggerBit = ret.Value

    tagDict = {}

    #if the TxTrigger is true, we'll get the values of TxTriggerID, TxMesssage.Code, TxMessage.Weight
    if triggerBit == True:
        ret = comm.Read("WXS_BoxDivertConfirm.TXTriggerID",datatype=INT)
        TxTriggerID = ret.Value[0]
        
        ret = comm.Read("WXS_BoxDivertConfirm.TXMessage.LaneActual",datatype=INT)
        TxMessageLaneActual = ret.Value

        ret = comm.Read("WXS_BoxDivertConfirm.TXMessage.Code",datatype=STRING)
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
    print('reading PLC...')
    try:

        with PLC() as comm:

            cc3_boxDivertConfirmTags = read_CC3_BoxDivertConfirm(comm)

            if cc3_boxDivertConfirmTags is None:
                continue

            triggerBit = cc3_boxDivertConfirmTags["TxTrigger"] 
            if not triggerBit:
                continue

            # Write to plc_logs table with PLC Lane Request
            PLC_Helpers.addPLCLog("CC3", "Diverted", "Carton ID: " + str(cc3_boxDivertConfirmTags["TxMessageCode"]))

            #write a divert confirm record
            PLC_Helpers.addDivertConfirm(cc3_boxDivertConfirmTags["TxMessageCode"], cc3_boxDivertConfirmTags["LaneActual"], "CC3")

            comm.Write("WXS_BoxDivertConfirm.TXTrigger", False)

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines) 
        PLC_Helpers.addPLCLog("CC3", "Error", exceptionDetails)

        try:
            #set trigger bit back to false
            comm.Write("WXS_BoxDivertConfirm.TxTrigger", False)
            PLC_Helpers.addPlcProcessErrorRecord(cc3_boxDivertConfirmTags["TxMessageCode"])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            PLC_Helpers.addPLCLog("CC3", "PLC Error", "Unable to communicate with the PLC. " + exceptionDetails) 

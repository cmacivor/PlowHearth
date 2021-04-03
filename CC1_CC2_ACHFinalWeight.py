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
CP1_2_PLC_IP = plc_ip_config.get("cc1cc2_plc_ip")



def read_CC1CC2_PLC_PHFinalWeight(comm):
    
    #with PLC() as comm:
    comm.IPAddress = CP1_2_PLC_IP

    triggerBit = False
    
    ret = comm.Read("WXS_ACHFinalWeight.TxTrigger", datatype=BOOL)
    triggerBit = ret.Value

    tagDict = {}

    #if the TxTrigger is true, we'll get the values of TxTriggerID, TxMesssage.Code, TxMessage.Weight
    if triggerBit == True:
        
        ret = comm.Read("WXS_ACHFinalWeight.TxMessage.Code",datatype=STRING)
        TxMessageCode = ret.Value
        
        if "noread" in TxMessageCode.lower():
            TxMessageCode = "No Read"
        elif "multilabel" in TxMessageCode.lower():
            TxMessageCode = "Multi-Read"
        elif TxMessageCode.isspace():
            TxMessageCode = "null"
        else:
            #TxMessageCode = str(TxMessageCode)
            TxMessageCode = ret.Value[5:25]


        ret = comm.Read("WXS_ACHFinalWeight.TxMessage.Weight",datatype=REAL)
        TxWeight = ret.Value

    
        tagDict["TxTrigger"] = triggerBit
        #tagDict["TxTriggerID"] = TxTriggerID
        tagDict["TxMessageCode"] = TxMessageCode
        tagDict["TxWeight"] = TxWeight

        return tagDict
 




while True:
    time.sleep(0.5)
    print('reading PLC...')
    try:

        with PLC() as comm:
            #when the TxTrigger goes true:
            # Read values from PLC
            # cc1cc2_phweightchecktags = read_CC1CC2_PLC_ACHWeightCheck(comm) #read_CC1CC2_PLC_PHWeightCheck(comm)
            cc1cc2_phfinalweighttags = read_CC1CC2_PLC_PHFinalWeight(comm)
            if cc1cc2_phfinalweighttags is None:
                continue

            triggerBit = cc1cc2_phfinalweighttags["TxTrigger"] 
            if not triggerBit:
                continue

            PLC_Helpers.addPLCLog("CC1/CC2ACH", "Final Weight", "Carton ID " + str(cc1cc2_phfinalweighttags["TxMessageCode"]))

         
            # Perform lookup/query to get carton record created from file
            cartonRecord = PLC_Helpers.getCartonByCartonId(cc1cc2_phfinalweighttags["TxMessageCode"])
            if cartonRecord is None:
                PLC_Helpers.addPLCLog("CC1/CC2ACH", "No carton", "No carton record found in cartons table. cartonID: " + str(cc1cc2_phfinalweighttags["TxMessageCode"]))
                comm.Write("WXS_ACHFinalWeight.TxTrigger", False)
                continue

            #get the weight record by the carton id, need to see if it exists first:
            weightRecord = PLC_Helpers.getWeightRecordByCartonId(cc1cc2_phfinalweighttags["TxMessageCode"])
            if weightRecord is None:
                PLC_Helpers.addPLCLog("CC1/CC2ACH", "No weight", "No weight record found in weights table. cartonID: " + str(cc1cc2_phfinalweighttags["TxMessageCode"]))
                comm.Write("WXS_ACHFinalWeight.TxTrigger", False)
                continue

            finalWeight = PLC_Helpers.formatWeightActual(cc1cc2_phfinalweighttags["TxWeight"])
            #update the weight record with the final weight value
            PLC_Helpers.updateWeightRecordWithFinalWeight(round(cc1cc2_phfinalweighttags["TxWeight"], 2), cc1cc2_phfinalweighttags["TxMessageCode"])
            #PLC_Helpers.updateWeight(cc1cc2_phfinalweighttags["TxMessageCode"], "CC1CC2", finalWeight, "NA", "NA")

            #set trigger bit back to false
            comm.Write("WXS_ACHFinalWeight.TxTrigger", False)

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines) 
        PLC_Helpers.addPLCLog("CC1/CC2ACH", "Error", exceptionDetails)

        try:
            #set trigger bit back to false
            comm.Write("WXS_ACHFinalWeight.TxTrigger", False)
            PLC_Helpers.addPlcProcessErrorRecord(cc1cc2_phfinalweighttags["TxMessageCode"])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            PLC_Helpers.addPLCLog("CC1/CC2ACH", "PLC Error", "Unable to communicate with the PLC. " + exceptionDetails) 


        
   
        


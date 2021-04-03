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
# CP3_PLC_IP = "10.1.1.17"
# Avasort_PLC_IP = "10.1.1.13"


def read_CC1CC2_PLC_ACHWeightCheck(comm):
    
    #with PLC() as comm:
    comm.IPAddress = CP1_2_PLC_IP

    triggerBit = False
    
    ret = comm.Read("WXS_ACHWeightCheck.TxTrigger", datatype=BOOL)
    triggerBit = ret.Value

    tagDict = {}

    #if the TxTrigger is true, we'll get the values of TxTriggerID, TxMesssage.Code, TxMessage.Weight
    if triggerBit == True:
        ret = comm.Read("WXS_ACHWeightCheck.TXTriggerID",datatype=INT)
        TxTriggerID = ret.Value[0]
        
        ret = comm.Read("WXS_ACHWeightCheck.TxMessage.Code",datatype=STRING)
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


        ret = comm.Read("WXS_ACHWeightCheck.TxMessage.Weight",datatype=REAL)
        TxWeight = ret.Value

    
        tagDict["TxTrigger"] = triggerBit
        tagDict["TxTriggerID"] = TxTriggerID
        tagDict["TxMessageCode"] = TxMessageCode
        tagDict["TxWeight"] = TxWeight

        return tagDict



def writeCartonRecordDataToPLC(didPassWeightCheck, phweightchecktags, comm):
    triggerId = phweightchecktags["TxTriggerID"]
    if didPassWeightCheck:
        #successfulCode = "2" + str(phweightchecktags["TxTriggerID"])
        successfulCode = 2000 + triggerId
        comm.Write("WXS_ACHWeightCheck.RxMessage.PrimaryLane", int(successfulCode))
        comm.Write("WXS_ACHWeightCheck.TxTrigger", False)
        return successfulCode
    else:
        #failureCode = "1" + str(phweightchecktags["TxTriggerID"])
        failureCode = 1000 + triggerId
        comm.Write("WXS_ACHWeightCheck.RxMessage.PrimaryLane", int(failureCode))
        comm.Write("WXS_ACHWeightCheck.TxTrigger", False)
        return failureCode



while True:
    time.sleep(0.1)
    print('reading PLC...')
    try:

        with PLC() as comm:
            #when the TxTrigger goes true:
            # Read values from PLC
            cc1cc2_phweightchecktags = read_CC1CC2_PLC_ACHWeightCheck(comm) #read_CC1CC2_PLC_PHWeightCheck(comm)

            if cc1cc2_phweightchecktags is None:
                continue

            triggerBit = cc1cc2_phweightchecktags["TxTrigger"] 
            if not triggerBit:
                continue

            # Write to plc_logs table with PLC Lane Request
            PLC_Helpers.addPLCLog("CC1/CC2ACH", "Lan Req", "Carton ID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))

            
            # Perform lookup/query to get carton record created from file
            cartonRecord = PLC_Helpers.getCartonByCartonId(cc1cc2_phweightchecktags["TxMessageCode"])
            if cartonRecord is None:
                PLC_Helpers.addPLCLog("CC1/CC2ACH", "No carton", "No carton record found in cartons table. cartonID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))
                comm.Write("WXS_ACHWeightCheck.TxTrigger", False)
                continue


            #get the weight record by the carton id, need to see if it exists first:
            weightRecord = PLC_Helpers.getWeightRecordByCartonId(cc1cc2_phweightchecktags["TxMessageCode"])
            if weightRecord is None:
                PLC_Helpers.addPLCLog("CC1/CC2ACH", "No weight", "No weight record found in weights table. cartonID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))
                comm.Write("WXS_ACHWeightCheck.TxTrigger", False)
                continue
            
            #check the weight against the tolerance
            assignedWeight = cartonRecord[4]
            convertedAssignedWeight = float(assignedWeight[:7] + "." + assignedWeight[7:9])
            weightResults = PLC_Helpers.isPackageWeightWithinToleranceFinal(convertedAssignedWeight, cc1cc2_phweightchecktags["TxWeight"])

            #weightResults = PLC_Helpers.isPackageWeightWithinTolerance(cartonRecord, cc1cc2_phweightchecktags)

            # Write results to PLC, set TxTrigger to False
            weightCode = writeCartonRecordDataToPLC(weightResults["didPassWeightCheck"], cc1cc2_phweightchecktags, comm)
            if weightCode is None:
                PLC_Helpers.addPLCLog("CC1/CC2ACH", "No code", "Weight code could not be determined. cartonID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))
                comm.Write("WXS_ACHWeightCheck.TxTrigger", False)
                break

            convertedWeight = PLC_Helpers.formatWeightActual(weightResults["actualWeight"])

            #update the weight record with the results
            PLC_Helpers.updateWeight(cc1cc2_phweightchecktags["TxMessageCode"], "CC1CC2ACH", convertedWeight, weightResults["weightCode"], weightResults["percentResult"]) 

            
            # Write to plc_logs with PLC Lane Response
            PLC_Helpers.addPLCLog("CC1/CC2ACH", "LanResp", "Carton ID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))

    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines) 
        PLC_Helpers.addPLCLog("CC1/CC2ACH", "Error", exceptionDetails)

        try:
            #set trigger bit back to false
            comm.Write("WXS_ACHWeightCheck.TxTrigger", False)
            PLC_Helpers.addPlcProcessErrorRecord(cc1cc2_phweightchecktags["TxMessageCode"])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            PLC_Helpers.addPLCLog("CC1/CC2ACH", "PLC Error", "Unable to communicate with the PLC. " + exceptionDetails) 
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
from decimal import Decimal


#note on the process:
#when the TxTrigger goes true:
    # Read values from PLC
    # Write to plc_logs table with PLC Lane Request
    # Perform lookup/query
    # Write results to PLC, set TxTrigger to False
    # Update scan_logs table with values from PLC including Lane Assigned and other available info
    # Write to plc_logs with PLC Lane Response
    # Update Container table if needed


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
# CP1_2_PLC_IP = "10.1.1.15"
# CP3_PLC_IP = "10.1.1.17"
# Avasort_PLC_IP = "10.1.1.13"


#reads the PHWeightCheck trigger bit in the CC1/CC2 Area.
def read_CC1CC2_PLC_PHWeightCheck(comm):
   
    #with PLC() as comm:
    comm.IPAddress = CP1_2_PLC_IP

    triggerBit = False
    
    ret = comm.Read("WXS_PHWeightCheck.TxTrigger", datatype=BOOL)
    triggerBit = ret.Value

    tagDict = {}

    #if the TxTrigger is true, we'll get the values of TxTriggerID, TxMesssage.Code, TxMessage.Weight
    if triggerBit == True:
        ret = comm.Read("WXS_PHWeightCheck.TXTriggerID",datatype=INT)
        TxTriggerID = ret.Value[0]
        
        ret = comm.Read("WXS_PHWeightCheck.TxMessage.Code",datatype=STRING)
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


        ret = comm.Read("WXS_PHWeightCheck.TxMessage.Weight",datatype=REAL)
        TxWeight = ret.Value

    
        tagDict["TxTrigger"] = triggerBit
        tagDict["TxTriggerID"] = TxTriggerID
        tagDict["TxMessageCode"] = TxMessageCode
        tagDict["TxWeight"] = TxWeight

        return tagDict




def writeCartonRecordDataToPLC(didPassWeightCheck, phweightchecktags, comm):

    triggerId = phweightchecktags["TxTriggerID"]

    if didPassWeightCheck:
        #successfulCode = "2000" + str(phweightchecktags["TxTriggerID"])
        successfulCode = 2000 + triggerId
        comm.Write("WXS_PHWeightCheck.RxMessage.PrimaryLane", int(successfulCode))
        comm.Write("WXS_PHWeightCheck.TxTrigger", False)
        return successfulCode
    else:
        #failureCode = "1000" + str(phweightchecktags["TxTriggerID"])
        failureCode = 1000 + triggerId
        comm.Write("WXS_PHWeightCheck.RxMessage.PrimaryLane", int(failureCode))
        comm.Write("WXS_PHWeightCheck.TxTrigger", False)
        return failureCode



while True:
    time.sleep(0.1)
    print('reading PLC...')
    try:

        with PLC() as comm:
            #when the TxTrigger goes true:
            # Read values from PLC
            cc1cc2_phweightchecktags = read_CC1CC2_PLC_PHWeightCheck(comm)

            if cc1cc2_phweightchecktags is None:
                continue

            triggerBit = cc1cc2_phweightchecktags["TxTrigger"] 
            if not triggerBit:
                continue

            # Write to plc_logs table with PLC Lane Request
            PLC_Helpers.addPLCLog("CC1/CC2PH", "LanReq", "CartonId: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))

            
            # Perform lookup/query to get carton record created from file
            cartonRecord = PLC_Helpers.getCartonByCartonId(cc1cc2_phweightchecktags["TxMessageCode"])
            if cartonRecord is None:
                PLC_Helpers.addPLCLog("CC1/CC2PH", "No carton", "No carton record found in cartons table. CartonID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))
                comm.Write("WXS_PHWeightCheck.TxTrigger", False)
                continue


            #get the weight record by the carton id, need to see if it exists first:
            weightRecord = PLC_Helpers.getWeightRecordByCartonId(cc1cc2_phweightchecktags["TxMessageCode"])
            if weightRecord is None:
                PLC_Helpers.addPLCLog("CC1/CC2PH", "No weight", "No weight record found in weights table. CartonID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))
                comm.Write("WXS_PHWeightCheck.TxTrigger", False)
                continue

            #check the weight against the tolerance
            #weightResults = PLC_Helpers.isPackageWeightWithinTolerance(cartonRecord, cc1cc2_phweightchecktags)
            assignedWeight = cartonRecord[4]
            convertedAssignedWeight = float(assignedWeight[:7] + "." + assignedWeight[7:9])

            weightResults = PLC_Helpers.isPackageWeightWithinToleranceFinal(convertedAssignedWeight, cc1cc2_phweightchecktags["TxWeight"])

            # Write results to PLC, set TxTrigger to False
            weightCode = writeCartonRecordDataToPLC(weightResults["didPassWeightCheck"], cc1cc2_phweightchecktags, comm)
            if weightCode is None:
                PLC_Helpers.addPLCLog("CC1/CC2PH", "No code", "Weight code could not be determined. CartonID: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))
                comm.Write("WXS_PHWeightCheck.TxTrigger", False)
                continue

            convertedWeight = PLC_Helpers.formatWeightActual(weightResults["actualWeight"])
            
            #update the weight record with the results
            PLC_Helpers.updateWeight(cc1cc2_phweightchecktags["TxMessageCode"], "CC1CC2PH", convertedWeight, weightResults["weightCode"], weightResults["percentResult"]) 

            
            # Write to plc_logs with PLC Lane Response
            PLC_Helpers.addPLCLog("CC1/CC2PH", "LanResp", "CartonId: " + str(cc1cc2_phweightchecktags["TxMessageCode"]))


            # Update Container table if needed
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines) 
        PLC_Helpers.addPLCLog("CC1/CC2PH", "Error", exceptionDetails)

        try:
            #set trigger bit back to false
            comm.Write("WXS_PHWeightCheck.TxTrigger", False)
            PLC_Helpers.addPlcProcessErrorRecord(cc1cc2_phweightchecktags["TxMessageCode"])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            PLC_Helpers.addPLCLog("CC1/CC2PH", "PLC Error", "Unable to communicate with the PLC. " + exceptionDetails) 



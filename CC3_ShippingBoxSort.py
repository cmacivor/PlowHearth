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
CP3_PLC_IP = plc_ip_config.get("cc3_plc_ip")

serverParams = python_config.read_server_config()
sortModuleApiUrl = serverParams.get('sort_api_url')


def read_CC3_WXS_ShippingBoxSort(comm):

    #with PLC() as comm:
    comm.IPAddress = CP3_PLC_IP

    triggerBit = False
    
    
    ret = comm.Read("WXS_ShippingBoxSort.TxTrigger", datatype=BOOL)
    triggerBit = ret.Value

    tagDict = {}

    #if the TxTrigger is true, we'll get the values of TxTriggerID, TxMesssage.Code, TxMessage.Weight
    if triggerBit == True:
        ret = comm.Read("WXS_ShippingBoxSort.TxTriggerID",datatype=INT)
        TxTriggerID = ret.Value[0]
        
    
        ret = comm.Read("WXS_ShippingBoxSort.TxMessage.Code",datatype=STRING)
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
        
        return tagDict

heartbeat = 0
while True:
    time.sleep(0.1)
       
    print('reading PLC...')
    try:

        with PLC() as comm:

            heartbeat = heartbeat + 1
            if heartbeat > 9999:
                heartbeat = 0
            
            cc3_boxDivertConfirmTags = read_CC3_WXS_ShippingBoxSort(comm)

            comm.Write("WXS_ShippingBoxSort.Heartbeat", heartbeat)

            if cc3_boxDivertConfirmTags is None:
                continue

            triggerBit = cc3_boxDivertConfirmTags["TxTrigger"] 
            if not triggerBit:
                continue

            # Write to plc_logs table with PLC Lane Request
            PLC_Helpers.addPLCLog("CC3", "Sorted", "Carton ID: " + str(cc3_boxDivertConfirmTags["TxMessageCode"]))

            triggerId = cc3_boxDivertConfirmTags["TxTriggerID"]

            laneAssigned = ""

            if cc3_boxDivertConfirmTags["TxMessageCode"] == "????????????????????":
               laneAssigned = requests.get(sortModuleApiUrl + f'/api/sorters/lanes/filter?name=Shipping&trigger_id={triggerId}&barcode=????????????????????')
               if laneAssigned is None or laneAssigned.text == "" or laneAssigned.text == "[]":   
                   PLC_Helpers.addPLCLog("CC3", "no lane", "Unable to retrieve lane assigned from sort API. CartonID: " + str(cc3_boxDivertConfirmTags["TxMessageCode"]))
                   comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
                   continue

               laneAssigned =  int(laneAssigned.text.replace("[", "").replace("]", ""))
               rxTriggerIdValue = (laneAssigned * 1000) + triggerId

               PLC_Helpers.addShippingSortRecord(cc3_boxDivertConfirmTags["TxMessageCode"], "CC3", None, triggerId, rxTriggerIdValue)
        
            # echo back the trigger Id, add the triggerId and the lane assigned, assign to RxTriggerId    
               comm.Write("WXS_ShippingBoxSort.RxMessage.PrimaryLane", rxTriggerIdValue)

            # set trigger bit to false
               comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
                
            else:
                
                #check to see if the package has "manifested". If it has, there should be a final_weight value in the weight record
                weightRecord = PLC_Helpers.getWeightRecordByCartonId(cc3_boxDivertConfirmTags["TxMessageCode"])
                finalWeight = weightRecord[7]
                if finalWeight is None:
                    laneAssigned = requests.get(sortModuleApiUrl + f'/api/sorters/lanes/filter?name=Shipping&trigger_id={triggerId}&barcode=NMWR')
                    if laneAssigned is None or laneAssigned.text == "" or laneAssigned.text == "[]":
                        PLC_Helpers.addPLCLog("CC3", "no lane", "The NMWR code is missing from sort API. CartonID: " + str(cc3_boxDivertConfirmTags["TxMessageCode"]))
                        comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
                        continue


                    laneAssigned =  int(laneAssigned.text.replace("[", "").replace("]", ""))
                    rxTriggerIdValue = (laneAssigned * 1000) + triggerId
                    PLC_Helpers.addShippingSortRecord(cc3_boxDivertConfirmTags["TxMessageCode"], "CC3", None, triggerId, rxTriggerIdValue)
                    comm.Write("WXS_ShippingBoxSort.RxMessage.PrimaryLane", rxTriggerIdValue)
                    comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
                             
                else:
                    #get the ship action and ship code from the carton record, and concatenate them together
                    # Perform lookup/query to get carton record created from file
                    cartonRecord = PLC_Helpers.getCartonByCartonId(cc3_boxDivertConfirmTags["TxMessageCode"])
                    if cartonRecord is None:
                        PLC_Helpers.addPLCLog("CC3", "No carton", "No carton record found in cartons table. cartonID: " + str(cc3_boxDivertConfirmTags["TxMessageCode"]))
                        comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
                        continue

                    shipAction = cartonRecord[7]
                    shipVia = cartonRecord[6]

                    code = shipAction.strip() + shipVia.strip()

                    #get the lane assigned
                    laneAssigned = requests.get(sortModuleApiUrl + f'/api/sorters/lanes/filter?name=Shipping&trigger_id={triggerId}&barcode={code}')
                    if laneAssigned is None or laneAssigned.text == "" or laneAssigned.text == "[]" :
                        PLC_Helpers.addPLCLog("CC3", "no lane", "Unable to retrieve lane assigned from sort API. CartonID: " + str(cc3_boxDivertConfirmTags["TxMessageCode"]))
                        comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
                        continue

                    #formattedLaneAssigned = laneAssigned.text.replace("[", "").replace("]", "") + str(cc3_boxDivertConfirmTags["TxTriggerID"])
                    #rxTriggerIdValue = triggerId + cc3_boxDivertConfirmTags["TxTriggerID"]
                    laneAssigned =  int(laneAssigned.text.replace("[", "").replace("]", ""))
                    rxTriggerIdValue = (laneAssigned * 1000) + triggerId

                    #write the values to the shipping_sort table
                    PLC_Helpers.addShippingSortRecord(cc3_boxDivertConfirmTags["TxMessageCode"], "CC3", code, triggerId, rxTriggerIdValue)
                    
                    #write the lane assigned to the PLC
                    #comm.Write("WXS_ShippingBoxSort.RxMessage.PrimaryLane", int(formattedLaneAssigned))

                    #echo back the trigger Id, add the triggerId and the lane assigned, assign to RxTriggerId    
                    comm.Write("WXS_ShippingBoxSort.RxMessage.PrimaryLane", rxTriggerIdValue)


                    #set trigger bit to false
                    comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
    
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines) 
        PLC_Helpers.addPLCLog("CC3", "Error", exceptionDetails)

        try:
            #set trigger bit back to false
            comm.Write("WXS_ShippingBoxSort.TxTrigger", False)
            PLC_Helpers.addPlcProcessErrorRecord(cc3_boxDivertConfirmTags["TxMessageCode"])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            PLC_Helpers.addPLCLog("CC3", "Error", "Unable to communicate with the PLC. " + exceptionDetails)
            


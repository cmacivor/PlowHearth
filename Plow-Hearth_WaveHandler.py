import os
import time
import shutil
import python_config
import Mysql_Connection
import CartonManager
import HostLog
import logging
from logging.handlers import RotatingFileHandler
import traceback
import sys
import datetime

loggingConfig = python_config.read_logging_config()
logFileLocation = loggingConfig.get('wavehandlerfilelocation')

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
logFile = logFileLocation #'C:\\socketserver\\DivertConfirmationClientLog'

my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024, 
                                 backupCount=2, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(my_handler)

config = python_config.read_fileconverter_config()
download_path = config.get('output_path')
processed_path = config.get('input_processed_path')
error_path = config.get('error_folder')

connection = Mysql_Connection.get("assignmentdb")
cursor = connection.cursor()

def updateFileProcessedCode(isError, fileName):
    try:
        conn = Mysql_Connection.get("assignmentdb")

        cursor = conn.cursor()

        sql = "UPDATE cartons SET file_process_message_type = %s, updated_at = %s where file_name = %s"

        currentTimeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        updateValues = None
        if isError:
            updateValues = ("02", currentTimeStamp, fileName)
        else:
            updateValues= ("01", currentTimeStamp, fileName)

        cursor.execute(sql, updateValues)

        conn.commit()

        rowcount = cursor.rowcount

        cursor.close()
        conn.close()

        return rowcount
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exceptionDetails = ''.join('!! ' + line for line in lines)
        print(''.join('!! ' + line for line in lines))

def parseWaveFiles():
    filelist = [ f for f in os.listdir(download_path) if f.endswith(".txt") ]
    if len(filelist) == 0:
        print("no files to process")
        return
    for f in filelist:
        try:
            processFile(f)
            return str(len(filelist)) + " files left to process"

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            print(''.join('!! ' + line for line in lines))
            #log the error
            print(e)
            HostLog.log("WaveHandler", "File Error", "file " + f + " failed to process")
            app_log.error(exceptionDetails)

 

def processFile(file_name):
    add_counter = 0
    update_counter = 0
    delete_counter = 0
    file_path = os.path.join(download_path, file_name)
    #fileContentRecordCount = 0 #the number of lines in the file
    fileRecordCount = 0 #the number in the header
    with open(file_path) as fp:
        try:
            count=0 
            for line in fp: 
                count += 1
                if count == 1:
                    headerRecord = line.split("|")
                    fileRecordCount = int(headerRecord[1])
                    
                if count != 1: #this gets everything after the header
                    data = line.split("|")
                    if len(data) > 1:
                        CartonManager.processAction(data, file_name, fileRecordCount)
                        if data[5] == 'A':
                            add_counter = add_counter + 1

                        elif data[5] == 'M':
                            update_counter = update_counter + 1

                        elif data[5] == 'D':
                            delete_counter = delete_counter + 1
            #WPH-11
            if count != 0 and fileRecordCount != 0:
                if count - 1 != fileRecordCount:
                    countMisMatchMessage = "File %s was processed, but the count in the header of the file mismatches the number found in the file" % (file_name)
                    HostLog.log("Wave Handler", "Error", countMisMatchMessage)
                    recordsUpdated = updateFileProcessedCode(True, file_name)
                    if recordsUpdated > 0:
                        HostLog.log("WaveHandler", "INFO", str(recordsUpdated) +  " records updated with the value of 02. File Name: " + file_name)
                    else:
                        HostLog.log("WaveHandler", "INFO", "No records with file name " + file_name + " were updated")
                    fp.close()
                    shutil.move(os.path.join(download_path, file_name), os.path.join(error_path, file_name))
                    return

            message = "File %s was processed with | %s records Added | %s records Modified | %s records Deleted" % (file_name, add_counter, update_counter, delete_counter)
            HostLog.log("Wave Handler", "Table Modify", message)
            updateFileProcessedCode(False, file_name)
            fp.close()
            moveFileToProcessedPath(file_name)
            print(message)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exceptionDetails = ''.join('!! ' + line for line in lines)
            app_log.error(exceptionDetails)
            HostLog.log("WaveHandler", "Record Error", "An error occurred while processing contents of " + file_name)
            #if this happens, an error occurred while processing the contents of the record. Here we'll move it to the error folder, and update any message
            #that matches the carton Id and file name as "O2"
            recordsUpdated = updateFileProcessedCode(True, file_name)
            if recordsUpdated > 0:
                HostLog.log("WaveHandler", "INFO", str(recordsUpdated) +  " records updated with the value of 02. File Name: " + file_name)
            else:
                HostLog.log("WaveHandler", "INFO", "No records with file name " + file_name + " were updated")
            #also we'll move the file to the error  folder
            fp.close()
            shutil.move(os.path.join(download_path, file_name), os.path.join(error_path, file_name))
            
            #WPH-23- create a carton record with error code of 02 to send to the WMS
            #errorRecord = ["00000000000000000000", "000000000", "000000000", "0000", "00" ]
            #CartonManager.add(errorRecord, file_name, 0)

            print(e)


def moveFileToProcessedPath(file_name):
    shutil.move(os.path.join(download_path, file_name), os.path.join(processed_path, file_name))



while True:
    print(parseWaveFiles())

    time.sleep(1)

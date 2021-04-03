import os
import time
from datetime import datetime
import python_config
import Mysql_Connection
import PLC_Helpers


def add(data, fileName, fileRecordCount):

    if len(data[1]) != 20:
        raise Exception("Carton ID is not the correct length")

    if len(data[2]) != 9:
        raise Exception("Weight Assign is not the correct length")

    if len(data[3]) != 4:
        raise Exception("Ship Via is not the correct length")

    if len(data[4]) != 2:
        raise Exception("Shipping Action is not the correct length")

    connection = Mysql_Connection.get("assignmentdb")
    cursor = connection.cursor()
    sql = "INSERT IGNORE INTO cartons (file_name, record_count, carton_id, weight_assign, ship_via, ship_action, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    currentTimeStamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    val = (fileName, fileRecordCount, data[1], data[2], data[3], data[4], currentTimeStamp, currentTimeStamp)
    cursor.execute(sql, val)
    connection.commit()
    connection.close()
    cursor.close()

def update(data):
    if len(data[1]) != 20:
        raise Exception("Carton ID is not the correct length")

    if len(data[2]) != 9:
        raise Exception("Weight Assign is not the correct length")

    if len(data[3]) != 4:
        raise Exception("Ship Via is not the correct length")

    connection = Mysql_Connection.get("assignmentdb")
    cursor = connection.cursor()
    sql = "UPDATE cartons SET weight_assign = %s, ship_via = %s, ship_action = %s, updated_at = %s WHERE carton_id = %s"
    currentTimeStamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    val = (data[2], data[3], data[4], currentTimeStamp, data[1])
    cursor.execute(sql, val)
    connection.commit()
    connection.close()
    cursor.close()

def delete(carton_id):
    connection = Mysql_Connection.get("assignmentdb")
    cursor = connection.cursor()
    sql = "DELETE FROM cartons WHERE carton_id = '"+ carton_id +"'"
    cursor.execute(sql)
    connection.commit()
    connection.close()
    cursor.close()

def processAction(data, fileName, fileRecordCount):
    if data[5] == 'A':
        add(data, fileName, fileRecordCount)
        PLC_Helpers.addWeight(data)

    elif data[5] == 'M':
        update(data)

    elif data[5] == 'D':
        delete(data[1])

    else:
        raise Exception("Unknown value in action type field")


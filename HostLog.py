import time
import mysql.connector
from datetime import datetime
import Mysql_Connection


def log(source, m_type, message):
    dbLog(source, m_type, message)

def dbLog(source, m_typ, message):
    try:
        connection = Mysql_Connection.get("assignmentdb")
        cursor = connection.cursor()
        currentTimeStamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        insertLogSql = ("INSERT INTO host_logs "
                                "(source, type, message, created_at, updated_at) "
                                "VALUES (%s, %s, %s, %s, %s)")
        
        parsedMessage = str(message).replace("\\", "").replace("\x02", "").replace("\x03", "")
        
        newLog = (source, m_typ, parsedMessage, currentTimeStamp, currentTimeStamp)

        cursor.execute(insertLogSql, newLog)
        connection.commit()
    except Exception as e:
        print(e)
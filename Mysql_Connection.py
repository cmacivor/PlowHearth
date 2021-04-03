import python_config
import mysql.connector

def get(database= 'database'):
    config = python_config.read_db_config()
    host = config.get('host')
    user = config.get('user')
    database = config.get(database)
    password = config.get('password')

    con = mysql.connector.connect(
                            host= host, 
                            user= user, 
                            database= database, 
                            password= password 
                        )

    return con
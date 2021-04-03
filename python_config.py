from configparser import SafeConfigParser
import os


def read_db_config(filename='config.ini', section='mysql'):
    """ Read database configuration file and return a dictionary object
    :param filename: name of the configuration file
    :param section: section of database configuration
    :return: a dictionary of database parameters
    """
    # create parser and read ini configuration file
    parser = SafeConfigParser()
    
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    initfile = os.path.join(thisfolder, 'config.ini')

    parser.read(initfile)

    # get section, default to mysql
    db = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            db[item[0]] = item[1]
    else:
        raise Exception('{0} not found in the {1} file'.format(section, filename))

    return db

def read_logging_config(filename='config.ini', section='logging'):
    parser = SafeConfigParser()
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    initfile = os.path.join(thisfolder, 'config.ini')
    parser.read(initfile)

    loggingInfo = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            loggingInfo[item[0]] = item[1]
    else:
        raise Exception('{0} not found in the {1} file'.format(section, filename))

    return loggingInfo

def read_server_config(filename='config.ini', section='ServerParams'):
    parser = SafeConfigParser()
    parser.read(filename)

    serverParams = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            serverParams[item[0]] = item[1]
    else:
        raise Exception('{0} not found in the {1} file'.format(section, filename))

    return serverParams

def read_fileconverter_config(filename='config.ini', section='FileConverterParams'):
    parser = SafeConfigParser()
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    initfile = os.path.join(thisfolder, 'config.ini')
    parser.read(initfile)

    fileConverterParams = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            fileConverterParams[item[0]] = item[1]
    else:
        raise Exception('{0} not found in the {1} file'.format(section, filename))

    return fileConverterParams


def read_plc_config(filename='config.ini', section='PLCParams'):
    parser = SafeConfigParser()
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    initfile = os.path.join(thisfolder, 'config.ini')
    parser.read(initfile)

    fileConverterParams = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            fileConverterParams[item[0]] = item[1]
    else:
        raise Exception('{0} not found in the {1} file'.format(section, filename))

    return fileConverterParams
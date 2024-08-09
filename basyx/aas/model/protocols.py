from enum import Enum


class Protocol(Enum):
    HTTP = "HTTP"
    MQTT = "MQTT"
    MODBUS = "MODBUS"
    COUCHDB = "COUCHDB"

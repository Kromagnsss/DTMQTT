"""Constants for Diematic MQTT bridge integration."""

DOMAIN = "diematic_to_mqtt"
PLATFORMS: list[str] = []

CONF_MODBUS_HOST = "modbus_host"
CONF_MODBUS_PORT = "modbus_port"
CONF_REGULATOR_TYPE = "regulator_type"
CONF_REGULATOR_ADDRESS = "regulator_address"
CONF_INTERFACE_ADDRESS = "interface_address"
CONF_PERIOD = "period"
CONF_TIMEZONE = "timezone"
CONF_TIME_SYNC = "time_sync"
CONF_ENABLE_CIRCUIT_A = "enable_circuit_a"
CONF_ENABLE_CIRCUIT_B = "enable_circuit_b"
CONF_MQTT_HOST = "mqtt_host"
CONF_MQTT_PORT = "mqtt_port"
CONF_MQTT_USERNAME = "mqtt_username"
CONF_MQTT_PASSWORD = "mqtt_password"
CONF_MQTT_CLIENT_ID = "mqtt_client_id"
CONF_MQTT_TOPIC_PREFIX = "mqtt_topic_prefix"
CONF_DISCOVERY_ENABLED = "discovery_enabled"
CONF_DISCOVERY_PREFIX = "discovery_prefix"

DEFAULT_NAME = "Diematic MQTT"
DEFAULT_MODBUS_PORT = 8899
DEFAULT_REGULATOR_TYPE = "Diematic3"
DEFAULT_REGULATOR_ADDRESS = 0x01
DEFAULT_INTERFACE_ADDRESS = 0x00
DEFAULT_PERIOD = 60
DEFAULT_TIME_SYNC = False
DEFAULT_ENABLE_CIRCUIT_A = False
DEFAULT_ENABLE_CIRCUIT_B = False
DEFAULT_MQTT_HOST = "127.0.0.1"
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_CLIENT_ID = "diematic"
DEFAULT_MQTT_TOPIC_PREFIX = "boiler"
DEFAULT_DISCOVERY_ENABLED = True
DEFAULT_DISCOVERY_PREFIX = "homeassistant"

REGULATOR_TYPES = ["Diematic3", "Diematic4", "DiematicDelta"]
ONLINE = "Online"
OFFLINE = "Offline"

"""Constants for the WLANThermo integration."""

DOMAIN = "wlanthermo"

# Configuration
CONF_DEVICE_NAME = "device_name"
CONF_TOPIC_PREFIX = "topic_prefix"

# MQTT Topics
TOPIC_STATUS_DATA = "status/data"
TOPIC_STATUS_SETTINGS = "status/settings"
TOPIC_SET_CHANNELS = "set/channels"
TOPIC_SET_PITMASTER = "set/pitmaster"

# Default values
DEFAULT_NAME = "WLANThermo"
DEFAULT_TOPIC_PREFIX = "WLanThermo/MINI-V3"

# Attributes
ATTR_CHANNEL = "channel"
ATTR_MIN_TEMP = "min_temp"
ATTR_MAX_TEMP = "max_temp"
ATTR_ALARM_MIN = "alarm_min"
ATTR_ALARM_MAX = "alarm_max"
ATTR_SENSOR_TYPE = "sensor_type"
ATTR_COLOR = "color"
ATTR_FIXED = "fixed"
ATTR_PID = "pid"
ATTR_SET_TEMP = "set_temp"
ATTR_MODE = "mode"

# Pitmaster Modes
PITMASTER_MODES = ["manual", "auto", "off"]  # Example, needs verification

# Data keys
DATA_COORDINATOR = "coordinator"
DATA_MQTT_UNSUBSCRIBE = "mqtt_unsubscribe"

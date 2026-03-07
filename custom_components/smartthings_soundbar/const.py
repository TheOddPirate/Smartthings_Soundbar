"""Constants for the SmartThings Soundbar integration."""
from homeassistant.const import CONF_API_KEY, CONF_DEVICE_ID, CONF_NAME

DOMAIN = "smartthings_soundbar"
DEFAULT_NAME = "SmartThings Soundbar"
DEFAULT_MAX_VOLUME = 100

CONF_MAX_VOLUME = "max_volume"
CONF_SOURCE_MAP = "source_map"

# Default source mapping (fallback for compatibility)
DEFAULT_SOURCE_MAP = {
    "HDMI1": {"sbMode": 3},
    "HDMI2": {"sbMode": 20},
    "digital": {"sbMode": 10},
    "wifi": {"sbMode": 25},
}

# Service constants
SERVICE_ADD_SOURCE_MAPPING = "add_source_mapping"
SERVICE_REMOVE_SOURCE_MAPPING = "remove_source_mapping"
SERVICE_CLEAR_SOURCE_MAPPINGS = "clear_source_mappings"

ATTR_SOURCE_NAME = "source_name"
ATTR_SB_MODE = "sb_mode"
ATTR_DEVICE_ID = "device_id"

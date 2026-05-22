import logging
import voluptuous as vol

from .api import SoundbarApi
from .const import CONF_MAX_VOLUME, DEFAULT_MAX_VOLUME, DEFAULT_NAME, DOMAIN

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
    PLATFORM_SCHEMA,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME, CONF_API_KEY, CONF_DEVICE_ID, STATE_UNAVAILABLE
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

SUPPORT_SMARTTHINGS_SOUNDBAR = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_MAX_VOLUME, default=DEFAULT_MAX_VOLUME): cv.positive_int,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartThings Soundbar media player from a config entry."""
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    api_key = entry.data[CONF_API_KEY]
    device_id = entry.data[CONF_DEVICE_ID]
    max_volume = entry.data.get(CONF_MAX_VOLUME, DEFAULT_MAX_VOLUME)
    
    async_add_entities([SmartThingsSoundbarMediaPlayer(name, api_key, device_id, max_volume)])


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the SmartThings Soundbar platform (legacy)."""
    name = config.get(CONF_NAME)
    api_key = config.get(CONF_API_KEY)
    device_id = config.get(CONF_DEVICE_ID)
    max_volume = config.get(CONF_MAX_VOLUME)
    add_entities([SmartThingsSoundbarMediaPlayer(name, api_key, device_id, max_volume)])
    # Auto-load select platform for sound mode using the same config
    try:
        load_platform(
            hass,
            "select",
            "smartthings_soundbar",
            {CONF_NAME: f"{name} Sound Mode", CONF_API_KEY: api_key, CONF_DEVICE_ID: device_id},
            config,
        )
    except Exception as ex:
        _LOGGER.warning("Failed to load sound mode select platform: %s", ex)


class SmartThingsSoundbarMediaPlayer(MediaPlayerEntity):

    def __init__(self, name, api_key, device_id, max_volume):
        self._name = name
        self._model = "default"
        self._sbMode = 0
        self._device_id = device_id
        self._api_key = api_key
        self._max_volume = max_volume
        self._volume = 1
        self._muted = False
        self._playing = True
        self._state = "on"
        self._source = ""
        self._source_list = []
        self._media_title = ""
        self._media_artist = None
        self._media_album = None
        self._media_image_url = None
        self._media_duration = None
        self._media_position = None
        self._sound_from = None

    def update(self):
        SoundbarApi.device_update(self)

    @property
    def unique_id(self) -> str | None:
        return f"SmartThings_Soundbar_{self._device_id}"

    def turn_off(self):
        arg = ""
        cmdtype = "switch_off"
        SoundbarApi.send_command(self, arg, cmdtype)

    def turn_on(self):
        arg = ""
        cmdtype = "switch_on"
        SoundbarApi.send_command(self, arg, cmdtype)

    def set_volume_level(self, arg, cmdtype="setvolume"):
        SoundbarApi.send_command(self, arg, cmdtype)

    def mute_volume(self, mute, cmdtype="audiomute"):
        SoundbarApi.send_command(self, mute, cmdtype)

    def volume_up(self, cmdtype="stepvolume"):
        arg = "up"
        SoundbarApi.send_command(self, arg, cmdtype)

    def volume_down(self, cmdtype="stepvolume"):
        arg = ""
        SoundbarApi.send_command(self, arg, cmdtype)

    def select_source(self, source, cmdtype="selectsource"):
        SoundbarApi.send_command(self, source, cmdtype)

    def select_sound_mode(self, sound_mode):
        SoundbarApi.send_command(self, sound_mode, "selectsoundmode")

    @property
    def device_class(self):
        return MediaPlayerDeviceClass.SPEAKER

    @property
    def supported_features(self):
        return SUPPORT_SMARTTHINGS_SOUNDBAR

    @property
    def available(self):
        return self._state != STATE_UNAVAILABLE

    @property
    def should_poll(self):
        return True

    @property
    def name(self):
        return self._name

    @property
    def media_title(self):
        return self._media_title

    @property
    def media_artist(self):
        return self._media_artist

    @property
    def media_album_name(self):
        return self._media_album

    @property
    def media_image_url(self):
        return self._media_image_url

    @property
    def media_duration(self):
        return self._media_duration

    @property
    def media_position(self):
        return self._media_position

    def media_play(self):
        arg = ""
        cmdtype = "play"
        SoundbarApi.send_command(self, arg, cmdtype)
        # Optimistically reflect state
        self._state = "playing"
        self.schedule_update_ha_state()

    def media_pause(self):
        arg = ""
        cmdtype = "pause"
        SoundbarApi.send_command(self, arg, cmdtype)
        # Optimistically reflect state
        self._state = "paused"
        self.schedule_update_ha_state()

    def media_play_pause(self):
        # Toggle based on current state
        if self._state == "playing":
            self.media_pause()
        else:
            self.media_play()

    @property
    def state(self):
        return self._state

    @property
    def is_volume_muted(self):
        return self._muted

    @property
    def volume_level(self):
        return self._volume

    @property
    def source(self):
        return self._source

    @property
    def source_list(self):
        return self._source_list

    @property
    def extra_state_attributes(self):
        attributes = {}

        if self._sound_from is not None:
            attributes["sound_from"] = self._sound_from

        if self._media_artist is not None:
            attributes["media_artist"] = self._media_artist
        if self._media_album is not None:
            attributes["media_album"] = self._media_album
        if self._model is not None:
            attributes["soundbar_model"] = self._model
        if self._sbMode is not None:
            attributes["sbMode"] = self._sbMode
            
            

        return attributes

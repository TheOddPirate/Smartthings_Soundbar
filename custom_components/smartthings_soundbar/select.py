import logging
import voluptuous as vol

from .api import SoundbarApi, DEFAULT_SOUND_MODES
from .const import DOMAIN

from homeassistant.components.select import (
    SelectEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_call_later
from homeassistant.const import (
    CONF_NAME,
    CONF_API_KEY,
    CONF_DEVICE_ID,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Sound Mode"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SmartThings Soundbar select from a config entry."""
    name = f"{entry.data.get(CONF_NAME, 'SmartThings Soundbar')} Sound Mode"
    api_key = entry.data[CONF_API_KEY]
    device_id = entry.data[CONF_DEVICE_ID]
    
    async_add_entities([SmartThingsSoundbarSoundModeSelect(name, api_key, device_id)])


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the SmartThings Soundbar select platform (legacy)."""
    cfg = discovery_info or config or {}
    name = cfg.get(CONF_NAME, DEFAULT_NAME)
    api_key = cfg.get(CONF_API_KEY)
    device_id = cfg.get(CONF_DEVICE_ID)
    add_entities([SmartThingsSoundbarSoundModeSelect(name, api_key, device_id)])


class SmartThingsSoundbarSoundModeSelect(SelectEntity):
    def __init__(self, name: str, api_key: str, device_id: str | None):
        self._name = name
        self._device_id = device_id or ""
        self._api_key = api_key
        self._sound_mode: str | None = None  # raw api value
        self._sound_mode_list: list[str] = list(DEFAULT_SOUND_MODES)  # raw api values
        self._sound_mode_raw: str | None = None
        # ensure ha knows options immediately
        self._attr_options = list(self._sound_mode_list)

    def _normalize(self, value: str) -> str:
        return value.strip().lower().replace(" ", "").replace("_", "")

    def update(self) -> None:
        SoundbarApi.soundmode_update(self)
        # keep options in sync for validation
        self._attr_options = list(self._sound_mode_list or DEFAULT_SOUND_MODES)

    @property
    def should_poll(self) -> bool:
        return True

    @property
    def unique_id(self) -> str | None:
        return f"SmartThings_Soundbar_{self._device_id}_soundmode"

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def options(self) -> list[str]:
        return self._sound_mode_list or list(DEFAULT_SOUND_MODES)

    @property
    def current_option(self) -> str | None:
        return self._sound_mode

    def select_option(self, option: str) -> None:
        # Ensure we pass normalized api value (lowercase, no spaces)
        norm = self._normalize(option)
        # Map normalization back to one of known options if needed
        candidates = {self._normalize(x): x for x in (self._sound_mode_list or DEFAULT_SOUND_MODES)}
        api_value = candidates.get(norm, option.strip().lower())
        SoundbarApi.send_command(self, api_value, "selectsoundmode")
        self._sound_mode = api_value
        self._sound_mode_raw = api_value
        self.schedule_update_ha_state()
        # Schedule delayed refresh to let device apply mode and publish state
        try:
            async_call_later(self.hass, 5.0, self._async_delayed_refresh)
        except Exception:
            pass

    async def _async_delayed_refresh(self, _now) -> None:
        try:
            await self.hass.async_add_executor_job(SoundbarApi.soundmode_update, self)
        finally:
            self.async_schedule_update_ha_state()

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._sound_mode_raw is not None:
            attrs["raw_sound_mode"] = self._sound_mode_raw
        return attrs

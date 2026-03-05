import json
import logging
import requests
from homeassistant.const import (STATE_OFF, STATE_ON, STATE_PAUSED, STATE_PLAYING, STATE_UNAVAILABLE)

API_BASEURL = "https://api.smartthings.com/v1"
API_DEVICES = API_BASEURL + "/devices/"
COMMAND_POWER_ON = "{'commands': [{'component': 'main','capability': 'switch','command': 'on'}]}"
COMMAND_POWER_OFF = "{'commands': [{'component': 'main','capability': 'switch','command': 'off'}]}"
COMMAND_REFRESH = "{'commands':[{'component': 'main','capability': 'refresh','command': 'refresh'}]}"
COMMAND_PAUSE = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'pause'}]}"
COMMAND_MUTE = "{'commands':[{'component': 'main','capability': 'audioMute','command': 'mute'}]}"
COMMAND_UNMUTE = "{'commands':[{'component': 'main','capability': 'audioMute','command': 'unmute'}]}"
COMMAND_PLAY = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'play'}]}"
COMMAND_STOP = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'stop'}]}"
COMMAND_REWIND = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'rewind'}]}"
COMMAND_FAST_FORWARD = "{'commands':[{'component': 'main','capability': 'mediaPlayback','command': 'fastForward'}]}"

CONTROLLABLE_SOURCES = ["bluetooth", "wifi"]

DEFAULT_SOUND_MODES = [
    "standard",
    "adaptive sound",
    "game",
    "surround",
]


class SoundbarApi:

    @staticmethod
    def device_update(entity):
        API_KEY = entity._api_key
        REQUEST_HEADERS = {"Authorization": "Bearer " + API_KEY}
        DEVICE_ID = entity._device_id
        API_DEVICE = API_DEVICES + DEVICE_ID
        API_DEVICE_STATUS = API_DEVICE + "/states"
        API_COMMAND = API_DEVICE + "/commands"

        try:
            requests.post(API_COMMAND, data=COMMAND_REFRESH, headers=REQUEST_HEADERS, timeout=10)
            resp = requests.get(API_DEVICE_STATUS, headers=REQUEST_HEADERS, timeout=10)
            if resp.status_code != 200:
                entity._state = STATE_UNAVAILABLE
                return
            data = resp.json()
        except requests.RequestException as ex:
            logging.getLogger(__name__).warning("SoundbarApi device_update network error: %s", ex)
            entity._state = STATE_UNAVAILABLE
            return
        except ValueError as ex:
            logging.getLogger(__name__).warning("SoundbarApi device_update invalid JSON: %s", ex)
            entity._state = STATE_UNAVAILABLE
            return

        switch_state = SoundbarApi.extractor(data, "main.switch.value")
        if switch_state is None:
            entity._state = STATE_UNAVAILABLE
            return
        playback_state = SoundbarApi.extractor(data, "main.playbackStatus.value")
        device_source = SoundbarApi.extractor(data, "main.inputSource.value")
        supported_sources_raw = SoundbarApi.extractor(data, "main.supportedInputSources.value")
        try:
            device_all_sources = json.loads(supported_sources_raw) if isinstance(supported_sources_raw, str) else supported_sources_raw
        except Exception:
            device_all_sources = []
        device_muted = SoundbarApi.extractor(data, "main.mute.value") != "unmuted"
        device_volume_raw = SoundbarApi.extractor(data, "main.volume.value")
        try:
            device_volume_val = int(device_volume_raw)
        except Exception:
            device_volume_val = 0
        device_volume = min(device_volume_val / entity._max_volume, 1)
        device_sound_from = SoundbarApi.extractor(data, "main.detailName.value")
        # Map AirPlay/Chromecast origin to wifi source for consistency
        try:
            if isinstance(device_sound_from, str):
                origin_norm = device_sound_from.strip().lower()
                if origin_norm in ("airplay", "chromecast built-in"):
                    device_source = "wifi"
        except Exception:
            pass

        if switch_state == "on":
            # Reflect playback state when available regardless of source
            if playback_state == "playing":
                entity._state = STATE_PLAYING
            elif playback_state == "paused":
                entity._state = STATE_PAUSED
            else:
                entity._state = STATE_ON
        else:
            entity._state = STATE_OFF
        entity._volume = device_volume
        try:
            entity._source_list = device_all_sources if isinstance(device_all_sources, list) else device_all_sources["value"]
        except Exception:
            entity._source_list = []
        entity._muted = device_muted
        entity._source = device_source
        entity._sound_from = device_sound_from if device_sound_from is not None else entity._sound_from
        try:
            if entity._state in [STATE_PLAYING, STATE_PAUSED] and 'trackDescription' in data.get('main', {}):
                entity._media_title = SoundbarApi.extractor(data, "main.trackDescription.value")
            else:
                entity._media_title = None
        except Exception:
            entity._media_title = None

        # Build media metadata
        media_title = None
        media_artist = None
        media_album = None
        media_image_url = None
        media_duration = None
        media_position = None

        # 1) SmartThings often provides audioTrackData (JSON/dict)
        atd = SoundbarApi.extractor(data, "main.audioTrackData.value")
        if atd is not None:
            try:
                if isinstance(atd, str):
                    atd_parsed = json.loads(atd)
                else:
                    atd_parsed = atd
                media_title = atd_parsed.get("title") or atd_parsed.get("track")
                media_artist = atd_parsed.get("artist")
                media_album = atd_parsed.get("album")
                media_image_url = atd_parsed.get("image") or atd_parsed.get("albumArtUrl")
                # duration may be in seconds or ms, try to normalize to seconds
                dur = atd_parsed.get("duration")
                if isinstance(dur, (int, float)):
                    media_duration = int(dur / 1000) if dur > 3600 * 10 else int(dur)
            except Exception:
                pass

        # 2) Capability specific fields
        if media_title is None:
            media_title = (
                SoundbarApi.extractor(data, "main.mediaTitle.value")
                or SoundbarApi.extractor(data, "main.title.value")
                or entity._media_title
            )
        if media_artist is None:
            media_artist = (
                SoundbarApi.extractor(data, "main.mediaArtist.value")
                or SoundbarApi.extractor(data, "main.artist.value")
            )
        if media_album is None:
            media_album = (
                SoundbarApi.extractor(data, "main.mediaAlbumName.value")
                or SoundbarApi.extractor(data, "main.album.value")
            )
        if media_image_url is None:
            media_image_url = (
                SoundbarApi.extractor(data, "main.albumArtUrl.value")
                or SoundbarApi.extractor(data, "main.imageURL.value")
            )

        # 3) Playback position/duration
        pp = SoundbarApi.extractor(data, "main.playbackPosition.value")
        try:
            if pp is not None:
                media_position = int(pp)
        except Exception:
            pass
        if media_duration is None:
            md = SoundbarApi.extractor(data, "main.mediaDuration.value")
            try:
                if md is not None:
                    media_duration = int(md)
            except Exception:
                pass

        # Assign only during active playback or when metadata available
        if entity._state in [STATE_PLAYING, STATE_PAUSED] or any([media_title, media_artist, media_album, media_image_url]):
            entity._media_title = media_title
            entity._media_artist = media_artist
            entity._media_album = media_album
            entity._media_image_url = media_image_url
            entity._media_duration = media_duration
            entity._media_position = media_position
        else:
            entity._media_artist = None
            entity._media_album = None
            entity._media_image_url = None
            entity._media_duration = None
            entity._media_position = None

    @staticmethod
    def send_command(entity, argument, cmdtype):
        API_KEY = entity._api_key
        REQUEST_HEADERS = {"Authorization": "Bearer " + API_KEY}
        DEVICE_ID = entity._device_id
        API_DEVICES = API_BASEURL + "/devices/"
        API_DEVICE = API_DEVICES + DEVICE_ID
        API_COMMAND = API_DEVICE + "/commands"

        try:
            if cmdtype == "setvolume":  # sets volume
                API_COMMAND_DATA = "{'commands':[{'component': 'main','capability': 'audioVolume','command': 'setVolume','arguments': "
                volume = int(argument * entity._max_volume)
                API_COMMAND_ARG = "[{}]}}]}}".format(volume)
                API_FULL = API_COMMAND_DATA + API_COMMAND_ARG
                requests.post(API_COMMAND, data=API_FULL, headers=REQUEST_HEADERS, timeout=10)
            elif cmdtype == "stepvolume":  # steps volume up or down
                if argument == "up":
                    API_COMMAND_DATA = "{'commands':[{'component': 'main','capability': 'audioVolume','command': 'volumeUp'}]}"
                    requests.post(API_COMMAND, data=API_COMMAND_DATA, headers=REQUEST_HEADERS, timeout=10)
                else:
                    API_COMMAND_DATA = "{'commands':[{'component': 'main','capability': 'audioVolume','command': 'volumeDown'}]}"
                    requests.post(API_COMMAND, data=API_COMMAND_DATA, headers=REQUEST_HEADERS, timeout=10)
            elif cmdtype == "audiomute":  # mutes audio
                if entity._muted == False:
                    requests.post(API_COMMAND, data=COMMAND_MUTE, headers=REQUEST_HEADERS, timeout=10)
                else:
                    requests.post(API_COMMAND, data=COMMAND_UNMUTE, headers=REQUEST_HEADERS, timeout=10)
            elif cmdtype == "switch_off":  # turns off
                requests.post(API_COMMAND, data=COMMAND_POWER_OFF, headers=REQUEST_HEADERS, timeout=10)
            elif cmdtype == "switch_on":  # turns on
                requests.post(API_COMMAND, data=COMMAND_POWER_ON, headers=REQUEST_HEADERS, timeout=10)
            elif cmdtype == "play":  # play
                requests.post(API_COMMAND, data=COMMAND_PLAY, headers=REQUEST_HEADERS, timeout=10)
            elif cmdtype == "pause":  # pause
                requests.post(API_COMMAND, data=COMMAND_PAUSE, headers=REQUEST_HEADERS, timeout=10)
            elif cmdtype == "selectsource":  # changes source
                #This is tested and working with Samsung Soundbar Q910A
                # sbMode is the value we need, and can be found at
                # https://my.smartthings.com/advanced/devices/device-id
                # under attributes, as 
                # main samsungvd.soundFrom mode 20
                # for me, should probably make a check for device type and match found values
                source_map = {
                    "HDMI1": {"sbMode": 3, "connectionType": "HDMI 1"},
                    "HDMI2": {"sbMode": 20, "connectionType": "HDMI 2"},
                    "digital": {"sbMode": 10, "connectionType": "D-IN"},
                    "wifi": {"sbMode": 25, "connectionType": "WIFI"},
                }
                if argument not in source_map:
                    logger.warning(f"Unknown source: {argument}")
                    raise ValueError(f"Unknown source: {argument}")
                headers_json = {**REQUEST_HEADERS, "Content-Type": "application/json"}
                execute_payload = {
                    "commands": [
                        {
                            "component": "main",
                            "capability": "execute",
                            "command": "execute",
                            "arguments": [
                                "/sec/networkaudio/soundFrom",
                                {
                                    "x.com.samsung.networkaudio.soundFrom": {
                                        "sbMode": source_map[argument]["sbMode"] 
                                    }
                                },
                            ],
                        }
                    ]
                }
                resp = requests.post(
                    API_COMMAND, json=execute_payload, headers=headers_json, timeout=10
                )
            elif cmdtype == "selectsoundmode":
                # Try execute path first
                headers_json = {**REQUEST_HEADERS, "Content-Type": "application/json"}
                execute_payload = {
                    "commands": [
                        {
                            "component": "main",
                            "capability": "execute",
                            "command": "execute",
                            "arguments": [
                                "/sec/networkaudio/soundmode",
                                {"x.com.samsung.networkaudio.soundmode": f"{argument}"},
                            ],
                        }
                    ]
                }
                resp = requests.post(
                    API_COMMAND, json=execute_payload, headers=headers_json, timeout=10
                )
                # Fallback to custom.soundmode if execute not supported
                if not getattr(resp, "ok", False):
                    soundmode_payload = {
                        "commands": [
                            {
                                "component": "main",
                                "capability": "custom.soundmode",
                                "command": "setSoundMode",
                                "arguments": [f"{argument}"],
                            }
                        ]
                    }
                    requests.post(
                        API_COMMAND, json=soundmode_payload, headers=headers_json, timeout=10
                    )
        except requests.RequestException as ex:
            logging.getLogger(__name__).warning("SoundbarApi send_command network error: %s", ex)
        entity.schedule_update_ha_state()

    @staticmethod
    def soundmode_update(entity):
        API_KEY = entity._api_key
        REQUEST_HEADERS = {"Authorization": "Bearer " + API_KEY}
        DEVICE_ID = entity._device_id
        API_DEVICE = API_DEVICES + DEVICE_ID
        API_DEVICE_STATUS = API_DEVICE + "/states"
        API_COMMAND = API_DEVICE + "/commands"

        try:
            requests.post(API_COMMAND, data=COMMAND_REFRESH, headers=REQUEST_HEADERS, timeout=10)
            resp = requests.get(API_DEVICE_STATUS, headers=REQUEST_HEADERS, timeout=10)
            if resp.status_code != 200:
                entity._sound_mode = None
                entity._sound_mode_list = DEFAULT_SOUND_MODES
                return
            data = resp.json()
        except requests.RequestException as ex:
            logging.getLogger(__name__).warning("SoundbarApi soundmode_update network error: %s", ex)
            entity._sound_mode = None
            entity._sound_mode_list = DEFAULT_SOUND_MODES
            return
        except ValueError as ex:
            logging.getLogger(__name__).warning("SoundbarApi soundmode_update invalid JSON: %s", ex)
            entity._sound_mode = None
            entity._sound_mode_list = DEFAULT_SOUND_MODES
            return

        # Try to locate sound mode from execute payload
        current_mode = None
        payload = SoundbarApi.extractor(data, "main.execute.data.value.payload")
        if isinstance(payload, dict):
            for key, value in payload.items():
                try:
                    if isinstance(key, str) and "networkaudio.soundmode" in key:
                        if isinstance(value, str):
                            current_mode = value
                        break
                except Exception:
                    continue

        # Fallback: try common paths used by some models
        if current_mode is None:
            current_mode = (
                SoundbarApi.extractor(data, "main.soundMode.value")
                or SoundbarApi.extractor(data, "main.mediaSoundMode.value")
            )

        # Try capability status for custom.soundmode (for some TVs)
        if current_mode is None:
            try:
                headers_json = {"Authorization": "Bearer " + entity._api_key}
                url = f"{API_DEVICES}{entity._device_id}/components/main/capabilities/custom.soundmode/status"
                r = requests.get(url, headers=headers_json, timeout=10)
                if r.ok:
                    js = r.json()
                    v = js.get("soundMode", {}).get("value")
                    if isinstance(v, str):
                        current_mode = v
            except Exception:
                pass

        # If still unknown, capture numeric mode if present for diagnostics
        mode_numeric = SoundbarApi.extractor(data, "main.mode.value")
        entity._sound_mode_raw = str(mode_numeric) if mode_numeric is not None else None

        # Build options list
        options = list(DEFAULT_SOUND_MODES)
        if isinstance(current_mode, str) and current_mode not in options:
            options.append(current_mode)

        # Preserve last known selection if API does not expose current mode
        if current_mode is None:
            current_mode = getattr(entity, "_sound_mode", None)
        entity._sound_mode = current_mode
        entity._sound_mode_list = options

    @staticmethod
    def extractor(json, path):
        def extractor_arr(json_obj, path_array):
            if path_array[0] not in json_obj:
                return None
            if len(path_array) > 1:
                return extractor_arr(json_obj[path_array[0]], path_array[1:])
            return json_obj[path_array[0]]
        try:
            return extractor_arr(json, path.split("."))
        except:
            return None

"""Runtime bridge between Diematic modbus and MQTT topics."""

from __future__ import annotations

import datetime as dt
import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from .const import (
    CONF_DISCOVERY_ENABLED,
    CONF_DISCOVERY_PREFIX,
    CONF_ENABLE_CIRCUIT_A,
    CONF_ENABLE_CIRCUIT_B,
    CONF_INTERFACE_ADDRESS,
    CONF_MODBUS_HOST,
    CONF_MODBUS_PORT,
    CONF_MQTT_CLIENT_ID,
    CONF_MQTT_HOST,
    CONF_MQTT_PASSWORD,
    CONF_MQTT_PORT,
    CONF_MQTT_TOPIC_PREFIX,
    CONF_MQTT_USERNAME,
    CONF_PERIOD,
    CONF_REGULATOR_ADDRESS,
    CONF_REGULATOR_TYPE,
    CONF_TIME_SYNC,
    CONF_TIMEZONE,
    OFFLINE,
    ONLINE,
)
from .vendor import Diematic3Panel, Diematic4Panel, DiematicDeltaPanel, Hassio

_LOGGER = logging.getLogger(__name__)


@dataclass
class MessageEntry:
    value: str
    update: bool = True


class MessageBuffer:
    def __init__(self, client: mqtt.Client, topic_prefix: str) -> None:
        self._client = client
        self._topic_prefix = topic_prefix
        self._buffer: dict[str, MessageEntry] = {}

    def clear(self) -> None:
        self._buffer = {}

    def update(self, topic: str, value: str) -> None:
        current = self._buffer.get(topic)
        if current is None or current.value != value:
            self._buffer[topic] = MessageEntry(value=value, update=True)

    def send(self) -> None:
        if not getattr(self._client, "brokerConnected", False):
            return
        for topic, entry in self._buffer.items():
            if not entry.update:
                continue
            full_topic = self._topic_prefix if topic == "" else f"{self._topic_prefix}/{topic}"
            self._client.publish(full_topic, entry.value, 1, True)
            entry.update = False


class DiematicMqttBridge:
    def __init__(self, config: dict, on_stop: Callable[[], None] | None = None) -> None:
        self._config = config
        self._on_stop = on_stop
        self._run = False
        self._watchdog: threading.Thread | None = None

        self._topic_prefix = f"{config[CONF_MQTT_TOPIC_PREFIX]}/{config[CONF_MQTT_CLIENT_ID]}"
        self._discovery_enabled = config[CONF_DISCOVERY_ENABLED]
        self._discovery_prefix = config[CONF_DISCOVERY_PREFIX]

        self._client = self._create_mqtt_client()
        self._buffer = MessageBuffer(self._client, self._topic_prefix)
        self._hassio = Hassio.Hassio(
            self._client,
            self._topic_prefix,
            config[CONF_MQTT_CLIENT_ID],
            self._discovery_prefix,
        )
        self._hassio.availabilityInfo("status", ONLINE, OFFLINE)
        self._hassio.setDevice("De Dietrich", config[CONF_REGULATOR_TYPE], config[CONF_MQTT_CLIENT_ID])

        self._panel = self._create_panel()
        self._panel.refreshPeriod = max(config[CONF_PERIOD], 10)
        self._panel.forceCircuitA = config[CONF_ENABLE_CIRCUIT_A]
        self._panel.forceCircuitB = config[CONF_ENABLE_CIRCUIT_B]

        self._panel.updateCallback = self._diematic_publish

    def _create_panel(self):
        panel_cls = {
            "Diematic3": Diematic3Panel.Diematic3Panel,
            "Diematic4": Diematic4Panel.Diematic4Panel,
            "DiematicDelta": DiematicDeltaPanel.DiematicDeltaPanel,
        }[self._config[CONF_REGULATOR_TYPE]]
        return panel_cls(
            self._config[CONF_MODBUS_HOST],
            int(self._config[CONF_MODBUS_PORT]),
            int(self._config[CONF_REGULATOR_ADDRESS]),
            int(self._config[CONF_INTERFACE_ADDRESS]),
            self._config[CONF_TIMEZONE],
            self._config[CONF_TIME_SYNC],
        )

    def _create_mqtt_client(self) -> mqtt.Client:
        if hasattr(mqtt, "CallbackAPIVersion"):
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        else:
            client = mqtt.Client()
        if self._config.get(CONF_MQTT_USERNAME):
            client.username_pw_set(self._config[CONF_MQTT_USERNAME], self._config.get(CONF_MQTT_PASSWORD))
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.will_set(f"{self._topic_prefix}/status", OFFLINE, 1, True)
        client.message_callback_add(f"{self._topic_prefix}/+/+/set", self._param_set)
        client.message_callback_add(f"{self._topic_prefix}/date/set", self._param_set)
        if self._discovery_enabled:
            client.message_callback_add(f"{self._discovery_prefix}/status", self._ha_send_discovery_messages)
        client.brokerConnected = False
        return client

    def start(self) -> None:
        self._run = True
        self._client.connect_async(self._config[CONF_MQTT_HOST], int(self._config[CONF_MQTT_PORT]))
        self._client.loop_start()
        self._panel.loop_start()
        self._watchdog = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog.start()
        _LOGGER.info("Diematic MQTT bridge started")

    def stop(self) -> None:
        self._run = False
        self._panel.loop_stop()
        self._client.loop_stop()
        _LOGGER.info("Diematic MQTT bridge stopped")

    def _watchdog_loop(self) -> None:
        while self._run:
            time.sleep(5)
            if threading.active_count() < 3:
                _LOGGER.error("A worker thread unexpectedly stopped")
                self.stop()
                if self._on_stop:
                    self._on_stop()
                break

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        del userdata, flags, reason_code, properties
        client.brokerConnected = True
        client.subscribe(f"{self._topic_prefix}/+/+/set", 2)
        client.subscribe(f"{self._topic_prefix}/date/set", 2)
        if self._discovery_enabled:
            client.subscribe(f"{self._discovery_prefix}/status", 2)
        self._buffer.clear()
        self._buffer.update("status", OFFLINE)
        self._buffer.send()

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        del client, userdata, flags, reason_code, properties

    def _param_set(self, client, userdata, message):
        del client, userdata
        topic = message.topic
        if topic.endswith("Temp/set"):
            self._temp_set(message)
        elif topic.endswith("mode/set"):
            self._mode_set(message)
        elif topic.endswith("date/set"):
            self._date_set(message)

    def _mode_set(self, message):
        table = {
            "/hotWater/mode/set": "hotWaterMode",
            "/zoneA/mode/set": "zoneAMode",
            "/zoneB/mode/set": "zoneBMode",
        }
        short_topic = message.topic[len(self._topic_prefix) :]
        if short_topic in table:
            setattr(self._panel, table[short_topic], message.payload.decode())

    def _temp_set(self, message):
        table = {
            "/hotWater/dayTemp/set": "hotWaterDayTargetTemp",
            "/hotWater/nightTemp/set": "hotWaterNightTargetTemp",
            "/zoneA/dayTemp/set": "zoneADayTargetTemp",
            "/zoneA/nightTemp/set": "zoneANightTargetTemp",
            "/zoneA/antiiceTemp/set": "zoneAAntiiceTargetTemp",
            "/zoneB/dayTemp/set": "zoneBDayTargetTemp",
            "/zoneB/nightTemp/set": "zoneBNightTargetTemp",
            "/zoneB/antiiceTemp/set": "zoneBAntiiceTargetTemp",
        }
        short_topic = message.topic[len(self._topic_prefix) :]
        if short_topic in table:
            setattr(self._panel, table[short_topic], float(message.payload))

    def _date_set(self, message):
        if message.topic.endswith("/date/set") and message.payload.decode() == "Now":
            setattr(self._panel, "datetime", dt.datetime.now().astimezone())

    def _diematic_publish(self, panel):
        def float_value(parameter):
            return f"{parameter:.1f}" if parameter is not None else ""

        def int_value(parameter):
            return f"{parameter:d}" if parameter is not None else ""

        self._buffer.update("status", ONLINE if panel.availability else OFFLINE)
        self._buffer.update("date", panel.datetime.isoformat() if panel.datetime is not None else "")
        self._buffer.update("lastTimeSync", panel.lastTimeSync.isoformat() if panel.lastTimeSync is not None else "")
        self._buffer.update("type", int_value(panel.type))
        self._buffer.update("ctrl", int_value(panel.release))
        self._buffer.update("ext/temp", float_value(panel.extTemp))
        self._buffer.update("temp", float_value(panel.temp))
        self._buffer.update("targetTemp", float_value(panel.targetTemp))
        self._buffer.update("returnTemp", float_value(panel.returnTemp))
        self._buffer.update("waterPressure", float_value(panel.waterPressure))
        self._buffer.update("power", int_value(panel.burnerPower))
        self._buffer.update("smokeTemp", float_value(panel.smokeTemp))
        self._buffer.update("ionizationCurrent", float_value(panel.ionizationCurrent))
        self._buffer.update("fanSpeed", int_value(panel.fanSpeed))
        self._buffer.update("burnerStatus", int_value(panel.burnerStatus))
        self._buffer.update("pumpPower", int_value(panel.pumpPower))
        self._buffer.update("alarm", json.dumps(panel.alarm) if panel.alarm is not None else "")
        self._buffer.update("nbImpuls", int_value(panel.nbImpuls))
        self._buffer.update("fctBrul", int_value(panel.fctBrul))
        self._buffer.update("hotWater/pump", int_value(panel.hotWaterPump))
        self._buffer.update("hotWater/temp", float_value(panel.hotWaterTemp))
        self._buffer.update("hotWater/mode", panel.hotWaterMode if panel.hotWaterMode is not None else "")
        self._buffer.update("hotWater/dayTemp", float_value(panel.hotWaterDayTargetTemp))
        self._buffer.update("hotWater/nightTemp", float_value(panel.hotWaterNightTargetTemp))
        self._buffer.update("zoneA/temp", float_value(panel.zoneATemp))
        self._buffer.update("zoneA/mode", panel.zoneAMode if panel.zoneAMode is not None else "")
        self._buffer.update("zoneA/pump", int_value(panel.zoneAPump))
        self._buffer.update("zoneA/dayTemp", float_value(panel.zoneADayTargetTemp))
        self._buffer.update("zoneA/nightTemp", float_value(panel.zoneANightTargetTemp))
        self._buffer.update("zoneA/antiiceTemp", float_value(panel.zoneAAntiiceTargetTemp))
        self._buffer.update("zoneB/temp", float_value(panel.zoneBTemp))
        self._buffer.update("zoneB/mode", panel.zoneBMode if panel.zoneBMode is not None else "")
        self._buffer.update("zoneB/pump", int_value(panel.zoneBPump))
        self._buffer.update("zoneB/dayTemp", float_value(panel.zoneBDayTargetTemp))
        self._buffer.update("zoneB/nightTemp", float_value(panel.zoneBNightTargetTemp))
        self._buffer.update("zoneB/antiiceTemp", float_value(panel.zoneBAntiiceTargetTemp))
        self._buffer.send()

    def _ha_send_discovery_messages(self, client, userdata, message):
        del client, userdata
        if message.payload.decode() != "online":
            return
        self._hassio.addSensor("heater_datetime", "Horloge Chaudière", None, "date", "{{ as_timestamp(value) |timestamp_custom ('%d/%m/%Y %H:%M') }}", None)
        self._hassio.addSwitch("heater_datetime_set", "Synchro Horloge", "unknown", "date/set", "--", "Now")
        self._hassio.addSensor("type", "Type", None, "type", None, None)
        self._hassio.addSensor("ctrl", "Controleur", None, "ctrl", None, None)
        self._hassio.addSensor("ext_temp", "Température Extérieure", "temperature", "ext/temp", None, "°C")
        self._hassio.addSensor("boiler_temp", "Température Chaudière", "temperature", "temp", None, "°C")
        self._hassio.addSensor("zone_A_temp", "Température Zone A", "temperature", "zoneA/temp", None, "°C")
        self._hassio.addSensor("zone_B_temp", "Température Zone B", "temperature", "zoneB/temp", None, "°C")

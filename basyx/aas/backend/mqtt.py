# Copyright (c) 2023 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import paho.mqtt.client as mqtt
import json
import threading
from typing import List, Dict, Any
from . import backends
from basyx.aas import model
from basyx.aas.model.protocols import Protocol


class MQTTBackend(backends.ValueBackend):
    @classmethod
    def _parse_source(cls, source: Any) -> Dict[str, Any]:
        """
        Parses the source dictionary to extract MQTT connection details.
        """
        if not isinstance(source.get('protocol'), Protocol) or source['protocol'] != Protocol.MQTT:
            raise ValueError("Invalid protocol. Must be MQTT protocol.")

        required_keys = ['base', 'topic', 'controlPacket']
        if not all(key in source for key in required_keys):
            raise ValueError(f"Invalid source format. {', '.join(required_keys)} must be provided.")

        parsed = {
            'broker': source['base'].split('://')[1],
            'topic': source['topic'],
            'control_packet': source['controlPacket'],
            'content_type': source.get('contentType', 'application/json'),
            'security': source.get('security', {})
        }
        return parsed

    @classmethod
    def _setup_mqtt_client(cls, mqtt_info: Dict[str, Any]) -> mqtt.Client:
        client = mqtt.Client()

        # Setup security if provided
        security = mqtt_info['security']
        if 'basic_sc' in security:
            client.username_pw_set(mqtt_info.get('username'), mqtt_info.get('password'))
        elif 'bearer_sc' in security:
            # For MQTT, we might use the token as a password
            client.username_pw_set('token', mqtt_info.get('token'))

        return client

    @classmethod
    def update_value(cls,
                     updated_object: model.Referable,
                     source: Any) -> None:
        """
        Updates an object by subscribing to the MQTT topic and receiving the latest state.
        """
        mqtt_info = cls._parse_source(source)

        if mqtt_info['control_packet'].lower() != 'subscribe':
            print(f"Warning: MQTT control packet '{mqtt_info['control_packet']}' may not be appropriate for updating "
                  f"data. SUBSCRIBE is recommended.")

        def on_message(client, userdata, message):
            try:
                if mqtt_info['content_type'] == 'application/json':
                    payload = json.loads(message.payload.decode())
                    updated_object.value = payload
                else:
                    # Handle non-JSON content types
                    payload = message.payload.decode().strip()
                    if payload.isdigit():
                        updated_object.value = int(payload)
                    elif payload.replace('.', '', 1).isdigit():
                        updated_object.value = float(payload)
                    else:
                        updated_object.value = payload
                print(f"Updated {updated_object.id_short} value to: {updated_object.value}")
            except Exception as e:
                print(f"Error processing message: {e}")

        def mqtt_listener():
            client = cls._setup_mqtt_client(mqtt_info)
            client.on_message = on_message

            try:
                host, port = mqtt_info['broker'].split(':')
                client.connect(host, int(port))
                client.subscribe(mqtt_info['topic'])
                client.loop_forever()
            except Exception as e:
                print(f"Failed to connect to MQTT broker: {e}")

        # Start MQTT listener in a separate thread
        thread = threading.Thread(target=mqtt_listener, daemon=True)
        thread.start()
        print(f"Started MQTT listener for {updated_object.id_short} on topic {mqtt_info['topic']}")

    @classmethod
    def commit_value(cls,
                     committed_object: model.Referable,
                     source: Any) -> None:
        """
        Commits an object by publishing to the MQTT topic.
        """
        mqtt_info = cls._parse_source(source)

        if mqtt_info['control_packet'].lower() != 'publish':
            print(f"Warning: MQTT control packet '{mqtt_info['control_packet']}' "
                  f"may not be appropriate for committing data. PUBLISH is recommended.")

        client = cls._setup_mqtt_client(mqtt_info)

        try:
            host, port = mqtt_info['broker'].split(':')
            client.connect(host, int(port))

            if mqtt_info['content_type'] == 'application/json':
                payload = json.dumps(committed_object.value)
            else:
                payload = str(committed_object.value)

            result = client.publish(mqtt_info['topic'], payload)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Successfully published update for {committed_object.id_short}")
            else:
                print(f"Failed to publish update for {committed_object.id_short}: {mqtt.error_string(result.rc)}")

            client.disconnect()
        except Exception as e:
            print(f"Failed to commit the object to the MQTT broker: {e}")


backends.register_backend(Protocol.MQTT, MQTTBackend)

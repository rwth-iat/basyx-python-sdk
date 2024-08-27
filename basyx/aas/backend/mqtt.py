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


class MQTTBackend(backends.Backend):
    @classmethod
    def _parse_source(cls, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the source dictionary to extract MQTT connection details.
        """
        required_keys = ['base', 'topic', 'controlPacket']
        if not all(key in source for key in required_keys):
            raise ValueError(f"Invalid source format. {', '.join(required_keys)} must be provided.")
        return {
            'broker': source['base'].split('://')[1],
            'topic': source['topic'],
            'control_packet': source['controlPacket'],
            'content_type': source.get('contentType', 'application/json')
        }

    @classmethod
    def update_object(cls,
                      updated_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      source: Dict[str, Any]) -> None:
        """
        Updates an object by subscribing to the MQTT topic and receiving the latest state.
        """
        mqtt_info = cls._parse_source(source)
        
        if mqtt_info['control_packet'].lower() != 'subscribe':
            print(f"Warning: MQTT control packet '{mqtt_info['control_packet']}' may not be appropriate for updating data. SUBSCRIBE is recommended.")

        def on_message(client, userdata, message):
            try:
                updated_object.value = message.payload.decode()
                print(f"Updated {updated_object.id_short} value to: {updated_object.value}")
            except Exception as e:
                print(f"Failed to update object value: {e}")

        def mqtt_listener():
            client = mqtt.Client()
            client.on_message = on_message

            try:
                client.connect(mqtt_info['broker'].split(':')[0], int(mqtt_info['broker'].split(':')[1]))
                client.subscribe(mqtt_info['topic'])
                client.loop_forever()
            except Exception as e:
                print(f"Failed to connect to MQTT broker: {e}")

        # Start MQTT listener in a separate thread
        thread = threading.Thread(target=mqtt_listener, daemon=True)
        thread.start()
        print(f"Started MQTT listener for {updated_object.id_short} on topic {mqtt_info['topic']}")

    @classmethod
    def commit_object(cls,
                      committed_object: model.Referable,
                      store_object: model.Referable,
                      relative_path: List[str],
                      source: Dict[str, Any]) -> None:
        """
        Commits an object by publishing to the MQTT topic.
        """
        mqtt_info = cls._parse_source(source)
        
        if mqtt_info['control_packet'].lower() != 'publish':
            print(f"Warning: MQTT control packet '{mqtt_info['control_packet']}' may not be appropriate for committing data. PUBLISH is recommended.")

        client = mqtt.Client()

        try:
            host, port = mqtt_info['broker'].split(':')
            client.connect(host, int(port))
            
            payload = json.dumps(committed_object.value)
            result = client.publish(mqtt_info['topic'], payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Successfully published update for {committed_object.id_short}")
            else:
                print(f"Failed to publish update for {committed_object.id_short}: {mqtt.error_string(result.rc)}")
            
            client.disconnect()
        except Exception as e:
            print(f"Failed to commit the object to the MQTT broker: {e}")

backends.register_backend(Protocol.MQTT, MQTTBackend)
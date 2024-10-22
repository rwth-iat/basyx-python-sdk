#!/usr/bin/env python3
# This work is licensed under a Creative Commons CCZero 1.0 Universal License.
# See http://creativecommons.org/publicdomain/zero/1.0/ for more information.
"""
Tutorial for data integration using AID (Asset Interfaces Description) and
AIMC (Asset Interfaces Mapping Configuration) with BaSyx Python SDK.

This tutorial demonstrates how to use AID and AIMC for data integration.
Customized Protocols can be used to perform data integration with different data sources too.
See "tutorial_backend_couchdb" for more information.

Step-by-Step Guide:
Step 1: Add relevant Submodels to an ObjectStore to retrieve information of data sources
Step 2: Update and commit using HTTP protocol
Step 3: Update and commit using MQTT protocol
Step 4: Remove the AIMC Submodel and related information of data sources
"""

# Import required BaSyx Python SDK modules
from basyx.aas.model import DictObjectStore, UniqueIdShortNamespace, SubmodelElementCollection, Property
import basyx.aas.adapter.json
import basyx.aas.adapter.xml
from basyx.aas.model.protocols import Protocol
import basyx.aas.backend.http
import basyx.aas.backend.mqtt


####################################################
# Step 1: Add relevant Submodels to an ObjectStore #
####################################################

# For this tutorial, we assume the AAS and Submodels are already created.
# The XML file is used only to provide the necessary objects for the tutorial.
xml_file_data = basyx.aas.adapter.xml.read_aas_xml_file('AID_AIMC_Example.xml')

# Extract the required Submodels from the XML data
sm_operation = xml_file_data.get_identifiable('https://example.com/ids/sm/OperationalData')
sm_AID = xml_file_data.get_identifiable('https://example.com/ids/sm/AssetInterfacesDescription')
sm_AIMC = xml_file_data.get_identifiable('https://example.com/ids/sm/AssetInterfacesMappingConfiguration')

# Create a DictObjectStore to manage the AAS and Submodels
# Note: The xml_file_data is also a DictObjectStore object and can be used directly.
# To demonstrate the entire process, we create a new DictObjectStore.
obj_store: DictObjectStore = DictObjectStore()

# Add Submodels to the ObjectStore
obj_store.add(sm_AID)
obj_store.add(sm_operation)

# Adding an AIMC Submodel creates a non-public mapping table for data source management.
# The DictObjectStore will detect if an added Sumodel is an AIMC Submodel with certain naming rules.
# The created mapping table obj_store._mapping contains the mapping information for data sources
obj_store.add(sm_AIMC)

# If you only want to use the AID Submodel to manage the configuration, you can add this into the mapping table manually
# In the example AAS, the 'current' Property is not part of the AIMC Submodel

assert isinstance(sm_AID, UniqueIdShortNamespace)
interface_http = sm_AID.get_referable('InterfaceHTTP')
assert isinstance(interface_http, UniqueIdShortNamespace)
interface_metadata = interface_http.get_referable('InterfaceMetadata')
assert isinstance(interface_metadata, UniqueIdShortNamespace)
aid_properties = interface_metadata.get_referable('Properties')
assert isinstance(aid_properties, UniqueIdShortNamespace)
aid_http_current = aid_properties.get_referable('current')

# Extract the source information for the property current from the AID Submodel
assert isinstance(aid_http_current, SubmodelElementCollection)
integration_source = obj_store.extract_aid_parameters(aid_http_current)


assert isinstance(sm_operation, UniqueIdShortNamespace)
http_smc = sm_operation.get_referable('HTTP_Data')
assert isinstance(http_smc, UniqueIdShortNamespace)
http_current = http_smc.get_referable('current')
# Add the source information to the mapping table
obj_store.add_source(http_current, Protocol.HTTP, integration_source)


#################################################
# Step 2: Update and commit using HTTP protocol #
#################################################

# Note: The HTTPBackend class is not standardized.
# Users should adapt it based on their specific server setup and requirements.

http_voltage = http_smc.get_referable('voltage')
http_status = http_smc.get_referable('status')

# Update 'voltage' data and 'current' data
obj_store.update_referable_value(http_voltage, Protocol.HTTP)

# Update 'current' data as well as 'voltage' data.
# As described above, the 'current' Property is not part of the AIMC Submodel.
# If no protocol type is provided, the ObjectStore will use the first available protocol (here HTTP) for the operation
obj_store.update_referable_value(http_current)

# Attempt to update 'status' (won't occur as it's set for commit operation)
obj_store.update_referable_value(http_status, Protocol.HTTP)

# Commit 'status' data
assert isinstance(http_status, Property)
http_status.value = 'commit_http'
obj_store.commit_referable_value(http_status, Protocol.HTTP)

# Attempt to commit 'voltage' (value in server will not change, as it's set only for update operation)
assert isinstance(http_voltage, Property)
http_voltage.value = '3.5'
obj_store.commit_referable_value(http_voltage, Protocol.HTTP)

#################################################
# Step 3: Update and commit using MQTT protocol #
#################################################

# Note: The MQTTBackend class is not standardized.
# Users should adapt it based on their specific server setup and requirements.

mqtt_smc = sm_operation.get_referable('MQTT_Data')
assert isinstance(mqtt_smc, UniqueIdShortNamespace)
mqtt_voltage = mqtt_smc.get_referable('voltage')
mqtt_status = mqtt_smc.get_referable('status')

# Continuously listening to the MQTT topic after subscribing to it
obj_store.subscribe_referable_value(mqtt_voltage, Protocol.MQTT)

# Publish 'status' data to the MQTT broker (one-time action for demonstration)
assert isinstance(mqtt_status, Property)
mqtt_status.value = 'commit_mqtt'
obj_store.publish_referable_value(mqtt_status, Protocol.MQTT)

#########################################################
# Step 4: Remove AIMC Submodel and related data sources #
#########################################################

# Removing the AIMC Submodel from the ObjectStore will remove related data sources
obj_store.discard(sm_AIMC)

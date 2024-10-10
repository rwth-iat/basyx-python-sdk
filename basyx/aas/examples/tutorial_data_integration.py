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
from basyx.aas import model
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
obj_store = model.DictObjectStore()

# Add Submodels to the ObjectStore
obj_store.add(sm_AID)
obj_store.add(sm_operation)

# Adding an AIMC Submodel creates a non-public mapping table for data source management.
# The DictObjectStore will detect if an added Sumodel is an AIMC Submodel with certain naming rules.
obj_store.add(sm_AIMC)

# For AIMC Submodels with custom naming rules, use the optional parameter
# obj_store.add(sm_AIMC, is_aimc=True)

# If you only want to use the AID Submodel to manage the configuration, you can add this into the mapping table manually
# In the example AAS, the 'current' Property is not part of the AIMC Submodel
aid_http_current = sm_AID.get_referable('InterfaceHTTP').get_referable('InterfaceMetadata').get_referable(
    'Properties').get_referable('current')
integration_source = obj_store.extract_aid_parameters(aid_http_current)
http_current = sm_operation.get_referable('HTTP_Data').get_referable('current')
obj_store.add_source(http_current, Protocol.HTTP, integration_source)

# The mapping table is only shown for demonstration purposes
mapping_table = obj_store._mapping

#################################################
# Step 2: Update and commit using HTTP protocol #
#################################################

# Note: The HTTPBackend class is not standardized.
# Users should adapt it based on their specific server setup and requirements.

http_voltage = sm_operation.get_referable('HTTP_Data').get_referable('voltage')
http_status = sm_operation.get_referable('HTTP_Data').get_referable('status')

# Update 'voltage' data and 'current' data
obj_store.update_referable_value(http_voltage, Protocol.HTTP)

# Update 'current' data as well as 'voltage' data.
# As described above, the 'current' Property is not part of the AIMC Submodel.
# If no protocol type is provided, the ObjectStore will use the first available protocol (here HTTP) for the operation
obj_store.update_referable_value(http_current)

# Attempt to update 'status' (won't occur as it's set for commit operation)
obj_store.update_referable_value(http_status, Protocol.HTTP)

# Commit 'status' data
http_status.value = 'commit_http'
obj_store.commit_referable_value(http_status, Protocol.HTTP)

# Attempt to commit 'voltage' (value in server will not change, as it's set only for update operation)
http_voltage.value = '3.5'
obj_store.commit_referable_value(http_voltage, Protocol.HTTP)

#################################################
# Step 3: Update and commit using MQTT protocol #
#################################################

# Note: The MQTTBackend class is not standardized.
# Users should adapt it based on their specific server setup and requirements.

mqtt_voltage = sm_operation.get_referable('MQTT_Data').get_referable('voltage')
mqtt_status = sm_operation.get_referable('MQTT_Data').get_referable('status')

# Continuously listening to the MQTT topic after subscribing to it
obj_store.subscribe_referable_value(mqtt_voltage, Protocol.MQTT)

# Publish 'status' data to the MQTT broker (one-time action for demonstration)
mqtt_status.value = 'commit_mqtt'
obj_store.publish_referable_value(mqtt_status, Protocol.MQTT)

#########################################################
# Step 4: Remove AIMC Submodel and related data sources #
#########################################################

# Removing the AIMC Submodel from the ObjectStore will remove related data sources
obj_store.discard(sm_AIMC)



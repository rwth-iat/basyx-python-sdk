#!/usr/bin/env python3
# This work is licensed under a Creative Commons CCZero 1.0 Universal License.
# See http://creativecommons.org/publicdomain/zero/1.0/ for more information.
"""
Module for storing Asset Administration Shells, Submodels and Assets in a CouchDB database server, using the
CouchDBObjectStore and CouchDB Backend.

It also shows the usage of the commit()/update() mechanism for synchronizing objects with an external data
source (CouchDB).
"""

from configparser import ConfigParser
from pathlib import Path

import basyx.aas.examples.data.new_example_aas
import basyx.aas.backend.couchdb


##########################################
# Step 1: Connecting to a CouchDB Server #
##########################################

# Connections to the CouchDB server are created by the CouchDB backend.
config = ConfigParser()
config.read([Path(__file__).parent.parent.parent.parent / 'test' / 'test_config.default.ini',
             Path(__file__).parent.parent.parent.parent / 'test' / 'test_config.ini'])

couchdb_url = config['couchdb']['url']
couchdb_database = config['couchdb']['database']
couchdb_user = config['couchdb']['user']
couchdb_password = config['couchdb']['password']

# Provide the login credentials to the CouchDB backend.
# These are used, whenever communication with this CouchDB server is required (either via the
# CouchDBObjectStore or via the update()/commit() backend.
basyx.aas.backend.couchdb.register_credentials(couchdb_url, couchdb_user, couchdb_password)

# Now, we create a CouchDBObjectStore as an interface for managing the objects in the CouchDB server.
couchdb_object_store = basyx.aas.backend.couchdb.CouchDBObjectStore(couchdb_url, couchdb_database)

#####################################################
# Step 2: Storing objects in the CouchDBObjectStore #
#####################################################

# Create some example identifiable objects
example_subModel_1 = basyx.aas.examples.data.new_example_aas.create_example_asset_identification_submodel()
example_subModel_2 = basyx.aas.examples.data.new_example_aas.create_example_bill_of_material_submodel()

# The objects are transferred to the CouchDB immediately. Additionally, the `source` attribute?? is set
# automatically, so update() and commit() will work automatically.
couchdb_object_store.add(example_subModel_1)
couchdb_object_store.add(example_subModel_2)

###############################################################################
# Step 3: Updating Objects from the CouchDB and Committing Changes to CouchDB #
###############################################################################

# Since the CouchDBObjectStore has set the `source` attribute of our SubModel objects, we can now use update() and
# commit() to synchronize changes to these objects with the database.
# The `source` indicates (via its URI scheme) that the CouchDB backend is used for the synchronization
# and references the correct CouchDB server url and database. For this to work, we must make sure
# to `import aas.backend.couchdb` at least once in this Python application, so the CouchDB backend is loaded.

# Fetch recent updates from the couchdb server
example_subModel_1.update()

# Make some changes to a Property within the subModel
prop = example_subModel_1.get_referable('ManufacturerName')
assert isinstance(prop, basyx.aas.model.Property)
prop.value = "RWTH Aachen"

# Commit these changes to the CouchDB server
# We can simply call commit() on the Property object. It will check the `source` attribute of the object itself as well
# as the source attribute of all ancestors in the object hierarchy (including the SubModel) and commit the changes to
# all of its external data sources.
prop.commit()

############
# Clean up #
############

# Let's delete the SubModels from the CouchDB to leave it in a clean state
couchdb_object_store.discard(example_subModel_1)
couchdb_object_store.discard(example_subModel_2)

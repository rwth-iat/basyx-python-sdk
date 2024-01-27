Missing constants:
- _SE

Used constants:
- ALLOWED_DATA_ELEMENT_CATEGORIES (location: https://github.com/aas-core-works/aas-core3.0-python/blob/d3a1f793732f6fa30db7674010cfd3f7bc65023d/aas_core3/constants.py#L11)


SubmodelElement:
- possesses class SubmodelElement (not abc)
- has a different constructor

Submodel:
- possesses class Submodel 
- New functions: 
    - over_submodel_elements_or_empty
    - descend_once
    - descend
    - accept
    - accept_with_context
    - transform
    - transform_with_context

DataElement:
- possesses class DataElement (not abc)
- Missing functions:
  - _set_category
- New functions:
  - category_or_default 

Property:
- possesses class Property 
- New constants:
  - value_type
  - value
  -  value_id
- Missing functions:
  - value (@property)
  - value (@value.setter)
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context 

MultiLanguageProperty:
- possesses class MultiLanguageProperty
- New constants:
  - value
  - value_id
- New functions:
  - over_value_or_empty 
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

Range:
- possesses class Range
- New constants:
  - value_type 
  - min
  - max
- Missing functions:
  - min (@property)
  - min (@min.setter)
  - max (@property)
  - max (@max.setter)
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

Blob:
- possesses class Blob
- New constants:
  - value
  - content_type
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

File: 
- possesses class File
- New constants:
  - value
  - content_type
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

ReferenceElement:
- possesses class ReferenceElement
- New constants:
  - value
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

SubmodelElementCollection:
- possesses class SubmodelElementCollection
- New constants:
  - value
- New functions:
  - over_value_or_empty
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

SubmodelElementList:
- possesses class SubmodelElementList
- New constants:
  - order_relevant
  - semantic_id_list_element
  - type_value_list_element
  - value_type_list_element
  - value
- Used functions:
  - _generate_id_short (location: https://github.com/aas-core-works/aas-core3.0-python/blob/d3a1f793732f6fa30db7674010cfd3f7bc65023d/aas_core3/verification.py#L2908)
  - _check_constraints (location: https://github.com/aas-core-works/aas-core3.0-python/blob/d3a1f793732f6fa30db7674010cfd3f7bc65023d/aas_core3/verification.py#L2844 (line 2844-2902))
-  Missing functions:
  - _unset_id_short
  - value (@property)
  - value (@value.setter)
  - type_value_list_element (@property)
  - order_relevant (@property)
  - semantic_id_list_element (@property)
  - value_type_list_element (@property)
- New functions:
  - over_value_or_empty
  - order_relevant_or_default
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

RelationshipElement:
- possesses class RelationshipElement
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

AnnotatedRelationshipElement:
- possesses class AnnotatedRelationshipElement
- New constants:
  - annotations
- New functions:
  - over_annotations_or_empty 
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

Operation:
- possesses class Operation
- New constants:
  - input_variables
  - output_variables
  - inoutput_variables 
- New functions:
  - over_input_variables_or_empty
  - over_output_variables_or_empty
  - over_inoutput_variables_or_empty   
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

Capability:
- possesses class Capability
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

Entity:
- possesses class Entity
- New constants:
  - statements
  - entity_type
  - global_asset_id
  - specific_asset_ids
- Used functions:
  - _validate_global_asset_id (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L5857)
  - _validate_aasd_014 (location: https://github.com/aas-core-works/aas-core3.0-python/blob/d3a1f793732f6fa30db7674010cfd3f7bc65023d/aas_core3/verification.py#L4438)
- Missing functions:
  - entity_type (@property)
  - entity_type (@entity_type.setter)
  - global_asset_id (@property)
  - global_asset_id (@global_asset_id.setter)
  - specific_asset_id (@property)
  - specific_asset_id (@specific_asset_id.setter)
  - _check_constraint_add_spec_asset_id
  - _check_constraint_set_spec_asset_id
  - _check_constraint_del_spec_asset_id
- New functions:
  - over_statements_or_empty
  - over_specific_asset_ids_or_empty 
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context

EventElement:
- possesses class EventElement (not abc)
- has a different constructor

BasicEventElement:
- possesses class BasicEventElement
- New constants:
  - observed
  - direction
  - state
  - message_topic
  - message_broker
  - last_update
  - min_interval
  - max_interval
- Missing functions:
  - direction (@property)
  - direction (@direction.setter)
  - last_update (@property)
  - last_update (@last_update.setter)
  - max_interval (@property)
  - max_interval (@max_interval.setter)
- New functions:
  - descend_once
  - descend
  - accept
  - accept_with_context
  - transform
  - transform_with_context
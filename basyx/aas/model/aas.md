AssetInformation:

  - Possesses Class AssetInformation.
  - New constants: 
    - asset_kind
    - global_asset_id
    - specific_asset_ids
    - asset_type
    - default_thumbnail.
  - New functions: 
    - over_specific_asset_ids_or_empty
    - descend_once
    - descend
    - accept
    - accept_with_context
    - transform
    - transform_with_context.
  - A different constructor.
  - Missing functions:
    - global_asset_id (@property) 
    - global_asset_id (@global_asset_id.setter)
    - specific_asset_id (@property)
    - specific_asset_id (@specific_asset_id.setter)
    - _check_constraint_set_spec_asset_id
    - _check_constraint_del_spec_asset_id
    - `__repr__`
  - Used functions:
    - def _validate_aasd_131 (@staticmethod) (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L2253)
    - _validate_global_asset_id (@staticmethod) (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L2268C49-L2268C64)
    

AssetAdministrationShell:


  - Possesses Class AssetAdministrationShell.
  - New constants: 
    - derived_from
    - asset_information
    - submodels.
  - New functions: 
    - over_submodels_or_empty
    - descend_once
    - descend
    - accept
    - accept_with_context
    - transform
    - transform_with_context.
  - A different constructor.
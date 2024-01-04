AssetInformation:

* Has:
* * Class AssetInformation.
* * New constants: asset_kind, global_asset_id, specific_asset_ids, asset_type, default_thumbnail.
* * New functions: over_specific_asset_ids_or_empty, descend_once, descend, accept, accept_with_context, transform, transform_with_context.
* * A different constructor.

* Doesn't have:
* * Any of our functions. 

AssetAdministrationShell:

* Has:
* * Class AssetAdministrationShell.
* * New constants: derived_from, asset_information, submodels.
* * New functions: over_submodels_or_empty, descend_once, descend, accept, accept_with_context, transform, transform_with_context.
* * A different constructor.
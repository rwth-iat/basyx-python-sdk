"""
Response filter for the access control layer: removes the resources a caller may not see from AAS API responses.

The filter makes no access decisions itself. It asks OPA (``response_filter`` in ``access_control/policy``) and applies
the answer. See ``README.md`` in this directory.
"""

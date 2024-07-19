"""
The package consists of the python implementation of the AssetAdministrationShell, as defined in the
'Details of the Asset Administration Shell' specification of Plattform Industrie 4.0.

The subpackage 'model' is an implementation of the meta-model of the AAS,
in 'adapter', you can find JSON and XML adapters to translate between BaSyx Python SDK objects and JSON/XML schemas;
and in 'util', some helpful functionality to actually use the AAS meta-model you created with 'model' is located.
"""

__version__ = "1.0.0"

from dateutil.relativedelta import relativedelta as Duration

# If you're using TYPE_CHECKING elsewhere, you might want to do this instead:
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dateutil.relativedelta import relativedelta as Duration
else:
    from dateutil.relativedelta import relativedelta as Duration

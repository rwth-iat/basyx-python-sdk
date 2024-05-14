"""
This package contains a python implementation of the meta-model of the AssetAdministrationShell.
The model is divided into 5 modules, splitting it in sensible parts. However, all classes (except for the
specialized Concept Descriptions) are imported into this top-level package, for simple imports like

.. code-block:: python

    from basyx.aas.model import AssetAdministrationShell, Submodel, Property
"""

from .aas import *
from .base import *
from .submodel import *
from .provider import *
from .concept import ConceptDescription
from . import datatypes

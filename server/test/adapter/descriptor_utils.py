from typing import Any

from app.model import DictDescriptorStore, SecurityAttributeObject, SecurityTypeEnum
from app.model.descriptor import AssetAdministrationShellDescriptor, SubmodelDescriptor
from app.model.endpoint import Endpoint, ProtocolInformation
from basyx.aas import model


def example_endpoint(interface: str = "AAS-3.0", href: str = "https://example.org/endpoint") -> Endpoint:
    return Endpoint(
        interface=interface,
        protocol_information=ProtocolInformation(
            href=href,
            endpoint_protocol="ExampleProtocol",
            endpoint_protocol_version=["1", "2"],
            subprotocol="ExampleSubprotocol",
            subprotocol_body="ExampleProtocolBody",
            subprotocol_body_encoding="ExampleEncoding",
            security_attributes=[SecurityAttributeObject(
                type_=SecurityTypeEnum.NONE,
                key="ExampleKey",
                value="ExampleValue"
            )]
        ))

def example_aas_descriptor(id_: str, **kwargs: Any) -> AssetAdministrationShellDescriptor:
    aas_descriptor_args = dict({
        "description": model.MultiLanguageTextType(
            {"en-US": "Example description", "de": "Beispiel Description"}
        ),
        "display_name": model.MultiLanguageNameType(
            {"en-US": "Exaple display name", "de": "Beispiel Anzeigename"}
        ),
        # TODO: Descriptor serialization fails with extensions, fix and enable test
        # "extension": [model.Extension(
        #     name="Example Descriptor Extension",
        #     value_type=model.datatypes.String,
        #     value="ExampleExtensionValue"
        # )],
        "administration": model.AdministrativeInformation(
            version="9", template_id="http://example.org/AdministrativeInformation"
        ),
        "asset_kind": model.AssetKind.INSTANCE,
        "asset_type": "http://example.org/TestAssetType/",
        "endpoints": [example_endpoint("AAS-3.0")],
        "global_asset_id": "http://example.org/TestAsset/",
        "id_short": "TestAsset",
        "specific_asset_id": [model.SpecificAssetId(
                    name="TestKey",
                    value="TestValue",
        )],
        "submodel_descriptors": []
    })
    aas_descriptor_args.update(kwargs)
    return AssetAdministrationShellDescriptor(id_=id_, **aas_descriptor_args)  # type: ignore


def example_submodel_descriptor(id_: str, **kwargs: Any) -> SubmodelDescriptor:
    descriptor_args = dict(
        {
            # TODO: SubmodelDescriptor.__init__() does not take args of Descriptor.__init__()
            # "description": model.MultiLanguageTextType(
            #   {"en-US": "Example description", "de": "Beispiel Description"}
            # ),
            # "display_name": model.MultiLanguageNameType(
            #   {"en-US": "Exaple display name", "de": "Beispiel Anzeigename"}
            # ),
            # TODO: equal to AssetAdministrationShellDescriptor
            # "extension": [model.Extension(
            #     name="Example Descriptor Extension",
            #     value_type=model.datatypes.String,
            #     value="ExampleExtensionValue"
            # )],
            "endpoints": [example_endpoint("SUBMODEL-3.0")],
            "administration": model.AdministrativeInformation(
                version="9", template_id="http://example.org/AdministrativeInformation"
            ),
            "id_short": "TestSubmodel",
            "semantic_id": model.ExternalReference(
                (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "http://example.org/SubmodelDescription/"),)
            ),
            "supplemental_semantic_id": [
                model.ExternalReference(
                    (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "http://example.org/SupplementalID/"),)
                )
            ],
        }
    )
    descriptor_args.update(kwargs)
    return SubmodelDescriptor(id_=id_, **descriptor_args)  # type: ignore

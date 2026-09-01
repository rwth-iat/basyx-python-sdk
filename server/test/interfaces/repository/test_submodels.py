import json

from app.util.converters import base64url_encode
from basyx.aas import model
from basyx.aas.adapter.json import AASToJsonEncoder
from basyx.aas.examples.data.example_aas_missing_attributes import create_example_submodel

from ..format_utils import (
    FormatClient,
    inject_format_clients,
    with_json_client,
    with_xml_client,
)
from .test_base import RepositoryEndpointTestBase


def _encode_reference(reference: model.Reference) -> str:
    return base64url_encode(json.dumps(reference, cls=AASToJsonEncoder))


# semanticId carried by ``create_example_submodel()``.
EXAMPLE_SEMANTIC_ID = model.ExternalReference(
    (model.Key(model.KeyTypes.GLOBAL_REFERENCE, "http://example.org/SubmodelTemplates/ExampleSubmodel"),)
)


@inject_format_clients
class SubmodelsEndpointsTest(RepositoryEndpointTestBase):
    """
    Endpoint tests for the implemented ``/submodels`` routes of :class:`~app.interfaces.repository.WSGIApp`
    that operate on the Submodel itself (the ``/submodel-elements`` subtree is covered separately).

    Bodies are written once against the format-agnostic ``format_client`` helper.
    For each test two variants are generated where the :class:`~..format_utils.JsonFormatClient` and
    :class:`~..format_utils.XmlFormatClient` are injected respectively.
    """

    __test__ = True

    SECOND_ID = "https://example.org/Test_Submodel_Second"

    def two_submodels_store(self) -> model.DictIdentifiableStore:
        store: model.DictIdentifiableStore = model.DictIdentifiableStore()
        store.add(create_example_submodel())
        second = create_example_submodel()
        second.id = self.SECOND_ID
        second.id_short = "SecondSubmodel"
        store.add(second)
        return store

    def _get_submodel_ids(self, format_client: FormatClient, query: str) -> set:
        response = format_client.get(f"/submodels?{query}")
        self.assert_ok(response)
        return {format_client.identifier(node) for node in format_client.parse_collection(response)}

    # ------------------------------------------------------------------ GET /submodels

    @with_json_client
    @with_xml_client
    def test_submodels_get(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        response = format_client.get("/submodels")

        self.assert_ok(response)
        self.assertEqual(2, len(format_client.parse_collection(response)))

    @with_json_client
    @with_xml_client
    def test_submodels_get_empty(self, format_client: FormatClient):
        response = format_client.get("/submodels")

        self.assert_ok(response)
        self.assertEqual(0, len(format_client.parse_collection(response)))

    # ------------------------------------------------------------------ GET /submodels?idShort=...&semanticId=...

    @with_json_client
    @with_xml_client
    def test_submodels_get_filter_by_id_short(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        ids = self._get_submodel_ids(format_client, "idShort=SecondSubmodel")

        self.assertEqual({self.SECOND_ID}, ids)

    @with_json_client
    @with_xml_client
    def test_submodels_get_filter_by_id_short_no_match(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        ids = self._get_submodel_ids(format_client, "idShort=Unknown")

        self.assertEqual(set(), ids)

    @with_json_client
    @with_xml_client
    def test_submodels_get_filter_by_semantic_id(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        ids = self._get_submodel_ids(format_client, f"semanticId={_encode_reference(EXAMPLE_SEMANTIC_ID)}")

        self.assertEqual({"https://example.org/Test_Submodel_Missing", self.SECOND_ID}, ids)

    @with_json_client
    @with_xml_client
    def test_submodels_get_filter_by_semantic_id_no_match(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())
        other = model.ExternalReference((model.Key(model.KeyTypes.GLOBAL_REFERENCE, "https://example.org/other"),))

        ids = self._get_submodel_ids(format_client, f"semanticId={_encode_reference(other)}")

        self.assertEqual(set(), ids)

    # ------------------------------------------------------------------ GET /submodels?limit=...&cursor=...

    @with_json_client
    @with_xml_client
    def test_submodels_get_pagination_limit(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        response = format_client.get("/submodels?limit=1")

        self.assert_ok(response)
        self.assertEqual(1, len(format_client.parse_collection(response)))

    @with_json_client
    @with_xml_client
    def test_submodels_get_pagination_cursor_walks_all_items(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        first_page = {
            format_client.identifier(node)
            for node in format_client.parse_collection(format_client.get("/submodels?limit=1"))
        }
        second_page = {
            format_client.identifier(node)
            for node in format_client.parse_collection(format_client.get("/submodels?limit=1&cursor=2"))
        }

        self.assertEqual(1, len(first_page))
        self.assertEqual(1, len(second_page))
        self.assertEqual(set(), first_page & second_page)
        self.assertEqual(
            {"https://example.org/Test_Submodel_Missing", self.SECOND_ID}, first_page | second_page
        )

    def test_submodels_get_negative_limit_returns_400(self):
        self.object_store.update(self.two_submodels_store())

        response = self.client.get("/submodels?limit=-1")

        self.assert_error(response, 400)

    # ------------------------------------------------------------------ POST /submodels

    @with_json_client
    @with_xml_client
    def test_submodels_post_success(self, format_client: FormatClient):
        example_submodel = create_example_submodel()

        response = format_client.post("/submodels", obj=example_submodel)

        self.assertEqual(201, response.status_code)
        self.assertIsNotNone(self.object_store.get(example_submodel.id, None))

    @with_json_client
    @with_xml_client
    def test_submodels_post_bad(self, format_client: FormatClient):
        example_submodel = create_example_submodel()
        example_submodel.id = None  # type: ignore

        response = format_client.post("/submodels", obj=example_submodel)

        self.assert_error(response, 400)

    @with_json_client
    @with_xml_client
    def test_submodels_post_conflict(self, format_client: FormatClient):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = format_client.post("/submodels", obj=example_submodel)

        self.assert_error(response, 409)

    # ------------------------------------------------------------------ GET /submodels/$metadata

    @with_json_client
    @with_xml_client
    def test_submodels_metadata_get(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        response = format_client.get("/submodels/$metadata")

        self.assert_ok(response)
        self.assertEqual(2, len(format_client.parse_collection(response)))

    def test_submodels_metadata_get_rejects_level(self):
        self.object_store.add(create_example_submodel())

        response = self.client.get("/submodels/$metadata?level=deep")

        self.assert_error(response, 400)

    # ------------------------------------------------------------------ GET /submodels/$reference

    @with_json_client
    @with_xml_client
    def test_submodels_reference_get(self, format_client: FormatClient):
        self.object_store.update(self.two_submodels_store())

        response = format_client.get("/submodels/$reference")

        self.assert_ok(response)
        references = format_client.parse_collection(response)
        self.assertEqual(2, len(references))
        self.assertEqual(
            {"https://example.org/Test_Submodel_Missing", self.SECOND_ID},
            {format_client.reference_target(ref) for ref in references},
        )

    # ------------------------------------------------------------------ GET /submodels/<submodel_id>

    @with_json_client
    @with_xml_client
    def test_submodel_get_success(self, format_client: FormatClient):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = format_client.get(f"/submodels/{base64url_encode(example_submodel.id)}")

        self.assert_ok(response)
        self.assertEqual(example_submodel.id, format_client.identifier(format_client.parse_object(response)))

    @with_json_client
    @with_xml_client
    def test_submodel_get_not_found(self, format_client: FormatClient):
        response = format_client.get(f"/submodels/{base64url_encode('https://example.org/unknown')}")

        self.assert_error(response, 404)

    def test_submodel_get_stripped_omits_submodel_elements(self):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)
        path = f"/submodels/{base64url_encode(example_submodel.id)}"

        full = self.client.get(path)
        stripped = self.client.get(f"{path}?level=core")

        self.assert_ok(full)
        self.assert_ok(stripped)
        self.assertIn("submodelElements", full.get_data(as_text=True))
        self.assertNotIn("submodelElements", stripped.get_data(as_text=True))

    def test_submodel_get_invalid_level_returns_400(self):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = self.client.get(f"/submodels/{base64url_encode(example_submodel.id)}?level=bogus")

        self.assert_error(response, 400)

    def test_submodel_get_extent_not_implemented(self):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = self.client.get(
            f"/submodels/{base64url_encode(example_submodel.id)}?extent=withBlobValue"
        )

        self.assert_error(response, 501)

    # ------------------------------------------------------------------ PUT /submodels/<submodel_id>

    @with_json_client
    @with_xml_client
    def test_submodel_put_success(self, format_client: FormatClient):
        self.object_store.add(create_example_submodel())
        updated_submodel = create_example_submodel()
        updated_submodel.id_short = "UpdatedIdShort"

        response = format_client.put(
            f"/submodels/{base64url_encode(updated_submodel.id)}", obj=updated_submodel
        )

        self.assertEqual(204, response.status_code)
        retrieved_submodel = self.object_store.get(updated_submodel.id, None)
        self.assertIsInstance(retrieved_submodel, model.Submodel)
        self.assertEqual("UpdatedIdShort", retrieved_submodel.id_short)

    @with_json_client
    @with_xml_client
    def test_submodel_put_not_found(self, format_client: FormatClient):
        updated_submodel = create_example_submodel()

        response = format_client.put(
            f"/submodels/{base64url_encode('https://example.org/unknown')}", obj=updated_submodel
        )

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ DELETE /submodels/<submodel_id>

    @with_json_client
    @with_xml_client
    def test_submodel_delete_success(self, format_client: FormatClient):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = format_client.delete(f"/submodels/{base64url_encode(example_submodel.id)}")

        self.assertEqual(204, response.status_code)
        self.assertIsNone(self.object_store.get(example_submodel.id, None))

    @with_json_client
    @with_xml_client
    def test_submodel_delete_not_found(self, format_client: FormatClient):
        response = format_client.delete(f"/submodels/{base64url_encode('https://example.org/unknown')}")

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ GET /submodels/<submodel_id>/$metadata

    @with_json_client
    @with_xml_client
    def test_submodel_metadata_get(self, format_client: FormatClient):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = format_client.get(f"/submodels/{base64url_encode(example_submodel.id)}/$metadata")

        self.assert_ok(response)
        self.assertEqual(
            example_submodel.id, format_client.identifier(format_client.parse_object(response))
        )

    def test_submodel_metadata_get_omits_submodel_elements(self):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = self.client.get(f"/submodels/{base64url_encode(example_submodel.id)}/$metadata")

        self.assert_ok(response)
        self.assertNotIn("submodelElements", response.get_data(as_text=True))

    def test_submodel_metadata_get_rejects_level(self):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = self.client.get(
            f"/submodels/{base64url_encode(example_submodel.id)}/$metadata?level=core"
        )

        self.assert_error(response, 400)

    def test_submodel_metadata_get_not_found(self):
        response = self.client.get(
            f"/submodels/{base64url_encode('https://example.org/unknown')}/$metadata"
        )

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ GET /submodels/<submodel_id>/$reference

    @with_json_client
    @with_xml_client
    def test_submodel_reference_get(self, format_client: FormatClient):
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = format_client.get(f"/submodels/{base64url_encode(example_submodel.id)}/$reference")

        self.assert_ok(response)
        self.assertEqual(
            example_submodel.id, format_client.reference_target(format_client.parse_object(response))
        )

    @with_json_client
    @with_xml_client
    def test_submodel_reference_get_not_found(self, format_client: FormatClient):
        response = format_client.get(
            f"/submodels/{base64url_encode('https://example.org/unknown')}/$reference"
        )

        self.assert_error(response, 404)

import abc
import io
import unittest
from unittest import mock

from app.interfaces import repository
from app.util.converters import base64url_encode
from basyx.aas import model
from basyx.aas.adapter import aasx
from basyx.aas.examples.data.example_aas_missing_attributes import (
    create_example_asset_administration_shell,
    create_example_submodel,
)
from werkzeug.test import Client, TestResponse

from .format_utils import FormatClient, JsonFormatClient, XmlFormatClient


class RespsitoryEdpointTestBase(unittest.TestCase, abc.ABC):
    __test__ = False

    object_store: model.DictIdentifiableStore
    file_store: mock.Mock
    repository_server: repository.WSGIApp
    fmt: FormatClient

    @classmethod
    @abc.abstractmethod
    def build_format_client(cls) -> FormatClient:
        raise NotImplementedError()

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.object_store = model.DictIdentifiableStore()
        cls.file_store = mock.Mock(spec=aasx.AbstractSupplementaryFileContainer)
        cls.repository_server = repository.WSGIApp(cls.object_store, cls.file_store, base_path="")
        cls.fmt = cls.build_format_client()

    def setUp(self) -> None:
        self.object_store.clear()
        self.file_store.reset_mock()

    @classmethod
    def two_shells_store(cls):
        store = model.DictIdentifiableStore()
        store.add(create_example_asset_administration_shell())
        second_shell = create_example_asset_administration_shell()
        second_shell.id = "https://example.org/Test_AssetAdministrationShell_Second"
        store.add(second_shell)
        return store

    # ------------------------------------------------------------------ shared assertion helpers

    def assert_ok(self, response: TestResponse) -> None:
        self.assertEqual(200, response.status_code, msg=response.get_data(as_text=True))
        self.assertEqual(self.fmt.content_type, response.mimetype)

    def assert_error(self, response: TestResponse, status_code: int) -> None:
        self.assertEqual(status_code, response.status_code, msg=response.get_data(as_text=True))
        self.assertFalse(self.fmt.result_success(response))


class TestServiceDescription(RespsitoryEdpointTestBase):
    __test__ = True
    
    @classmethod
    def build_format_client(cls) -> FormatClient:
        return JsonFormatClient(Client(cls.repository_server))

    def test_description(self):
        response = self.fmt.get("/description")
        self.assertEqual(200, response.status_code)


class TestShellsThumbnailEndpoint(RespsitoryEdpointTestBase):
    __test__ = True

    @classmethod
    def build_format_client(cls) -> FormatClient:
        return JsonFormatClient(Client(cls.repository_server))

    # ------------------------------------------------------------------ GET .../asset-information/thumbnail

    def thumbnail_path(self, aas_id: str) -> str:
        return f"/shells/{base64url_encode(aas_id)}/asset-information/thumbnail"

    def test_shell_thumbnail_get_success(self):
        example_shell = create_example_asset_administration_shell()
        example_shell.asset_information.default_thumbnail = model.Resource("/thumbnail.png", "image/png")
        self.object_store.add(example_shell)
        self.file_store.write_file.side_effect = lambda name, stream: stream.write(b"thumbnail-bytes")

        response = self.fmt.get(self.thumbnail_path(example_shell.id))

        self.assertEqual(200, response.status_code)
        self.assertEqual("image/png", response.mimetype)
        self.assertEqual(b"thumbnail-bytes", response.get_data())
        self.file_store.write_file.assert_called_once_with("/thumbnail.png", mock.ANY)

    def test_shell_thumbnail_get_no_thumbnail_set(self):
        example_shell = create_example_asset_administration_shell()
        example_shell.asset_information.default_thumbnail = None
        self.object_store.add(example_shell)

        response = self.fmt.get(self.thumbnail_path(example_shell.id))

        self.assert_error(response, 404)

    def test_shell_thumbnail_get_external_reference(self):
        example_shell = create_example_asset_administration_shell()
        example_shell.asset_information.default_thumbnail = model.Resource(
            "https://example.org/thumbnail.png", "image/png"
        )
        self.object_store.add(example_shell)

        response = self.fmt.get(self.thumbnail_path(example_shell.id))

        self.assert_error(response, 400)

    # ------------------------------------------------------------------ PUT .../asset-information/thumbnail

    def test_shell_thumbnail_put_success(self):
        # Also exercises the "replace an existing local thumbnail" branch, since the fixture shell already
        # carries a (non-local) default_thumbnail; a fresh local one is added on top of that here.
        example_shell = create_example_asset_administration_shell()
        example_shell.asset_information.default_thumbnail = model.Resource("/old.png", "image/png")
        self.object_store.add(example_shell)
        self.file_store.add_file.return_value = "/new.png"

        response = self.fmt.put(
            self.thumbnail_path(example_shell.id),
            data={
                "fileName": "/new.png",
                "file": (io.BytesIO(b"thumbnail-bytes"), "new.png", "image/png"),
            },
            headers={"Accept": self.fmt.content_type},
            content_type="multipart/form-data"
        )

        self.assertEqual(204, response.status_code)
        self.file_store.add_file.assert_called_once_with("/new.png", mock.ANY, "image/png")
        self.file_store.delete_file.assert_called_once_with("/old.png")
        retrieved_shell = self.object_store.get(example_shell.id)
        self.assertIsInstance(retrieved_shell, model.AssetAdministrationShell)
        new_thumbnail = retrieved_shell.asset_information.default_thumbnail
        self.assertIsNotNone(new_thumbnail)
        self.assertEqual("/new.png", new_thumbnail.path)
        self.assertEqual("image/png", new_thumbnail.content_type)

    def test_shell_thumbnail_put_missing_filename(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)

        response = self.fmt.client.put(
            self.thumbnail_path(example_shell.id),
            data={"file": (io.BytesIO(b"thumbnail-bytes"), "thumbnail.png", "image/png")},
            headers={"Accept": self.fmt.content_type},
        )

        self.assert_error(response, 400)

    def test_shell_thumbnail_put_shell_not_found(self):
        response = self.fmt.client.put(
            self.thumbnail_path("https://example.org/unknown"),
            data={
                "fileName": "/thumbnail.png",
                "file": (io.BytesIO(b"thumbnail-bytes"), "thumbnail.png", "image/png"),
            },
            headers={"Accept": self.fmt.content_type},
        )

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ DELETE .../asset-information/thumbnail

    def test_shell_thumbnail_delete_success(self):
        example_shell = create_example_asset_administration_shell()
        example_shell.asset_information.default_thumbnail = model.Resource("/thumbnail.png", "image/png")
        self.object_store.add(example_shell)

        response = self.fmt.delete(self.thumbnail_path(example_shell.id))

        self.assertEqual(204, response.status_code)
        self.file_store.delete_file.assert_called_once_with("/thumbnail.png")
        retrieved_shell = self.object_store.get(example_shell.id)
        self.assertIsInstance(retrieved_shell, model.AssetAdministrationShell)
        self.assertIsNone(retrieved_shell.asset_information.default_thumbnail)

    def test_shell_thumbnail_delete_no_thumbnail_set(self):
        example_shell = create_example_asset_administration_shell()
        example_shell.asset_information.default_thumbnail = None
        self.object_store.add(example_shell)

        response = self.fmt.delete(self.thumbnail_path(example_shell.id))

        self.assert_error(response, 404)

    def test_shell_thumbnail_delete_external_reference(self):
        example_shell = create_example_asset_administration_shell()
        example_shell.asset_information.default_thumbnail = model.Resource(
            "https://example.org/thumbnail.png", "image/png"
        )
        self.object_store.add(example_shell)

        response = self.fmt.delete(self.thumbnail_path(example_shell.id))

        self.assert_error(response, 400)


class _ShellsEndpointsTest(RespsitoryEdpointTestBase, abc.ABC):
    """
    Endpoint tests for the implemented ``/shells`` routes of :class:`~app.interfaces.repository.WSGIApp`.

    Bodies are written once against the format-agnostic :attr:`fmt` helper; the concrete
    :class:`TestShellsEndpointsJson` / :class:`TestShellsEndpointsXml` subclasses run them once per format by
    swapping :attr:`format_client_cls`.
    """

    __test__ = False

    def two_shells_store(self):
        store = model.DictIdentifiableStore()
        store.add(create_example_asset_administration_shell())
        second_shell = create_example_asset_administration_shell()
        second_shell.id = "https://example.org/Test_AssetAdministrationShell_Second"
        store.add(second_shell)
        return store

    # ------------------------------------------------------------------ GET /shells

    def test_shells_get(self):
        self.object_store.update(self.two_shells_store())

        response = self.fmt.get("/shells")

        self.assert_ok(response)
        self.assertEqual(2, len(self.fmt.parse_collection(response)))

    # ------------------------------------------------------------------ POST /shells

    def test_shells_post_success(self):
        example_shell = create_example_asset_administration_shell()

        response = self.fmt.post("/shells", obj=example_shell)

        self.assertEqual(201, response.status_code)
        self.assertIsNotNone(self.object_store.get(example_shell.id, None))

    def test_shells_post_bad(self):
        example_shell = create_example_asset_administration_shell()
        example_shell.id = None  # type: ignore

        response = self.fmt.post("/shells", obj=example_shell)

        self.assert_error(response, 400)

    def test_shells_post_conflict(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)

        response = self.fmt.post("/shells", obj=example_shell)

        self.assert_error(response, 409)

    # ------------------------------------------------------------------ GET /shells/$reference

    def test_shells_reference_get(self):
        self.object_store.update(self.two_shells_store())
        example_shell = next(iter(self.object_store))

        response = self.fmt.get("/shells/$reference")

        self.assert_ok(response)
        references = self.fmt.parse_collection(response)
        self.assertEqual(2, len(references))
        self.assertIn(example_shell.id, [self.fmt.reference_target(ref) for ref in references])

    # ------------------------------------------------------------------ GET /shells/<aas_id>

    def test_shell_get_success(self):
        self.object_store.update(self.two_shells_store())
        example_shell = next(iter(self.object_store))

        response = self.fmt.get(f"/shells/{base64url_encode(example_shell.id)}")

        self.assert_ok(response)
        self.assertEqual(example_shell.id, self.fmt.identifier(self.fmt.parse_object(response)))

    def test_shell_get_not_found(self):
        response = self.fmt.get(f"/shells/{base64url_encode('https://example.org/unknown')}")

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ GET /shells/<aas_id>/$reference

    def test_shell_reference_get(self):
        self.object_store.update(self.two_shells_store())
        example_shell = next(iter(self.object_store))

        response = self.fmt.get(f"/shells/{base64url_encode(example_shell.id)}/$reference")

        self.assert_ok(response)
        self.assertEqual(example_shell.id, self.fmt.reference_target(self.fmt.parse_object(response)))

    # ------------------------------------------------------------------ PUT /shells/<aas_id>

    def test_shell_put_success(self):
        self.object_store.add(create_example_asset_administration_shell())
        updated_shell = create_example_asset_administration_shell()
        updated_shell.id_short = "UpdatedIdShort"

        response = self.fmt.put(f"/shells/{base64url_encode(updated_shell.id)}", obj=updated_shell)

        self.assertEqual(204, response.status_code)
        retrieved_shell = self.object_store.get(updated_shell.id, None)
        self.assertIsInstance(retrieved_shell, model.AssetAdministrationShell)
        self.assertEqual("UpdatedIdShort", retrieved_shell.id_short)

    def test_shell_put_not_found(self):
        updated_shell = create_example_asset_administration_shell()

        response = self.fmt.put(f"/shells/{base64url_encode('https://example.org/unknown')}", obj=updated_shell)

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ DELETE /shells/<aas_id>

    def test_shell_delete_success(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)

        response = self.fmt.delete(f"/shells/{base64url_encode(example_shell.id)}")

        self.assertEqual(204, response.status_code)
        self.assertIsNone(self.object_store.get(example_shell.id, None))

    def test_shell_delete_not_found(self):
        response = self.fmt.delete(f"/shells/{base64url_encode('https://example.org/unknown')}")

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ GET /shells/<aas_id>/asset-information

    def test_shell_asset_information_get(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)

        response = self.fmt.get(f"/shells/{base64url_encode(example_shell.id)}/asset-information")

        self.assert_ok(response)
        self.assertEqual(
            example_shell.asset_information.global_asset_id,
            self.fmt.field(self.fmt.parse_object(response), "globalAssetId"),
        )

    # ------------------------------------------------------------------ PUT /shells/<aas_id>/asset-information

    def test_shell_asset_information_put(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        new_asset_information = model.AssetInformation(
            asset_kind=model.AssetKind.INSTANCE,
            global_asset_id="http://example.org/changed_asset",
        )

        response = self.fmt.put(
            f"/shells/{base64url_encode(example_shell.id)}/asset-information",
            obj=new_asset_information,
        )

        self.assertEqual(204, response.status_code)
        retrieved_shell = self.object_store.get(example_shell.id)
        self.assertIsInstance(retrieved_shell, model.AssetAdministrationShell)
        self.assertEqual(
            "http://example.org/changed_asset",
            retrieved_shell.asset_information.global_asset_id,
        )

    # ------------------------------------------------------------------ GET /shells/<aas_id>/submodel-refs

    def test_shell_submodel_refs_get(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)

        response = self.fmt.get(f"/shells/{base64url_encode(example_shell.id)}/submodel-refs")

        self.assert_ok(response)
        references = self.fmt.parse_collection(response)
        self.assertEqual(1, len(references))
        self.assertEqual("https://example.org/Test_Submodel_Missing", self.fmt.reference_target(references[0]))

    # ------------------------------------------------------------------ POST /shells/<aas_id>/submodel-refs

    def test_shell_submodel_refs_post_success(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        new_ref = model.ModelReference(
            (model.Key(model.KeyTypes.SUBMODEL, "https://example.org/NewSubmodel"),), model.Submodel
        )

        response = self.fmt.post(f"/shells/{base64url_encode(example_shell.id)}/submodel-refs", obj=new_ref)

        self.assertEqual(201, response.status_code)
        retrieved_shell = self.object_store.get(example_shell.id)
        self.assertIsInstance(retrieved_shell, model.AssetAdministrationShell)
        identifiers = {ref.get_identifier() for ref in retrieved_shell.submodel}
        self.assertIn("https://example.org/NewSubmodel", identifiers)

    def test_shell_submodel_refs_post_conflict(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        existing_ref = model.ModelReference(
            (model.Key(model.KeyTypes.SUBMODEL, "https://example.org/Test_Submodel_Missing"),), model.Submodel
        )

        response = self.fmt.post(f"/shells/{base64url_encode(example_shell.id)}/submodel-refs", obj=existing_ref)

        self.assert_error(response, 409)

    # ------------------------------------------------------------------ DELETE /shells/<aas_id>/submodel-refs/<sm_id>

    def test_shell_submodel_refs_delete_success(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        submodel_id = "https://example.org/Test_Submodel_Missing"

        response = self.fmt.delete(
            f"/shells/{base64url_encode(example_shell.id)}/submodel-refs/{base64url_encode(submodel_id)}"
        )

        self.assertEqual(204, response.status_code)
        retrieved_shell = self.object_store.get(example_shell.id)
        self.assertIsInstance(retrieved_shell, model.AssetAdministrationShell)
        self.assertEqual(0, len(list(retrieved_shell.submodel)))

    def test_shell_submodel_refs_delete_not_found(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)

        response = self.fmt.delete(
            f"/shells/{base64url_encode(example_shell.id)}/submodel-refs/"
            f"{base64url_encode('https://example.org/unknown')}"
        )

        self.assert_error(response, 404)

    # ------------------------------------------------------------------ PUT /shells/<aas_id>/submodels/<sm_id>

    def test_shell_submodel_refs_submodel_put(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        self.object_store.add(create_example_submodel())
        updated_submodel = create_example_submodel()
        updated_submodel.id_short = "UpdatedSubmodel"

        response = self.fmt.put(
            f"/shells/{base64url_encode(example_shell.id)}/submodels/{base64url_encode(updated_submodel.id)}",
            obj=updated_submodel,
        )

        self.assertEqual(204, response.status_code)
        retrieved_sm = self.object_store.get(updated_submodel.id)
        self.assertIsInstance(retrieved_sm, model.Submodel)
        self.assertEqual("UpdatedSubmodel", retrieved_sm.id_short)

    # ------------------------------------------------------------------ DELETE /shells/<aas_id>/submodels/<sm_id>

    def test_shell_submodel_refs_submodel_delete(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        example_submodel = create_example_submodel()
        self.object_store.add(example_submodel)

        response = self.fmt.delete(
            f"/shells/{base64url_encode(example_shell.id)}/submodels/{base64url_encode(example_submodel.id)}"
        )

        self.assertEqual(204, response.status_code)
        self.assertIsNone(self.object_store.get(example_submodel.id, None))
        retrieved_shell = self.object_store.get(example_shell.id)
        self.assertIsInstance(retrieved_shell, model.AssetAdministrationShell)
        self.assertEqual(0, len(list(retrieved_shell.submodel)))

    # ------------------------------------------------------------------ /shells/<aas_id>/submodels/<sm_id> redirect

    def test_shell_submodel_refs_submodel_redirect(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        submodel_id = "https://example.org/Test_Submodel_Missing"

        response = self.fmt.get(
            f"/shells/{base64url_encode(example_shell.id)}/submodels/{base64url_encode(submodel_id)}"
        )

        self.assertEqual(307, response.status_code)
        self.assertIn(f"/submodels/{base64url_encode(submodel_id)}", response.headers["Location"])

    def test_shell_submodel_refs_submodel_redirect_with_path(self):
        example_shell = create_example_asset_administration_shell()
        self.object_store.add(example_shell)
        submodel_id = "https://example.org/Test_Submodel_Missing"

        response = self.fmt.get(
            f"/shells/{base64url_encode(example_shell.id)}/submodels/{base64url_encode(submodel_id)}/submodel-elements"
        )

        self.assertEqual(307, response.status_code)
        self.assertTrue(response.headers["Location"].endswith("/submodel-elements"))


class TestShellsEndpointsJson(_ShellsEndpointsTest):
    __test__ = True

    @classmethod
    def build_format_client(cls) -> FormatClient:
        return JsonFormatClient(Client(cls.repository_server))


class TestShellsEndpointsXml(_ShellsEndpointsTest):
    __test__ = True

    @classmethod
    def build_format_client(cls) -> FormatClient:
        return XmlFormatClient(Client(cls.repository_server))

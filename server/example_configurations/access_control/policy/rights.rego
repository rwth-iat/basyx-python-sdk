# Copyright (c) 2026 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

# Rights required by the operations of the AAS HTTP/REST API.
#
# A request is mapped to the operation it calls, and the operation to the rights of the AAS Access Rule Model
# (IDTA-01004) that an access rule must grant. The mapping is the normative annex "Operation to RIGHT Mapping" of
# IDTA-01002 v3.2:
# https://industrialdigitaltwin.io/aas-specifications/IDTA-01002/v3.2/annex/operation-to-right-mapping.html
# The table `annex_operations` is taken from it unchanged; the specification is published by the Industrial Digital
# Twin Association under the Creative Commons Attribution 4.0 International License (CC BY 4.0).
#
# Two rights ("CREATE", "UPDATE") mean that the right depends on whether the resource already exists. No right means
# that the operation takes the right of the request that started it (asynchronous bulk results).
package envoy.authz

import rego.v1

# The API is served below these base paths (`api_base_paths`, "{api_version}" is replaced by `api_version`), e.g.
# "/repository/api/v3.1". The rest of the request path addresses the operation.
api_paths contains trim_suffix(substring(request_path, count(base), -1), "/") if {
	some template in object.get(config, "api_base_paths", [])
	base := replace(template, "{api_version}", api_version)
	startswith(request_path, concat("", [base, "/"]))
}

# Base paths must not overlap; if a request matches more than one, it addresses no operation.
api_path := path if {
	count(api_paths) == 1
	some path in api_paths
}

# HEAD returns the headers of GET and therefore requires the same rights.
operation_method := "GET" if request_method == "HEAD"

operation_method := request_method if request_method != "HEAD"

# Servers may offer operations beyond the specification (`additional_operations`, same shape as below).
operations := array.concat(annex_operations, object.get(config, "additional_operations", []))

matching_operations contains op if {
	some op in operations
	op.method == operation_method
	operation_path_matches(op.path, api_path)
}

# A request whose path and method match no operation, or more than one, addresses no operation.
operation := op if {
	count(matching_operations) == 1
	some op in matching_operations
}

required_rights := {right | some right in operation.rights}

# Each placeholder (e.g. "{aasIdentifier}", "{idShortPath}") matches exactly one non-empty path segment that is not a
# modifier such as "$reference" (see segment_matches).
operation_path_matches(template, path) if {
	template_segments := split(trim_prefix(template, "/"), "/")
	path_segments_ := split(trim_prefix(path, "/"), "/")
	count(template_segments) == count(path_segments_)
	every i, segment in template_segments {
		segment_matches(segment, path_segments_[i])
	}
}

annex_operations := [
	{"name": "GetAssetAdministrationShell", "method": "GET", "path": "/aas", "rights": ["READ"]},
	{"name": "PutAssetAdministrationShell", "method": "PUT", "path": "/aas", "rights": ["UPDATE"]},
	{"name": "GetAssetAdministrationShell-Reference", "method": "GET", "path": "/aas/$reference", "rights": ["VIEW"]},
	{"name": "GetAssetInformation", "method": "GET", "path": "/aas/asset-information", "rights": ["READ"]},
	{"name": "PutAssetInformation", "method": "PUT", "path": "/aas/asset-information", "rights": ["UPDATE"]},
	{"name": "GetThumbnail", "method": "GET", "path": "/aas/asset-information/thumbnail", "rights": ["READ"]},
	{"name": "PutThumbnail", "method": "PUT", "path": "/aas/asset-information/thumbnail", "rights": ["UPDATE"]},
	{"name": "DeleteThumbnail", "method": "DELETE", "path": "/aas/asset-information/thumbnail", "rights": ["DELETE"]},
	{"name": "GetAllSubmodelReferences", "method": "GET", "path": "/aas/submodel-refs", "rights": ["VIEW"]},
	{"name": "PostSubmodelReference", "method": "POST", "path": "/aas/submodel-refs", "rights": ["CREATE"]},
	{"name": "DeleteSubmodelReference", "method": "DELETE", "path": "/aas/submodel-refs/{submodelIdentifier}", "rights": ["DELETE"]},
	{"name": "GetSubmodelById_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}", "rights": ["READ"]},
	{"name": "PutSubmodelById_AAS", "method": "PUT", "path": "/aas/submodels/{submodelIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "PatchSubmodelById_AAS", "method": "PATCH", "path": "/aas/submodels/{submodelIdentifier}", "rights": ["UPDATE"]},
	{"name": "DeleteSubmodelById_AAS", "method": "DELETE", "path": "/aas/submodels/{submodelIdentifier}", "rights": ["DELETE"]},
	{"name": "GetSubmodelById-Metadata_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodeByIdMetadata_AAS", "method": "PATCH", "path": "/aas/submodels/{submodelIdentifier}/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodelById-ValueOnly_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/$value", "rights": ["READ"]},
	{"name": "PatchSubmodelById-ValueOnly_AAS", "method": "PATCH", "path": "/aas/submodels/{submodelIdentifier}/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodelById-Reference_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodelById-Path_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/$path", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElements_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements", "rights": ["READ"]},
	{"name": "PostSubmodelElement_AAS", "method": "POST", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements", "rights": ["CREATE"]},
	{"name": "GetAllSubmodelElements-Metadata_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/$metadata", "rights": ["READ"]},
	{"name": "GetAllSubmodelElements-ValueOnly_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/$value", "rights": ["READ"]},
	{"name": "GetAllSubmodelElementsReference_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/$reference", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElementsPath_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/$path", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["READ"]},
	{"name": "PostSubmodelElementByPath_AAS", "method": "POST", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["CREATE"]},
	{"name": "PutSubmodelElementByPath_AAS", "method": "PUT", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["CREATE", "UPDATE"]},
	{"name": "PatchSubmodelElementValueByPath_AAS", "method": "PATCH", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["UPDATE"]},
	{"name": "DeleteSubmodelElementByPath_AAS", "method": "DELETE", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["DELETE"]},
	{"name": "GetSubmodelElementByPath-Metadata_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodelElementValueByPath-Metadata_AAS", "method": "PATCH", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-ValueOnly_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value", "rights": ["READ"]},
	{"name": "PatchSubmodelElementValueByPathValueOnly_AAS", "method": "PATCH", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-Reference_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath-Path_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$path", "rights": ["VIEW"]},
	{"name": "GetFileByPath_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["READ"]},
	{"name": "PutFileByPath_AAS", "method": "PUT", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["UPDATE"]},
	{"name": "DeleteFileByPath_AAS", "method": "DELETE", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["DELETE"]},
	{"name": "InvokeOperationSync_AAS", "method": "POST", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationSync-ValueOnly_AAS", "method": "POST", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke/$value", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync_AAS", "method": "POST", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync-ValueOnly_AAS", "method": "POST", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async/$value", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncStatus_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-status/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult-ValueOnly_AAS", "method": "GET", "path": "/aas/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}/$value", "rights": ["EXECUTE"]},
	{"name": "GetSubmodel", "method": "GET", "path": "/submodel", "rights": ["READ"]},
	{"name": "PutSubmodel", "method": "PUT", "path": "/submodel", "rights": ["UPDATE"]},
	{"name": "PatchSubmodel", "method": "PATCH", "path": "/submodel", "rights": ["UPDATE"]},
	{"name": "GetSubmodel-Metadata", "method": "GET", "path": "/submodel/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodel-Metadata", "method": "PATCH", "path": "/submodel/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodel-ValueOnly", "method": "GET", "path": "/submodel/$value", "rights": ["READ"]},
	{"name": "PatchSubmodel-ValueOnly", "method": "PATCH", "path": "/submodel/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodel-Reference", "method": "GET", "path": "/submodel/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodel-Path", "method": "GET", "path": "/submodel/$path", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElements", "method": "GET", "path": "/submodel/submodel-elements", "rights": ["READ"]},
	{"name": "PostSubmodelElement", "method": "POST", "path": "/submodel/submodel-elements", "rights": ["CREATE"]},
	{"name": "GetAllSubmodelElements-Metadata", "method": "GET", "path": "/submodel/submodel-elements/$metadata", "rights": ["READ"]},
	{"name": "GetAllSubmodelElements-ValueOnly", "method": "GET", "path": "/submodel/submodel-elements/$value", "rights": ["READ"]},
	{"name": "GetAllSubmodelElements-Reference", "method": "GET", "path": "/submodel/submodel-elements/$reference", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElements-Path", "method": "GET", "path": "/submodel/submodel-elements/$path", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}", "rights": ["READ"]},
	{"name": "PostSubmodelElementByPath", "method": "POST", "path": "/submodel/submodel-elements/{idShortPath}", "rights": ["CREATE"]},
	{"name": "PutSubmodelElementByPath", "method": "PUT", "path": "/submodel/submodel-elements/{idShortPath}", "rights": ["CREATE", "UPDATE"]},
	{"name": "PatchSubmodelElementByPath", "method": "PATCH", "path": "/submodel/submodel-elements/{idShortPath}", "rights": ["UPDATE"]},
	{"name": "DeleteSubmodelElementByPath", "method": "DELETE", "path": "/submodel/submodel-elements/{idShortPath}", "rights": ["DELETE"]},
	{"name": "GetSubmodelElementByPath-Metadata", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodelElementByPath-Metadata", "method": "PATCH", "path": "/submodel/submodel-elements/{idShortPath}/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-ValueOnly", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/$value", "rights": ["READ"]},
	{"name": "PatchSubmodelElementByPath-ValueOnly", "method": "PATCH", "path": "/submodel/submodel-elements/{idShortPath}/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-Reference", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath-Path", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/$path", "rights": ["VIEW"]},
	{"name": "GetFileByPath", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/attachment", "rights": ["READ"]},
	{"name": "PutFileByPath", "method": "PUT", "path": "/submodel/submodel-elements/{idShortPath}/attachment", "rights": ["UPDATE"]},
	{"name": "DeleteFileByPath", "method": "DELETE", "path": "/submodel/submodel-elements/{idShortPath}/attachment", "rights": ["DELETE"]},
	{"name": "InvokeOperation", "method": "POST", "path": "/submodel/submodel-elements/{idShortPath}/invoke", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationSync-ValueOnly", "method": "POST", "path": "/submodel/submodel-elements/{idShortPath}/invoke/$value", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync", "method": "POST", "path": "/submodel/submodel-elements/{idShortPath}/invoke-async", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync-ValueOnly", "method": "POST", "path": "/submodel/submodel-elements/{idShortPath}/invoke-async/$value", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncStatus", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/operation-status/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/operation-results/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult-ValueOnly", "method": "GET", "path": "/submodel/submodel-elements/{idShortPath}/operation-results/{handleId}/$value", "rights": ["EXECUTE"]},
	{"name": "GetAllAssetAdministrationShells", "method": "GET", "path": "/shells", "rights": ["READ"]},
	{"name": "PostAssetAdministrationShell", "method": "POST", "path": "/shells", "rights": ["CREATE"]},
	{"name": "GetAllAssetAdministrationShellsRecentChanges", "method": "GET", "path": "/shells/$recent-changes", "rights": ["READ"]},
	{"name": "GetAllAssetAdministrationShells-Reference", "method": "GET", "path": "/shells/$reference", "rights": ["VIEW"]},
	{"name": "GetAssetAdministrationShellById", "method": "GET", "path": "/shells/{aasIdentifier}", "rights": ["READ"]},
	{"name": "PutAssetAdministrationShellById", "method": "PUT", "path": "/shells/{aasIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "DeleteAssetAdministrationShellById", "method": "DELETE", "path": "/shells/{aasIdentifier}", "rights": ["DELETE"]},
	{"name": "GetAssetAdministrationShellVersionByIdAndDate", "method": "GET", "path": "/shells/{aasIdentifier}/$history", "rights": ["READ"]},
	{"name": "GetAssetAdministrationShellById-Reference_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/$reference", "rights": ["VIEW"]},
	{"name": "GetAssetAdministrationShellByIdSigned", "method": "GET", "path": "/shells/{aasIdentifier}/$signed", "rights": ["READ"]},
	{"name": "GetAssetInformation_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/asset-information", "rights": ["READ"]},
	{"name": "PutAssetInformation_AasRepository", "method": "PUT", "path": "/shells/{aasIdentifier}/asset-information", "rights": ["UPDATE"]},
	{"name": "GetThumbnail_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/asset-information/thumbnail", "rights": ["READ"]},
	{"name": "PutThumbnail_AasRepository", "method": "PUT", "path": "/shells/{aasIdentifier}/asset-information/thumbnail", "rights": ["UPDATE"]},
	{"name": "DeleteThumbnail_AasRepository", "method": "DELETE", "path": "/shells/{aasIdentifier}/asset-information/thumbnail", "rights": ["DELETE"]},
	{"name": "GetAllSubmodelReferences_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodel-refs", "rights": ["VIEW"]},
	{"name": "PostSubmodelReference_AasRepository", "method": "POST", "path": "/shells/{aasIdentifier}/submodel-refs", "rights": ["CREATE"]},
	{"name": "DeleteSubmodelReference_AasRepository", "method": "DELETE", "path": "/shells/{aasIdentifier}/submodel-refs/{submodelIdentifier}", "rights": ["DELETE"]},
	{"name": "GetSubmodelById_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}", "rights": ["READ"]},
	{"name": "PutSubmodelById_AasRepository", "method": "PUT", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "PatchSubmodel_AasRepository", "method": "PATCH", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}", "rights": ["UPDATE"]},
	{"name": "DeleteSubmodelById_AasRepository", "method": "DELETE", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}", "rights": ["DELETE"]},
	{"name": "GetSubmodelById-Metadata_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodelById-Metadata_AasRepository", "method": "PATCH", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodelById-ValueOnly_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/$value", "rights": ["READ"]},
	{"name": "PatchSubmodelById-ValueOnly_AasRepository", "method": "PATCH", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodelById-Reference_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodelById-Path_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/$path", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElements_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements", "rights": ["READ"]},
	{"name": "PostSubmodelElement_AasRepository", "method": "POST", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements", "rights": ["CREATE"]},
	{"name": "GetAllSubmodelElements-Metadata_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/$metadata", "rights": ["READ"]},
	{"name": "GetAllSubmodelElements-ValueOnly_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/$value", "rights": ["READ"]},
	{"name": "GetAllSubmodelElements-Reference_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/$reference", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElements-Path_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/$path", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["READ"]},
	{"name": "PostSubmodelElementByPath_AasRepository", "method": "POST", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["CREATE"]},
	{"name": "PutSubmodelElementByPath_AasRepository", "method": "PUT", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["CREATE", "UPDATE"]},
	{"name": "PatchSubmodelElementValueByPath_AasRepository", "method": "PATCH", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["UPDATE"]},
	{"name": "DeleteSubmodelElementByPath_AasRepository", "method": "DELETE", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["DELETE"]},
	{"name": "GetSubmodelElementByPath-Metadata_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodelElementValueByPath-Metadata", "method": "PATCH", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-ValueOnly_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value", "rights": ["READ"]},
	{"name": "PatchSubmodelElementValueByPath-ValueOnly", "method": "PATCH", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-Reference_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath-Path_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$path", "rights": ["VIEW"]},
	{"name": "GetFileByPath_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["READ"]},
	{"name": "PutFileByPath_AasRepository", "method": "PUT", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["UPDATE"]},
	{"name": "DeleteFileByPath_AasRepository", "method": "DELETE", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["DELETE"]},
	{"name": "InvokeOperation_AasRepository", "method": "POST", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke", "rights": ["EXECUTE"]},
	{"name": "InvokeOperation-ValueOnly_AasRepository", "method": "POST", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke/$value", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync_AasRepository", "method": "POST", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync-ValueOnly_AasRepository", "method": "POST", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async/$value", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncStatus_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-status/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult-ValueOnly_AasRepository", "method": "GET", "path": "/shells/{aasIdentifier}/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}/$value", "rights": ["EXECUTE"]},
	{"name": "QueryAssetAdministrationShells", "method": "POST", "path": "/query/shells", "rights": ["READ"]},
	{"name": "GetAllSubmodels", "method": "GET", "path": "/submodels", "rights": ["READ"]},
	{"name": "PostSubmodel", "method": "POST", "path": "/submodels", "rights": ["CREATE"]},
	{"name": "GetAllSubmodelsRecentChanges", "method": "GET", "path": "/submodels/$recent-changes", "rights": ["READ"]},
	{"name": "GetAllSubmodels-Metadata", "method": "GET", "path": "/submodels/$metadata", "rights": ["READ"]},
	{"name": "GetAllSubmodels-ValueOnly", "method": "GET", "path": "/submodels/$value", "rights": ["READ"]},
	{"name": "GetAllSubmodels-Reference", "method": "GET", "path": "/submodels/$reference", "rights": ["VIEW"]},
	{"name": "GetAllSubmodels-Path", "method": "GET", "path": "/submodels/$path", "rights": ["VIEW"]},
	{"name": "GetSubmodelById", "method": "GET", "path": "/submodels/{submodelIdentifier}", "rights": ["READ"]},
	{"name": "PutSubmodelById", "method": "PUT", "path": "/submodels/{submodelIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "PatchSubmodelById", "method": "PATCH", "path": "/submodels/{submodelIdentifier}", "rights": ["UPDATE"]},
	{"name": "DeleteSubmodelById", "method": "DELETE", "path": "/submodels/{submodelIdentifier}", "rights": ["DELETE"]},
	{"name": "GetSubmodelVersionByIdAndDate", "method": "GET", "path": "/submodels/{submodelIdentifier}/$history", "rights": ["READ"]},
	{"name": "GetSubmodelById-Metadata", "method": "GET", "path": "/submodels/{submodelIdentifier}/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodelById-Metadata", "method": "PATCH", "path": "/submodels/{submodelIdentifier}/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodelById-ValueOnly", "method": "GET", "path": "/submodels/{submodelIdentifier}/$value", "rights": ["READ"]},
	{"name": "PatchSubmodelById-ValueOnly", "method": "PATCH", "path": "/submodels/{submodelIdentifier}/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodelById-Reference", "method": "GET", "path": "/submodels/{submodelIdentifier}/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodelByIdSigned", "method": "GET", "path": "/submodels/{submodelIdentifier}/$signed", "rights": ["READ"]},
	{"name": "GetSubmodelById-Path", "method": "GET", "path": "/submodels/{submodelIdentifier}/$path", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElements_SubmodelRepository", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements", "rights": ["READ"]},
	{"name": "PostSubmodelElement_SubmodelRepo", "method": "POST", "path": "/submodels/{submodelIdentifier}/submodel-elements", "rights": ["CREATE"]},
	{"name": "GetAllSubmodelElements-Metadata_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/$metadata", "rights": ["READ"]},
	{"name": "GetAllSubmodelElements-ValueOnly_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/$value", "rights": ["READ"]},
	{"name": "GetAllSubmodelElements-Reference_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/$reference", "rights": ["VIEW"]},
	{"name": "GetAllSubmodelElements-Path_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/$path", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["READ"]},
	{"name": "PostSubmodelElementByPath_SubmodelRepo", "method": "POST", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["CREATE"]},
	{"name": "PutSubmodelElementByPath_SubmodelRepo", "method": "PUT", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["CREATE", "UPDATE"]},
	{"name": "PatchSubmodelElementByPath_SubmodelRepo", "method": "PATCH", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["UPDATE"]},
	{"name": "DeleteSubmodelElementByPath_SubmodelRepo", "method": "DELETE", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}", "rights": ["DELETE"]},
	{"name": "GetSubmodelElementByPath-Metadata_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$metadata", "rights": ["READ"]},
	{"name": "PatchSubmodelElementByPath-Metadata_SubmodelRepo", "method": "PATCH", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$metadata", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-ValueOnly_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value", "rights": ["READ"]},
	{"name": "PatchSubmodelElementByPath-ValueOnly_SubmodelRepo", "method": "PATCH", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$value", "rights": ["UPDATE"]},
	{"name": "GetSubmodelElementByPath-Reference_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$reference", "rights": ["VIEW"]},
	{"name": "GetSubmodelElementByPath-Path_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/$path", "rights": ["VIEW"]},
	{"name": "GetFileByPath_SubmodelRepo", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["READ"]},
	{"name": "PutFileByPath_SubmodelRepo", "method": "PUT", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["UPDATE"]},
	{"name": "DeleteFileByPath_SubmodelRepo", "method": "DELETE", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/attachment", "rights": ["DELETE"]},
	{"name": "InvokeOperation_SubmodelRepo", "method": "POST", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke", "rights": ["EXECUTE"]},
	{"name": "InvokeOperation-ValueOnly_SubmodelRepository", "method": "POST", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke/$value", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync_SubmodelRepository", "method": "POST", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async", "rights": ["EXECUTE"]},
	{"name": "InvokeOperationAsync-ValueOnly_SubmodelRepository", "method": "POST", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async/$value", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncStatus_SubmodelRepository", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-status/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult_SubmodelRepository", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}", "rights": ["EXECUTE"]},
	{"name": "GetOperationAsyncResult-ValueOnly_SubmodelRepository", "method": "GET", "path": "/submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}/$value", "rights": ["EXECUTE"]},
	{"name": "QuerySubmodels", "method": "POST", "path": "/query/submodels", "rights": ["READ"]},
	{"name": "GetAllConceptDescriptions", "method": "GET", "path": "/concept-descriptions", "rights": ["READ"]},
	{"name": "PostConceptDescription", "method": "POST", "path": "/concept-descriptions", "rights": ["CREATE"]},
	{"name": "GetAllConceptDescriptionsRecentChanges", "method": "GET", "path": "/concept-descriptions/$recent-changes", "rights": ["READ"]},
	{"name": "GetConceptDescriptionById", "method": "GET", "path": "/concept-descriptions/{cdIdentifier}", "rights": ["READ"]},
	{"name": "PutConceptDescriptionById", "method": "PUT", "path": "/concept-descriptions/{cdIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "DeleteConceptDescriptionById", "method": "DELETE", "path": "/concept-descriptions/{cdIdentifier}", "rights": ["DELETE"]},
	{"name": "GetConceptDescriptionByIdSigned", "method": "GET", "path": "/concept-descriptions/{cdIdentifier}/$signed", "rights": ["READ"]},
	{"name": "QueryConceptDescriptions", "method": "POST", "path": "/query/concept-descriptions", "rights": ["READ"]},
	{"name": "GetAllAssetAdministrationShellDescriptors", "method": "GET", "path": "/shell-descriptors", "rights": ["VIEW"]},
	{"name": "PostAssetAdministrationShellDescriptor", "method": "POST", "path": "/shell-descriptors", "rights": ["CREATE"]},
	{"name": "GetAssetAdministrationShellDescriptorById", "method": "GET", "path": "/shell-descriptors/{aasIdentifier}", "rights": ["VIEW"]},
	{"name": "PutAssetAdministrationShellDescriptorById", "method": "PUT", "path": "/shell-descriptors/{aasIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "DeleteAssetAdministrationShellDescriptorById", "method": "DELETE", "path": "/shell-descriptors/{aasIdentifier}", "rights": ["DELETE"]},
	{"name": "GetAllSubmodelDescriptorsThroughSuperpath", "method": "GET", "path": "/shell-descriptors/{aasIdentifier}/submodel-descriptors", "rights": ["VIEW"]},
	{"name": "PostSubmodelDescriptor-ThroughSuperpath", "method": "POST", "path": "/shell-descriptors/{aasIdentifier}/submodel-descriptors", "rights": ["CREATE"]},
	{"name": "GetSubmodelDescriptorByIdThroughSuperpath", "method": "GET", "path": "/shell-descriptors/{aasIdentifier}/submodel-descriptors/{submodelIdentifier}", "rights": ["VIEW"]},
	{"name": "PutSubmodelDescriptorByIdThroughSuperpath", "method": "PUT", "path": "/shell-descriptors/{aasIdentifier}/submodel-descriptors/{submodelIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "DeleteSubmodelDescriptorByIdThroughSuperpath", "method": "DELETE", "path": "/shell-descriptors/{aasIdentifier}/submodel-descriptors/{submodelIdentifier}", "rights": ["DELETE"]},
	{"name": "QueryAssetAdministrationShellDescriptors", "method": "POST", "path": "/query/shell-descriptors", "rights": ["VIEW"]},
	{"name": "BulkPostAssetAdministrationShellDescriptor", "method": "POST", "path": "/bulk/shell-descriptors", "rights": ["CREATE"]},
	{"name": "BulkPutAssetAdministrationShellDescriptorById", "method": "PUT", "path": "/bulk/shell-descriptors", "rights": ["CREATE", "UPDATE"]},
	{"name": "BulkDeleteAssetAdministrationShellDescriptorById", "method": "DELETE", "path": "/bulk/shell-descriptors", "rights": ["DELETE"]},
	{"name": "BulkGetAsyncStatus", "method": "GET", "path": "/bulk/status/{handleId}", "rights": []},
	{"name": "BulkGetAsyncResult", "method": "GET", "path": "/bulk/result/{handleId}", "rights": []},
	{"name": "GetAllSubmodelDescriptors", "method": "GET", "path": "/submodel-descriptors", "rights": ["VIEW"]},
	{"name": "PostSubmodelDescriptor", "method": "POST", "path": "/submodel-descriptors", "rights": ["CREATE"]},
	{"name": "GetSubmodelDescriptorById", "method": "GET", "path": "/submodel-descriptors/{submodelIdentifier}", "rights": ["VIEW"]},
	{"name": "PutSubmodelDescriptorById", "method": "PUT", "path": "/submodel-descriptors/{submodelIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "DeleteSubmodelDescriptorById", "method": "DELETE", "path": "/submodel-descriptors/{submodelIdentifier}", "rights": ["DELETE"]},
	{"name": "QuerySubmodelDescriptors", "method": "POST", "path": "/query/submodel-descriptors", "rights": ["VIEW"]},
	{"name": "BulkPostSubmodel", "method": "POST", "path": "/bulk/submodel-descriptors", "rights": ["CREATE"]},
	{"name": "BulkPutSubmodelDescriptorsById", "method": "PUT", "path": "/bulk/submodel-descriptors", "rights": ["CREATE", "UPDATE"]},
	{"name": "BulkDeleteSubmodelDescriptorsById", "method": "DELETE", "path": "/bulk/submodel-descriptors", "rights": ["DELETE"]},
	{"name": "GetAllAssetAdministrationShellIdsByAssetLink", "method": "GET", "path": "/lookup/shells", "rights": ["VIEW"]},
	{"name": "SearchAllAssetAdministrationShellIdsByAssetLink", "method": "POST", "path": "/lookup/shellsByAssetLink", "rights": ["VIEW"]},
	{"name": "GetAllAssetLinksById", "method": "GET", "path": "/lookup/shells/{aasIdentifier}", "rights": ["VIEW"]},
	{"name": "PostAllAssetLinksById", "method": "POST", "path": "/lookup/shells/{aasIdentifier}", "rights": ["CREATE", "UPDATE"]},
	{"name": "DeleteAllAssetLinksById", "method": "DELETE", "path": "/lookup/shells/{aasIdentifier}", "rights": ["DELETE"]},
	{"name": "GetAllAASXPackageIds", "method": "GET", "path": "/packages", "rights": ["VIEW"]},
	{"name": "PostAASXPackage", "method": "POST", "path": "/packages", "rights": ["CREATE"]},
	{"name": "GetAASXByPackageId", "method": "GET", "path": "/packages/{packageId}", "rights": ["READ"]},
	{"name": "PutAASXByPackageId", "method": "PUT", "path": "/packages/{packageId}", "rights": ["CREATE", "UPDATE"]},
	{"name": "DeleteAASXByPackageId", "method": "DELETE", "path": "/packages/{packageId}", "rights": ["DELETE"]},
	{"name": "PostAsyncAASXPackage", "method": "POST", "path": "/packages-async", "rights": ["CREATE"]},
	{"name": "GetAasxAsyncStatus", "method": "GET", "path": "/packages-async/status/{handleId}", "rights": ["CREATE"]},
	{"name": "GetAasxAsyncResult", "method": "GET", "path": "/packages-async/result/{handleId}", "rights": ["CREATE"]},
	{"name": "GenerateSerializationByIds", "method": "GET", "path": "/serialization", "rights": ["READ"]},
	{"name": "GetSelfDescription", "method": "GET", "path": "/description", "rights": ["READ"]},
]

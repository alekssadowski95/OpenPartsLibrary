"""SPDX hardware BOM export helpers."""

import uuid
from datetime import datetime, timezone


def build_spdx_hardware_bom(components):
    """Build an SPDX 3 JSON-LD document for selected hardware components.

    :param components: Iterable of dictionaries containing part metadata,
        quantity, pricing, supplier, and optional CAD archive filename.
    :return: SPDX JSON-LD document ready to serialize.
    :rtype: dict
    """

    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    namespace = f"https://openpartslibrary.local/spdxdocs/my-bill-of-materials-{uuid.uuid4()}"
    creation_info = {
        "type": "CreationInfo",
        "specVersion": "3.0.1",
        "created": created,
        "createdBy": ["https://openpartslibrary.local/agents/OpenPartsLibrary"],
        "createdUsing": ["https://openpartslibrary.local/tools/OpenPartsLibrary"],
    }
    bom_id = f"{namespace}#hardware-bom"

    graph = [
        {
            "spdxId": "https://openpartslibrary.local/agents/OpenPartsLibrary",
            "type": "Agent",
            "creationInfo": creation_info,
            "name": "OpenPartsLibrary",
        },
        {
            "spdxId": "https://openpartslibrary.local/tools/OpenPartsLibrary",
            "type": "Tool",
            "creationInfo": creation_info,
            "name": "OpenPartsLibrary",
        },
    ]

    component_ids = []
    relationship_ids = []
    for index, component in enumerate(components, start=1):
        component_id = f"{namespace}#component-{index}"
        component_ids.append(component_id)

        graph.append({
            "spdxId": component_id,
            "type": "Package",
            "creationInfo": creation_info,
            "name": component["name"],
            "summary": f"Part number: {component['part_number']}",
            "description": component["description"],
            "downloadLocation": "NOASSERTION",
            "comment": (
                f"Hardware BOM item. Quantity: {component['quantity']}; "
                f"price per item: {component['price_per_item']} {component['currency']}; "
                f"supplier: {component['supplier'] or 'NOASSERTION'}; "
                f"CAD file in ZIP: {component['cad_file'] or 'not included'}."
            ),
        })

        relationship_id = f"{namespace}#relationship-contains-{index}"
        relationship_ids.append(relationship_id)
        graph.append({
            "spdxId": relationship_id,
            "type": "Relationship",
            "creationInfo": creation_info,
            "from": bom_id,
            "relationshipType": "contains",
            "to": [component_id],
        })

    graph.append({
        "spdxId": bom_id,
        "type": "Bom",
        "creationInfo": creation_info,
        "name": "OpenPartsLibrary Hardware BOM",
        "summary": "Hardware bill of materials for selected OpenPartsLibrary parts.",
        "profileConformance": ["core", "software"],
        "rootElement": component_ids,
        "element": component_ids + relationship_ids,
    })

    return {
        "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
        "@graph": graph,
    }

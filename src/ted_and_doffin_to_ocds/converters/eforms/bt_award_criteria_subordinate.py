# converters/bt_award_criteria_subordinate.py

import logging
from typing import Any

from lxml import etree

logger = logging.getLogger(__name__)

NAMESPACES = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
    "efext": "http://data.europa.eu/p27/eforms-ubl-extensions/1",
    "efbc": "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1",
}

# Mapping table for number weight codes
NUMBER_WEIGHT_MAPPING = {
    "dec-exa": "decimalExact",
    "dec-mid": "decimalRangeMiddle",
    "ord-imp": "order",
    "per-exa": "percentageExact",
    "per-mid": "percentageRangeMiddle",
    "poi-exa": "pointsExact",
    "poi-mid": "pointsRangeMiddle",
}

# Mapping table for threshold codes
THRESHOLD_CODE_MAPPING = {"max-pass": "maximumBids", "min-score": "minimumScore"}


def _add_value(obj: dict[str, Any], key: str, value: Any) -> None:
    existing = obj.get(key)
    if existing is None:
        obj[key] = value
        return
    if isinstance(existing, list):
        if value not in existing:
            existing.append(value)
        return
    if existing != value:
        obj[key] = [existing, value]


def _parse_subordinate_criteria(element: etree._Element) -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = []

    sub_criteria = element.xpath(
        ".//cac:TenderingTerms/cac:AwardingTerms/cac:AwardingCriterion"
        "/cac:SubordinateAwardingCriterion",
        namespaces=NAMESPACES,
    )

    for sub in sub_criteria:
        criterion: dict[str, Any] = {}

        name = sub.xpath("cbc:Name/text()", namespaces=NAMESPACES)
        if name and name[0].strip():
            criterion["name"] = name[0].strip()

        description = sub.xpath("cbc:Description/text()", namespaces=NAMESPACES)
        if description and description[0].strip():
            criterion["description"] = description[0].strip()

        crit_type = sub.xpath(
            "cbc:AwardingCriterionTypeCode[@listName='award-criterion-type']/text()",
            namespaces=NAMESPACES,
        )
        if crit_type and crit_type[0].strip():
            criterion["type"] = crit_type[0].strip()

        parameters = sub.xpath(
            "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/"
            "efext:EformsExtension/efac:AwardCriterionParameter",
            namespaces=NAMESPACES,
        )

        for param in parameters:
            code_elem = param.xpath("efbc:ParameterCode", namespaces=NAMESPACES)
            code_text = code_elem[0].text.strip() if code_elem and code_elem[0].text else ""
            list_name = code_elem[0].get("listName") if code_elem else None
            numeric_texts = param.xpath(
                "efbc:ParameterNumeric/text()",
                namespaces=NAMESPACES,
            )
            numeric_text = numeric_texts[0].strip() if numeric_texts else ""

            if list_name == "number-weight":
                if code_text and code_text in NUMBER_WEIGHT_MAPPING:
                    _add_value(criterion, "weight", NUMBER_WEIGHT_MAPPING[code_text])
                if numeric_text:
                    _add_value(criterion, "number", numeric_text)
            elif list_name == "number-fixed":
                if code_text:
                    _add_value(criterion, "fixed", code_text)
                if numeric_text:
                    try:
                        _add_value(criterion, "number", float(numeric_text))
                    except ValueError:
                        logger.warning(
                            "Invalid fixed number value '%s' in SubordinateAwardingCriterion",
                            numeric_text,
                        )
            elif list_name == "number-threshold":
                if code_text and code_text in THRESHOLD_CODE_MAPPING:
                    _add_value(
                        criterion,
                        "threshold",
                        THRESHOLD_CODE_MAPPING[code_text],
                    )
                if numeric_text:
                    try:
                        _add_value(criterion, "number", float(numeric_text))
                    except ValueError:
                        logger.warning(
                            "Invalid threshold number value '%s' in SubordinateAwardingCriterion",
                            numeric_text,
                        )

        if criterion:
            criteria.append(criterion)

    return criteria


def parse_subordinate_award_criteria(xml_content: str | bytes) -> dict[str, Any] | None:
    """Parse SubordinateAwardingCriterion blocks into coherent award criteria objects.

    Builds a single, consistent awardCriteria.criteria list per lot / lot group,
    combining type, name, description and number parameters from the same
    SubordinateAwardingCriterion element.
    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    root = etree.fromstring(xml_content)
    result: dict[str, Any] = {"tender": {}}

    lots_data = []
    lots = root.xpath(
        "//cac:ProcurementProjectLot[cbc:ID/@schemeName='Lot']",
        namespaces=NAMESPACES,
    )
    for lot in lots:
        lot_id = lot.xpath("cbc:ID/text()", namespaces=NAMESPACES)[0]
        criteria = _parse_subordinate_criteria(lot)
        if criteria:
            lots_data.append({"id": lot_id, "awardCriteria": {"criteria": criteria}})

    if lots_data:
        result["tender"]["lots"] = lots_data

    lot_groups_data = []
    lot_groups = root.xpath(
        "//cac:ProcurementProjectLot[cbc:ID/@schemeName='LotsGroup']",
        namespaces=NAMESPACES,
    )
    for lot_group in lot_groups:
        lot_group_id = lot_group.xpath("cbc:ID/text()", namespaces=NAMESPACES)[0]
        criteria = _parse_subordinate_criteria(lot_group)
        if criteria:
            lot_groups_data.append(
                {"id": lot_group_id, "awardCriteria": {"criteria": criteria}}
            )

    if lot_groups_data:
        result["tender"]["lotGroups"] = lot_groups_data

    return result if result["tender"] else None


def merge_subordinate_award_criteria(
    release_json: dict[str, Any], award_criteria_data: dict[str, Any] | None
) -> None:
    """Merge parsed SubordinateAwardingCriterion data into the release JSON."""
    if not award_criteria_data:
        logger.warning("No SubordinateAwardingCriterion data to merge")
        return

    tender = release_json.setdefault("tender", {})

    if "lots" in award_criteria_data.get("tender", {}):
        existing_lots = tender.setdefault("lots", [])
        for new_lot in award_criteria_data["tender"]["lots"]:
            existing_lot = next(
                (lot for lot in existing_lots if lot["id"] == new_lot["id"]),
                None,
            )
            if existing_lot:
                award_criteria = existing_lot.setdefault("awardCriteria", {})
                award_criteria["criteria"] = new_lot["awardCriteria"]["criteria"]
            else:
                existing_lots.append(new_lot)

    if "lotGroups" in award_criteria_data.get("tender", {}):
        existing_lot_groups = tender.setdefault("lotGroups", [])
        for new_group in award_criteria_data["tender"]["lotGroups"]:
            existing_group = next(
                (group for group in existing_lot_groups if group["id"] == new_group["id"]),
                None,
            )
            if existing_group:
                award_criteria = existing_group.setdefault("awardCriteria", {})
                award_criteria["criteria"] = new_group["awardCriteria"]["criteria"]
            else:
                existing_lot_groups.append(new_group)

    logger.info("Merged SubordinateAwardingCriterion data")

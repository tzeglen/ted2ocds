# converters/bt_place_performance_address_procedure.py

import logging
from typing import Any

from lxml import etree

logger = logging.getLogger(__name__)

NAMESPACES = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}

# ISO 3166-1 alpha-3 to alpha-2 conversion dictionary for European countries
ISO_3166_CONVERSION = {
    "ALB": "AL",
    "AND": "AD",
    "AUT": "AT",
    "BLR": "BY",
    "BEL": "BE",
    "BIH": "BA",
    "BGR": "BG",
    "HRV": "HR",
    "CYP": "CY",
    "CZE": "CZ",
    "DNK": "DK",
    "EST": "EE",
    "FIN": "FI",
    "FRA": "FR",
    "DEU": "DE",
    "GRC": "GR",
    "HUN": "HU",
    "ISL": "IS",
    "IRL": "IE",
    "ITA": "IT",
    "KAZ": "KZ",
    "XKX": "XK",
    "LVA": "LV",
    "LIE": "LI",
    "LTU": "LT",
    "LUX": "LU",
    "MLT": "MT",
    "MDA": "MD",
    "MCO": "MC",
    "MNE": "ME",
    "NLD": "NL",
    "MKD": "MK",
    "NOR": "NO",
    "POL": "PL",
    "PRT": "PT",
    "ROU": "RO",
    "RUS": "RU",
    "SMR": "SM",
    "SRB": "RS",
    "SVK": "SK",
    "SVN": "SI",
    "ESP": "ES",
    "SWE": "SE",
    "CHE": "CH",
    "TUR": "TR",
    "UKR": "UA",
    "GBR": "GB",
    "VAT": "VA",
}


def _convert_country_code(code: str) -> str:
    converted = ISO_3166_CONVERSION.get(code.upper())
    if not converted:
        logger.warning("No conversion found for country code: %s", code)
        return code
    return converted


def parse_procedure_place_performance_address(
    xml_content: str | bytes,
) -> dict[str, Any] | None:
    """Parse procedure place performance address from RealizedLocation.

    Builds one Address per cac:RealizedLocation, combining street, postal code,
    locality, region, country and optional description into a single object.
    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    try:
        root = etree.fromstring(xml_content)
        result = {"tender": {"deliveryAddresses": []}}

        locations = root.xpath(
            "/*/cac:ProcurementProject/cac:RealizedLocation",
            namespaces=NAMESPACES,
        )

        for location in locations:
            address: dict[str, Any] = {}

            # Description (BT-728)
            description = location.xpath("cbc:Description/text()", namespaces=NAMESPACES)
            if description and description[0].strip():
                address["description"] = description[0].strip()
                language_id = location.xpath(
                    "cbc:Description/@languageID", namespaces=NAMESPACES
                )
                if language_id:
                    address["language"] = language_id[0]

            # Address fields
            addr = location.xpath("cac:Address", namespaces=NAMESPACES)
            if addr:
                addr = addr[0]

                # Street address (StreetName + AdditionalStreetName + AddressLine/Line)
                street_parts = []
                street_name = addr.xpath("cbc:StreetName/text()", namespaces=NAMESPACES)
                if street_name:
                    street_parts.append(street_name[0])

                additional_street = addr.xpath(
                    "cbc:AdditionalStreetName/text()", namespaces=NAMESPACES
                )
                if additional_street:
                    street_parts.append(additional_street[0])

                address_lines = addr.xpath(
                    "cac:AddressLine/cbc:Line/text()", namespaces=NAMESPACES
                )
                street_parts.extend(address_lines)

                if street_parts:
                    address["streetAddress"] = ", ".join(
                        part.strip() for part in street_parts if part.strip()
                    )

                postal_zone = addr.xpath(
                    "cbc:PostalZone/text()", namespaces=NAMESPACES
                )
                if postal_zone and postal_zone[0].strip():
                    address["postalCode"] = postal_zone[0].strip()

                city = addr.xpath("cbc:CityName/text()", namespaces=NAMESPACES)
                if city and city[0].strip():
                    address["locality"] = city[0].strip()

                region = addr.xpath(
                    "cbc:CountrySubentityCode/text()", namespaces=NAMESPACES
                )
                if region and region[0].strip():
                    address["region"] = region[0].strip()

                country = addr.xpath(
                    "cac:Country/cbc:IdentificationCode/text()",
                    namespaces=NAMESPACES,
                )
                if country and country[0].strip():
                    address["country"] = _convert_country_code(country[0].strip())

            if address:
                result["tender"]["deliveryAddresses"].append(address)

        return result if result["tender"]["deliveryAddresses"] else None

    except Exception:
        logger.exception("Error parsing procedure place performance address")
        return None


def merge_procedure_place_performance_address(
    release_json: dict[str, Any],
    address_data: dict[str, Any] | None,
) -> None:
    """Merge procedure place performance address data into the release JSON."""
    if not address_data:
        logger.info("No procedure place performance address data to merge")
        return

    tender = release_json.setdefault("tender", {})
    tender["deliveryAddresses"] = address_data["tender"]["deliveryAddresses"]
    logger.info(
        "Merged procedure place performance address data: %d addresses",
        len(address_data["tender"]["deliveryAddresses"]),
    )

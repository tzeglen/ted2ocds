# converters/bt_publication_date_notice.py

import logging

from lxml import etree

from ted_and_doffin_to_ocds.utils.date_utils import start_date

logger = logging.getLogger(__name__)


def parse_notice_publication_date(xml_content: str | bytes) -> str | None:
    """Parse notice publication date from efac:Publication/efbc:PublicationDate.

    Args:
        xml_content: XML content to parse

    Returns:
        ISO formatted date string (start of day) or None if no value found.

    """
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    root = etree.fromstring(xml_content)
    namespaces = {
        "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
        "efext": "http://data.europa.eu/p27/eforms-ubl-extensions/1",
        "efbc": "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1",
    }

    publication_date = root.xpath(
        (
            "/*/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/"
            "efext:EformsExtension/efac:Publication/efbc:PublicationDate/text()"
        ),
        namespaces=namespaces,
    )

    if not publication_date:
        return None

    try:
        return start_date(publication_date[0])
    except ValueError:
        logger.exception("Invalid notice publication date format")
        return None


def merge_notice_publication_date(
    release_json: dict, notice_publication_date: str | None
) -> None:
    """Merge notice publication date into release JSON root."""
    if not notice_publication_date:
        logger.warning("No notice publication date data to merge")
        return

    release_json["publicationDate"] = notice_publication_date
    logger.info("Merged notice publication date: %s", notice_publication_date)

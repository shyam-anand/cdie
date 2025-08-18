import logging
from cdie.extraction.auditdate import AuditDateExtractor
from cdie.extraction.auditor import AuditorExtractor
from cdie.extraction.findings import FindingsExtractor
from cdie.extraction.suppliers import SupplierExtractor
import spacy
from spacy.language import Language

logger = logging.getLogger(__name__)

nlp: Language | None = None


def get_nlp() -> Language:
    global nlp
    if nlp is None:
        # enable only Named Entity Recognition
        nlp = spacy.load("en_core_web_sm", exclude=["attribute_ruler", "lemmatizer"])
        nlp.add_pipe("sentencizer")
        logger.info("nlp loaded")
    return nlp


extractors = {
    "auditor": AuditorExtractor(get_nlp()),
    "date": AuditDateExtractor(get_nlp()),
    "supplier": SupplierExtractor(get_nlp()),
    "findings": FindingsExtractor(get_nlp()),
}

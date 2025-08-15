import argparse

from cdie import loggingconfig
from cdie.extraction import extract
from cdie.extraction.auditreport import AuditReport

logger = loggingconfig.get_logger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--extract",
        nargs="*",
        default=["all"],
        choices=["auditor", "date", "factory", "findings", "all"],
    )
    parser.add_argument("-f", "--file", type=str)
    args, _ = parser.parse_known_args()

    source_file = args.file
    if (extract_args := args.extract) and "all" in extract_args:
        extract_types = ["auditor", "date", "factory", "findings"]
    else:
        extract_types = extract_args

    print(f"Extracting info from {source_file}")
    report = AuditReport(source_file)
    for candidate in extract.extract_info(source_file, extract_types=extract_types):
        report.add_candidate(candidate)
    audit_report = report.get_report()
    logger.info(audit_report)

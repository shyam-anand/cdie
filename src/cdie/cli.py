import argparse
import pathlib

from cdie import loggingconfig

from cdie.reports import reportgenerator
from cdie.reports import requestid
from cdie.ingestion import pipeline as ingestion_pipeline

logger = loggingconfig.get_logger(__name__)


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--extract",
        nargs="*",
        default=["all"],
        choices=["auditor", "date", "supplier", "findings", "all"],
    )
    parser.add_argument("-f", "--file", type=str, required=True)
    parser.add_argument("-n", "--no-report", action="store_true")
    args, _ = parser.parse_known_args()

    if (extract_args := args.extract) and "all" in extract_args:
        extract_types = ["auditor", "date", "supplier", "findings"]
    else:
        extract_types = extract_args

    request_id = requestid.get_request_id()
    ingestion_pipeline.run(
        pathlib.Path(args.file),
        request_id,
        extract_types,  # type: ignore
        not args.no_report,
    )
    report = reportgenerator.get_report(request_id)
    print("-" * 80)
    print(report.model_dump_json(indent=2) if report else "No report found")
    print("-" * 80)


if __name__ == "__main__":
    cli()

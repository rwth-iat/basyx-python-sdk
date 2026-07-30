import argparse
import logging
import re
import sys
import traceback
from pathlib import Path
from typing import Optional

from basyx.aas import adapter
from basyx.aas.model import AASConstraintViolation

logger = logging.getLogger(__name__)


def sanitize_name(name: str, max_len: int = 120) -> str:
    pattern = r'[<>:"/\\|?*\x00-\x1f\s\'{}\(\)\[\]]'
    name = re.sub(pattern, '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')[:max_len]



def write_error_report(file_type, example_file, rel_path, error_dir, tb):
    error_dir.mkdir(parents=True, exist_ok=True)
    # Use the full relative path (not just the stem) to avoid collisions: generated example sets reuse
    # the same filenames across many different subdirectories.
    error_file = error_dir / f"{sanitize_name(str(rel_path))}.txt"

    content = example_file.read_text(encoding="utf-8")
    error_output = f"=== {file_type.upper()} File: {rel_path} ===\n{content}\n\n=== Stacktrace ====\n{tb}"
    error_file.write_text(error_output, encoding="utf-8")


def run_example_test(file_type, example_file, read_fn, base_path=None, output_dir=None, is_xml=False):
    rel_path = example_file.relative_to(base_path) if base_path else example_file

    try:
        read_fn(example_file)
        return True
    except (KeyError, TypeError, ValueError, AASConstraintViolation) as ex:
        tb = traceback.format_exc()
        error_msg = extract_error_message(ex) if is_xml else str(ex).split(">>>")[0].strip()
        logger.error(f"[{file_type.upper()}] ERROR on {rel_path}: {error_msg}")

        if output_dir:
            error_dir = output_dir / file_type / sanitize_name(error_msg)
            write_error_report(file_type, example_file, rel_path, error_dir, tb)
        return False

    except NotImplementedError as ex:
        tb = traceback.format_exc()
        error_msg = extract_error_message(ex) if is_xml else str(ex).split(">>>")[0].strip()
        logger.warning(f"[{file_type.upper()}] NOT_IMPLEMENTED on {rel_path}: {error_msg}")

        if output_dir:
            error_dir = output_dir / file_type / "NotImplementedError" / sanitize_name(error_msg)
            write_error_report(file_type, example_file, rel_path, error_dir, tb)
        return True

    except Exception as ex:
        # Catch-all so an exception type not (yet) anticipated by the except clauses above (e.g. thrown by a
        # future implementation change) fails just this one example instead of aborting the whole run.
        # Deliberately not `except BaseException`, so KeyboardInterrupt/SystemExit still propagate.
        tb = traceback.format_exc()
        error_msg = extract_error_message(ex) if is_xml else str(ex).split(">>>")[0].strip()
        logger.error(f"[{file_type.upper()}] UNEXPECTED {type(ex).__name__} on {rel_path}: {error_msg}")

        if output_dir:
            error_dir = (
                    output_dir
                    / file_type
                    / "UnexpectedError"
                    / sanitize_name(type(ex).__name__)
                    / sanitize_name(error_msg)
            )
            write_error_report(file_type, example_file, rel_path, error_dir, tb)
        return False

def extract_error_message(ex):
    message = str(ex)
    cause = ex.__cause__
    while cause is not None:
        message = f"{message} -> {cause}"
        cause = cause.__cause__
    return re.sub(r'on line [0-9]+', "", message.split("->")[-1]).strip()


def test_json_example(example_file: Path, base_path: Optional[Path] = None, output_dir: Optional[Path] = None) -> bool:
    """
    Attempts to read and deserialize an example file. Reports the status and saves information to output path.

    :param example_file: File which contains the example that should be deserialized
    :param base_path: Base directory to compute relative paths
    :param output_dir: Path to store the failed outputs
    :return: bool that indicates if the example was successfully deserialized
    """
    return run_example_test(
        file_type="json",
        example_file=example_file,
        read_fn=lambda f: adapter.json.read_aas_json_file(f, failsafe=False),
        base_path=base_path,
        output_dir=output_dir,
    )


def test_xml_example(example_file: Path, base_path: Optional[Path] = None, output_dir: Optional[Path] = None) -> bool:
    """
    Attempts to read and deserialize an XML example file. Reports the status and saves information to output path.

    :param example_file: File which contains the example that should be deserialized
    :param base_path: Base directory to compute relative paths
    :param output_dir: Path to store the failed outputs
    :return: bool that indicates if the example was successfully deserialized
    """
    return run_example_test(
        file_type="xml",
        example_file=example_file,
        read_fn=lambda f: adapter.xml.read_aas_xml_file(f, failsafe=False),
        base_path=base_path,
        output_dir=output_dir,
        is_xml=True,
    )


def main(example_path_str: str, output_path_str: Optional[str]) -> None:
    example_path = Path(example_path_str)
    output_path = Path(output_path_str) if output_path_str else None
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)

    test_configs = [
        ("JSON", example_path / "json" / "examples" / "generated", "*.json", test_json_example),
        ("XML", example_path / "xml" / "examples" / "generated", "*.xml", test_xml_example),
    ]

    total_failed = 0
    for name, directory, glob_pattern, test_fn in test_configs:
        total = 0
        failed = 0
        for test_file in sorted(directory.glob(f"**/{glob_pattern}")):
            total += 1
            if not test_fn(test_file, directory, output_path):
                failed += 1

        if failed == 0:
            logger.info(f"No {name} tests out of {total:d} failed")
        else:
            logger.error(f"Failed {failed:d}/{total:d} {name.lower()} tests")

        total_failed += failed

    sys.exit(total_failed)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", required=True, help="path to examples directory")
    parser.add_argument("--output", required=False, help="path to output directory")
    args = parser.parse_args()

    main(args.examples, args.output)
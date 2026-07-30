import argparse
import logging
import re
import sys
import traceback
from pathlib import Path
from typing import Callable, Literal, Optional

from basyx.aas import adapter
from basyx.aas.model import AASConstraintViolation

logger = logging.getLogger(__name__)

def sanitize_name(name: str, max_len: int = 120) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\s]', '_', name)
    return name[:max_len]

def test_json_example(example_file: Path, base_path: Optional[Path] = None, output_dir: Optional[Path] = None) -> bool:
    """
    Attempts to read and deserialize an example file. Reports the status and saves information to output path.

    :param example_file: File which contains the example that should be deserialized
    :param deserializer: Function that is used to deserialize the example
    :param output_dir: Path to store the failed outputs
    :return: bool that indicates if the example was successfully deserialized
    """
    try:
        adapter.json.read_aas_json_file(example_file, failsafe=False)
        return True
    except (KeyError, TypeError, ValueError, AASConstraintViolation) as ex:
        tb = traceback.format_exc()
        error_msg = str(ex).split(">>>")[0].strip()

        rel_path = example_file.relative_to(base_path) if base_path else example_file
        logger.error(f"[JSON] ERROR on {rel_path}: {error_msg}")

        if output_dir:
            error_dir = output_dir / sanitize_name(error_msg)
            error_dir.mkdir(parents=True, exist_ok=True)
            error_file = error_dir / f"{sanitize_name(example_file.stem)}.txt"

            json_content = example_file.read_text(encoding="utf-8")
            error_output = f"=== JSON File: {rel_path} ===\n{json_content}\n\n=== Stacktrace ====\n{tb}"
            error_file.write_text(error_output, encoding="utf-8")
        return False
    except NotImplementedError as ex:
        tb = traceback.format_exc()
        error_msg = str(ex).split(">>>")[0].strip()

        rel_path = example_file.relative_to(base_path) if base_path else example_file
        logger.warning(f"[JSON] Unimplemented behavior on {rel_path}: {error_msg}")

        if output_dir:
            error_dir = output_dir / "NotImplementedError" / sanitize_name(error_msg)
            error_dir.mkdir(parents=True, exist_ok=True)
            error_file = error_dir / f"{sanitize_name(example_file.stem)}.txt"

            json_content = example_file.read_text(encoding="utf-8")
            error_output = f"=== JSON File: {rel_path} ===\n{json_content}\n\n=== Stacktrace ====\n{tb}"
            error_file.write_text(error_output, encoding="utf-8")
        return True

def main(example_path_str: str, output_path_str: Optional[str])-> None:
    example_path = Path(example_path_str)
    json_example_dir = example_path / "json" / "examples"
    xml_example_dir = example_path / "xml" / "examples"

    output_path = None
    if output_path_str:
        output_path = Path(output_path_str)
        output_path.mkdir(parents=True, exist_ok=True)

    total = 0
    failed = 0
    for json_test in json_example_dir.glob("**/*.json"):
        total += 1
        success = test_json_example(json_test, json_example_dir, output_path)
        if not success:
            failed += 1

    if failed == 0:
        logger.info(f"No JSON tests out of {total:d} failed")
    else:
        logger.error(f"Failed {failed:d}/{total:d} json tests")
    sys.exit(failed)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", required=True, help="path to examples directory")
    parser.add_argument("--output", required=False, help="path to output directory")
    args = parser.parse_args()

    main(args.examples, args.output)

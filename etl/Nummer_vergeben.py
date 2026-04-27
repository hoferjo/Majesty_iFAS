"""
Article Number Assignment Module (Nummer_vergeben)

Generates 8-digit article numbers in the format: XX.YY.ZZZZ
- Skips existing numbers in PROD, TEST databases
- Skips "majesty" numbers (existing numbers from artikelstamm_majesty)
- Skips previously generated numbers (stored in generated_numbers.csv)
- Returns the lowest available number matching the criteria
"""

from pathlib import Path
from typing import Optional, Set
import csv
import logging


def _get_generated_numbers_path(base_dir: Path) -> Path:
    """Get the path to the generated numbers tracking file."""
    return base_dir / "data" / "processed" / "cache" / "generated_numbers.csv"


def _load_generated_numbers(base_dir: Path) -> Set[str]:
    """
    Load all previously generated article numbers.

    Args:
        base_dir: Base directory containing the data

    Returns:
        Set of previously generated article numbers
    """
    generated = set()
    numbers_path = _get_generated_numbers_path(base_dir)

    logging.info(f"[LOAD] Loading generated numbers from {numbers_path}")

    if not numbers_path.exists():
        logging.info(f"[LOAD] File does not exist yet")
        return generated

    try:
        with open(numbers_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            logging.info(f"[LOAD] File has {len(lines)} lines total")

            reader = csv.DictReader(f)
            if reader is None or reader.fieldnames is None:
                logging.warning(f"[LOAD] Invalid CSV format in {numbers_path}")
                return generated

            for row in reader:
                if row is None:
                    continue
                number = str(row.get('number', '')).strip()
                if number and len(number) > 0:
                    generated.add(number)
                    logging.debug(f"[LOAD] Loaded number: {number}")

        logging.info(f"[LOAD] Successfully loaded {len(generated)} previously generated numbers")
        if len(generated) > 0:
            logging.info(f"[LOAD] First few: {sorted(list(generated))[:5]}")

    except Exception as e:
        logging.error(f"[LOAD] ERROR loading generated numbers: {type(e).__name__}: {e}")
        import traceback
        logging.error(f"[LOAD] Traceback: {traceback.format_exc()}")

    return generated


def _save_generated_number(base_dir: Path, number: str) -> None:
    """
    Save a generated article number to the tracking file.

    Args:
        base_dir: Base directory containing the data
        number: The generated number to save
    """
    numbers_path = _get_generated_numbers_path(base_dir)
    numbers_path.parent.mkdir(parents=True, exist_ok=True)

    logging.info(f"[SAVE] Attempting to save number: {number} to {numbers_path}")

    try:
        # Check if file exists and has more than just the header
        file_exists = numbers_path.exists()
        has_data = False

        if file_exists:
            try:
                with open(numbers_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    has_data = len(lines) > 1  # More than just header
                    logging.info(f"[SAVE] File exists with {len(lines)} lines, has_data={has_data}")
            except Exception as e:
                logging.error(f"[SAVE] Error reading file: {e}")
                has_data = False

        # Write to file (create if doesn't exist)
        mode = 'w' if not file_exists else 'a'
        logging.info(f"[SAVE] Opening file in mode '{mode}'")

        with open(numbers_path, mode, encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['number', 'timestamp'])

            # Write header if file is new
            if not file_exists:
                logging.info(f"[SAVE] Writing header to new file")
                writer.writeheader()

            # Write the generated number with timestamp
            import datetime
            timestamp = datetime.datetime.now().isoformat()
            logging.info(f"[SAVE] Writing row: number={number}, timestamp={timestamp}")
            writer.writerow({
                'number': number,
                'timestamp': timestamp
            })

        logging.info(f"[SAVE] Successfully saved number: {number}")

        # Verify write
        with open(numbers_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            logging.info(f"[SAVE] Verification: file now has {len(lines)} lines")
            if len(lines) > 1:
                logging.info(f"[SAVE] Last line: {lines[-1].strip()}")

    except Exception as e:
        logging.error(f"[SAVE] ERROR saving generated number {number}: {type(e).__name__}: {e}")
        import traceback
        logging.error(f"[SAVE] Traceback: {traceback.format_exc()}")
        raise


def _load_existing_numbers(base_dir: Path) -> Set[str]:
    """
    Load all existing article numbers from PROD, TEST, and majesty data.

    Args:
        base_dir: Base directory containing the data

    Returns:
        Set of existing article numbers in XX.YY.ZZZZ format
    """
    existing = set()

    # Paths to existing data
    prod_path = base_dir / "data" / "processed" / "cache" / "existing" / "existing_articles_PROD.csv"
    test_path = base_dir / "data" / "processed" / "cache" / "existing" / "existing_articles_TEST.csv"
    majesty_path = base_dir / "data" / "raw" / "artikelstamm" / "artikelstamm_majesty_2026_03_30.csv"

    # Load from PROD
    if prod_path.exists():
        try:
            with open(prod_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    artnr = str(row.get('artnr', '')).strip()
                    if artnr:
                        existing.add(artnr)
        except Exception as e:
            logging.warning(f"Error loading PROD numbers: {e}")

    # Load from TEST
    if test_path.exists():
        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    artnr = str(row.get('artnr', '')).strip()
                    if artnr:
                        existing.add(artnr)
        except Exception as e:
            logging.warning(f"Error loading TEST numbers: {e}")

    # Load from Majesty
    if majesty_path.exists():
        try:
            with open(majesty_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    artnr = str(row.get('artnr', '')).strip()
                    if artnr:
                        existing.add(artnr)
        except Exception as e:
            logging.warning(f"Error loading Majesty numbers: {e}")

    return existing


def _parse_formatted_number(number_str: str) -> Optional[tuple]:
    """
    Parse a number string in XX.YY.ZZZZ format.

    Args:
        number_str: Number string like "10.10.0001"

    Returns:
        Tuple of (xx, yy, zzzz) as integers, or None if format doesn't match
    """
    parts = number_str.split('.')
    if len(parts) != 3:
        return None

    try:
        xx = int(parts[0])
        yy = int(parts[1])
        zzzz = int(parts[2])

        # Validate ranges
        if 0 <= xx <= 99 and 0 <= yy <= 99 and 0 <= zzzz <= 9999:
            return (xx, yy, zzzz)
    except ValueError:
        pass

    return None


def _format_number(xx: int, yy: int, zzzz: int) -> str:
    """Format numbers into XX.YY.ZZZZ format."""
    return f"{xx:02d}.{yy:02d}.{zzzz:04d}"


def generate_article_number(
    base_dir: Path = None,
    prefix: str = ""
) -> str:
    """
    Generate the next available 8-digit article number in XX.YY.ZZZZ format.

    Skips existing numbers in PROD, TEST, and majesty data.
    Skips previously generated numbers (stored in generated_numbers.csv).
    Returns the lowest available number matching the prefix criteria.

    Args:
        base_dir: Base directory for the project (defaults to config parent)
        prefix: Optional prefix constraint. Examples:
                - "" (empty): Return lowest unused number starting from 00.00.0000
                - "10": Return lowest unused number starting with 10 (10.00.0000+)
                - "10.20": Return lowest unused number starting with 10.20 (10.20.0000+)
                - "10.20.5678": Return 10.20.5678 if available, else next in range

    Returns:
        Article number string in format XX.YY.ZZZZ

    Raises:
        ValueError: If prefix format is invalid or no numbers available
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent

    logging.info(f"[GENERATE] Starting number generation with prefix='{prefix}'")

    # Load all used numbers (existing + generated)
    existing = _load_existing_numbers(base_dir)
    logging.info(f"[GENERATE] Loaded {len(existing)} existing numbers")

    generated = _load_generated_numbers(base_dir)
    logging.info(f"[GENERATE] Loaded {len(generated)} previously generated numbers")

    used = existing | generated
    logging.info(f"[GENERATE] Total used numbers: {len(used)}")

    # Parse prefix to determine starting point
    prefix = prefix.strip() if prefix else ""

    if prefix == "":
        # No prefix: start from 00.00.0000
        start_xx, start_yy, start_zzzz = 0, 0, 0
    elif "." not in prefix:
        # Only first two digits: e.g., "10" -> 10.00.0000
        try:
            start_xx = int(prefix)
            if not (0 <= start_xx <= 99):
                raise ValueError(f"First part must be 0-99, got {start_xx}")
            start_yy, start_zzzz = 0, 0
        except ValueError as e:
            raise ValueError(f"Invalid prefix: {prefix}") from e
    else:
        # Full or partial: parse what we have
        parts = prefix.split('.')

        if len(parts) == 2:
            # XX.YY format
            try:
                start_xx = int(parts[0])
                start_yy = int(parts[1])
                start_zzzz = 0
                if not (0 <= start_xx <= 99) or not (0 <= start_yy <= 99):
                    raise ValueError(f"Parts must be 0-99, got {start_xx}.{start_yy}")
            except ValueError as e:
                raise ValueError(f"Invalid prefix: {prefix}") from e
        elif len(parts) == 3:
            # XX.YY.ZZZZ format
            try:
                start_xx = int(parts[0])
                start_yy = int(parts[1])
                start_zzzz = int(parts[2])
                if not (0 <= start_xx <= 99) or not (0 <= start_yy <= 99) or not (0 <= start_zzzz <= 9999):
                    raise ValueError(f"Invalid ranges in {prefix}")
            except ValueError as e:
                raise ValueError(f"Invalid prefix: {prefix}") from e

            # If full number specified, check if available
            candidate = _format_number(start_xx, start_yy, start_zzzz)
            if candidate not in used:
                _save_generated_number(base_dir, candidate)
                return candidate
            # If taken, fall through to find next available
        else:
            raise ValueError(f"Invalid prefix format: {prefix}")

    # Search for next available number
    max_iterations = 1_000_000  # Safety limit
    iterations = 0

    xx, yy, zzzz = start_xx, start_yy, start_zzzz

    while iterations < max_iterations:
        candidate = _format_number(xx, yy, zzzz)
        if candidate not in used:
            _save_generated_number(base_dir, candidate)
            return candidate

        # Increment: ZZZZ → YY → XX
        zzzz += 1
        if zzzz > 9999:
            zzzz = 0
            yy += 1
            if yy > 99:
                yy = 0
                xx += 1
                if xx > 99:
                    raise ValueError("No available article numbers (range exhausted)")

        iterations += 1

    raise ValueError(f"Failed to find available number after {max_iterations} attempts")


if __name__ == "__main__":
    # Example usage
    base_dir = Path(__file__).parent.parent

    print("Article Number Generation Examples:")
    print("-" * 50)

    # Test 1: No prefix - lowest available
    try:
        num = generate_article_number(base_dir)
        print(f"No prefix: {num}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Prefix "10"
    try:
        num = generate_article_number(base_dir, "10")
        print(f"Prefix '10': {num}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: Prefix "10.20"
    try:
        num = generate_article_number(base_dir, "10.20")
        print(f"Prefix '10.20': {num}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 4: Prefix "10.20.5678"
    try:
        num = generate_article_number(base_dir, "10.20.5678")
        print(f"Prefix '10.20.5678': {num}")
    except Exception as e:
        print(f"Error: {e}")



def _parse_formatted_number(number_str: str) -> Optional[tuple]:
    """
    Parse a number string in XX.YY.ZZZZ format.

    Args:
        number_str: Number string like "10.10.0001"

    Returns:
        Tuple of (xx, yy, zzzz) as integers, or None if format doesn't match
    """
    parts = number_str.split('.')
    if len(parts) != 3:
        return None

    try:
        xx = int(parts[0])
        yy = int(parts[1])
        zzzz = int(parts[2])

        # Validate ranges
        if 0 <= xx <= 99 and 0 <= yy <= 99 and 0 <= zzzz <= 9999:
            return (xx, yy, zzzz)
    except ValueError:
        pass

    return None


def _format_number(xx: int, yy: int, zzzz: int) -> str:
    """Format numbers into XX.YY.ZZZZ format."""
    return f"{xx:02d}.{yy:02d}.{zzzz:04d}"


def generate_article_number(
    base_dir: Path = None,
    prefix: str = ""
) -> str:
    """
    Generate the next available 8-digit article number in XX.YY.ZZZZ format.

    Skips existing numbers in PROD, TEST, and majesty data.
    Returns the lowest available number matching the prefix criteria.

    Args:
        base_dir: Base directory for the project (defaults to config parent)
        prefix: Optional prefix constraint. Examples:
                - "" (empty): Return lowest unused number starting from 00.00.0000
                - "10": Return lowest unused number starting with 10 (10.00.0000+)
                - "10.20": Return lowest unused number starting with 10.20 (10.20.0000+)
                - "10.20.5678": Return 10.20.5678 if available, else next available

    Returns:
        Article number string in format XX.YY.ZZZZ

    Raises:
        ValueError: If prefix format is invalid or no numbers available
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent

    # Load existing numbers
    existing = _load_existing_numbers(base_dir)

    # Parse prefix to determine starting point
    prefix = prefix.strip() if prefix else ""

    if prefix == "":
        # No prefix: start from 00.00.0000
        start_xx, start_yy, start_zzzz = 0, 0, 0
    elif "." not in prefix:
        # Only first two digits: e.g., "10" -> 10.00.0000
        try:
            start_xx = int(prefix)
            if not (0 <= start_xx <= 99):
                raise ValueError(f"First part must be 0-99, got {start_xx}")
            start_yy, start_zzzz = 0, 0
        except ValueError as e:
            raise ValueError(f"Invalid prefix: {prefix}") from e
    else:
        # Full or partial: parse what we have
        parts = prefix.split('.')

        if len(parts) == 2:
            # XX.YY format
            try:
                start_xx = int(parts[0])
                start_yy = int(parts[1])
                start_zzzz = 0
                if not (0 <= start_xx <= 99) or not (0 <= start_yy <= 99):
                    raise ValueError(f"Parts must be 0-99, got {start_xx}.{start_yy}")
            except ValueError as e:
                raise ValueError(f"Invalid prefix: {prefix}") from e
        elif len(parts) == 3:
            # XX.YY.ZZZZ format
            try:
                start_xx = int(parts[0])
                start_yy = int(parts[1])
                start_zzzz = int(parts[2])
                if not (0 <= start_xx <= 99) or not (0 <= start_yy <= 99) or not (0 <= start_zzzz <= 9999):
                    raise ValueError(f"Invalid ranges in {prefix}")
            except ValueError as e:
                raise ValueError(f"Invalid prefix: {prefix}") from e

            # If full number specified, check if available
            candidate = _format_number(start_xx, start_yy, start_zzzz)
            if candidate not in existing:
                return candidate
            # If taken, fall through to find next available
        else:
            raise ValueError(f"Invalid prefix format: {prefix}")

    # Search for next available number
    max_iterations = 1_000_000  # Safety limit
    iterations = 0

    xx, yy, zzzz = start_xx, start_yy, start_zzzz

    while iterations < max_iterations:
        candidate = _format_number(xx, yy, zzzz)
        if candidate not in existing:
            return candidate

        # Increment: ZZZZ → YY → XX
        zzzz += 1
        if zzzz > 9999:
            zzzz = 0
            yy += 1
            if yy > 99:
                yy = 0
                xx += 1
                if xx > 99:
                    raise ValueError("No available article numbers (range exhausted)")

        iterations += 1

    raise ValueError(f"Failed to find available number after {max_iterations} attempts")


if __name__ == "__main__":
    # Example usage
    base_dir = Path(__file__).parent.parent

    print("Article Number Generation Examples:")
    print("-" * 50)

    # Test 1: No prefix - lowest available
    try:
        num = generate_article_number(base_dir)
        print(f"No prefix: {num}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Prefix "10"
    try:
        num = generate_article_number(base_dir, "10")
        print(f"Prefix '10': {num}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: Prefix "10.20"
    try:
        num = generate_article_number(base_dir, "10.20")
        print(f"Prefix '10.20': {num}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 4: Prefix "10.20.5678"
    try:
        num = generate_article_number(base_dir, "10.20.5678")
        print(f"Prefix '10.20.5678': {num}")
    except Exception as e:
        print(f"Error: {e}")

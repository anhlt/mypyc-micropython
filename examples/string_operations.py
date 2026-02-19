"""String operations example module for mypyc-micropython.

Demonstrates string method support including:
- Concatenation and repetition
- Case transformations (upper, lower, capitalize, title, swapcase)
- Searching (find, rfind, index, rindex, count)
- Splitting and joining (split, rsplit, join)
- Stripping (strip, lstrip, rstrip)
- Replacement (replace)
- Checking (startswith, endswith)
- Padding (center, ljust, rjust, zfill)
- Partitioning (partition, rpartition)
"""


def concat_strings(a: str, b: str) -> str:
    """Concatenate two strings."""
    return a + b


def repeat_string(s: str, n: int) -> str:
    """Repeat a string n times."""
    return s * n


def to_upper(s: str) -> str:
    """Convert string to uppercase."""
    return s.upper()


def to_lower(s: str) -> str:
    """Convert string to lowercase."""
    return s.lower()


def capitalize_string(s: str) -> str:
    """Capitalize first character."""
    return s.capitalize()


def title_string(s: str) -> str:
    """Convert to title case."""
    return s.title()


def swapcase_string(s: str) -> str:
    """Swap case of all characters."""
    return s.swapcase()


def find_substring(s: str, sub: str) -> int:
    """Find first occurrence of substring."""
    return s.find(sub)


def rfind_substring(s: str, sub: str) -> int:
    """Find last occurrence of substring."""
    return s.rfind(sub)


def count_substring(s: str, sub: str) -> int:
    """Count occurrences of substring."""
    return s.count(sub)


def split_string(s: str) -> list:
    """Split string on whitespace."""
    return s.split()


def split_on_sep(s: str, sep: str) -> list:
    """Split string on separator."""
    return s.split(sep)


def join_strings(sep: str, items: list) -> str:
    """Join list of strings with separator."""
    return sep.join(items)


def strip_string(s: str) -> str:
    """Strip whitespace from both ends."""
    return s.strip()


def lstrip_string(s: str) -> str:
    """Strip whitespace from left end."""
    return s.lstrip()


def rstrip_string(s: str) -> str:
    """Strip whitespace from right end."""
    return s.rstrip()


def strip_chars(s: str, chars: str) -> str:
    """Strip specific characters from both ends."""
    return s.strip(chars)


def replace_string(s: str, old: str, new: str) -> str:
    """Replace occurrences of old with new."""
    return s.replace(old, new)


def starts_with(s: str, prefix: str) -> bool:
    """Check if string starts with prefix."""
    return s.startswith(prefix)


def ends_with(s: str, suffix: str) -> bool:
    """Check if string ends with suffix."""
    return s.endswith(suffix)


def center_string(s: str, width: int) -> str:
    """Center string in given width."""
    return s.center(width)


def ljust_string(s: str, width: int) -> str:
    """Left-justify string in given width."""
    return s.ljust(width)


def rjust_string(s: str, width: int) -> str:
    """Right-justify string in given width."""
    return s.rjust(width)


def zfill_string(s: str, width: int) -> str:
    """Pad numeric string with zeros on left."""
    return s.zfill(width)


def partition_string(s: str, sep: str) -> tuple:
    """Partition string at first occurrence of separator."""
    return s.partition(sep)


def rpartition_string(s: str, sep: str) -> tuple:
    """Partition string at last occurrence of separator."""
    return s.rpartition(sep)


def process_csv_line(line: str) -> list:
    """Process a CSV line by splitting on comma and stripping."""
    parts: list = line.split(",")
    result: list = []
    for part in parts:
        result.append(part.strip())
    return result


def normalize_text(text: str) -> str:
    """Normalize text: lowercase, strip, replace multiple spaces."""
    s: str = text.lower()
    s = s.strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def build_path(parts: list) -> str:
    """Build a path from parts using / separator."""
    return "/".join(parts)


def extract_extension(filename: str) -> str:
    """Extract file extension from filename."""
    idx: int = filename.rfind(".")
    if idx == -1:
        return ""
    return filename[idx + 1 :]


def format_number(n: int, width: int) -> str:
    """Format a number with leading zeros."""
    s: str = str(n)
    return s.zfill(width)

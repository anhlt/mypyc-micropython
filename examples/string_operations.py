def concat_strings(a: str, b: str) -> str:
    return a + b


def repeat_string(s: str, n: int) -> str:
    return s * n


def to_upper(s: str) -> str:
    return s.upper()


def to_lower(s: str) -> str:
    return s.lower()


def find_substring(s: str, sub: str) -> int:
    return s.find(sub)


def rfind_substring(s: str, sub: str) -> int:
    return s.rfind(sub)


def count_substring(s: str, sub: str) -> int:
    return s.count(sub)


def split_string(s: str) -> list[str]:
    return s.split()


def split_on_sep(s: str, sep: str) -> list[str]:
    return s.split(sep)


def join_strings(sep: str, items: list[str]) -> str:
    return sep.join(items)


def strip_string(s: str) -> str:
    return s.strip()


def lstrip_string(s: str) -> str:
    return s.lstrip()


def rstrip_string(s: str) -> str:
    return s.rstrip()


def strip_chars(s: str, chars: str) -> str:
    return s.strip(chars)


def replace_string(s: str, old: str, new: str) -> str:
    return s.replace(old, new)


def starts_with(s: str, prefix: str) -> bool:
    return s.startswith(prefix)


def ends_with(s: str, suffix: str) -> bool:
    return s.endswith(suffix)


def center_string(s: str, width: int) -> str:
    return s.center(width)


def partition_string(s: str, sep: str) -> tuple[str, str, str]:
    return s.partition(sep)


def rpartition_string(s: str, sep: str) -> tuple[str, str, str]:
    return s.rpartition(sep)


def process_csv_line(line: str) -> list[str]:
    parts: list[str] = line.split(",")
    result: list[str] = []
    for part in parts:
        result.append(part.strip())
    return result


def normalize_text(text: str) -> str:
    s: str = text.lower()
    s = s.strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def build_path(parts: list[str]) -> str:
    return "/".join(parts)


def extract_extension(filename: str) -> str:
    idx: int = filename.rfind(".")
    if idx == -1:
        return ""
    return filename[idx + 1 :]

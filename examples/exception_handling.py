def safe_divide(a: int, b: int) -> int:
    try:
        return a // b
    except ZeroDivisionError:
        return 0


def validate_positive(n: int) -> int:
    if n < 0:
        raise ValueError("must be positive")
    return n


def validate_range(n: int, min_val: int, max_val: int) -> int:
    if n < min_val:
        raise ValueError("too small")
    if n > max_val:
        raise ValueError("too large")
    return n


def with_cleanup(value: int) -> int:
    result: int = 0
    try:
        result = value * 2
    finally:
        result = result + 1
    return result


def multi_catch(a: int, b: int) -> int:
    try:
        if b == 0:
            raise ZeroDivisionError
        if a < 0:
            raise ValueError
        return a // b
    except ZeroDivisionError:
        return -1
    except ValueError:
        return -2


def try_else(a: int, b: int) -> int:
    result: int = 0
    try:
        result = a + b
    except ZeroDivisionError:
        result = -1
    else:
        result = result * 2
    return result


def full_try(a: int, b: int) -> int:
    result: int = 0
    try:
        result = a // b
    except ZeroDivisionError:
        result = -1
    finally:
        result = result + 100
    return result


def catch_with_binding(a: int, b: int) -> int:
    try:
        return a // b
    except ZeroDivisionError as e:
        return -1


def catch_all(value: int) -> int:
    try:
        if value < 0:
            raise ValueError
        if value > 100:
            raise TypeError
        return value
    except:
        return -1


def nested_try(a: int, b: int, c: int) -> int:
    try:
        try:
            return a // b
        except ZeroDivisionError:
            return b // c
    except ZeroDivisionError:
        return -1

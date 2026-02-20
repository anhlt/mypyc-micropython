def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i: int = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i = i + 2
    return True


def gcd(a: int, b: int) -> int:
    if b == 0:
        return a
    return gcd(b, a % b)


def lcm(a: int, b: int) -> int:
    return (a * b) // gcd(a, b)


def power(base: int, exp: int) -> int:
    if exp == 0:
        return 1
    if exp == 1:
        return base
    half: int = power(base, exp // 2)
    if exp % 2 == 0:
        return half * half
    return half * half * base

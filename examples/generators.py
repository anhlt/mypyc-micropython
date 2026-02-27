def countdown(n: int):
    while n > 0:
        yield n
        n -= 1


def squares(n: int):
    for i in range(n):
        yield i * i

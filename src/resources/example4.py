def select(cond, val1, val2):
    if cond:
        return val1
    return val2

result = select(True, 1, "hello")
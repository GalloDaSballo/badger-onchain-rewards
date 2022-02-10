# Assert approximate integer
def approx(actual, expected, max_treshhold):
    diff = int(abs(actual - expected))
    # 0 diff should automtically be a match
    if diff == 0:
        return True
    return diff <= max_treshhold
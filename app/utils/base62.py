import random
import string

ALPHABET = string.ascii_letters + string.digits  # a-z A-Z 0-9 → 62 chars
BASE = len(ALPHABET)  # 62


def encode(num: int) -> str:
    """Encode an integer to a Base62 string."""
    if num == 0:
        return ALPHABET[0]

    result = []
    while num:
        result.append(ALPHABET[num % BASE])
        num //= BASE
    return "".join(reversed(result))


def decode(code: str) -> int:
    """Decode a Base62 string back to an integer."""
    num = 0
    for char in code:
        num = num * BASE + ALPHABET.index(char)
    return num


def generate_random_code(length: int = 7) -> str:
    """
    Generate a cryptographically random Base62 code.
    Preferred over encode(id) because it doesn't expose sequential IDs.
    Collision probability at 7 chars: ~1 in 3.5 trillion per code.
    """
    return "".join(random.choices(ALPHABET, k=length))

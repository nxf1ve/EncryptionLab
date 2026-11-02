"""Учебная реализация Магмы и CFB-64 (регистр 128 бит)."""
import hashlib
import os
from pathlib import Path

# Pi_0 применяется к младшей тетраде, Pi_7 — к старшей.
SBOX = (
    (12,4,6,2,10,5,11,9,14,8,13,7,0,3,15,1),
    (6,8,2,3,9,10,5,12,1,14,4,7,11,13,0,15),
    (11,3,5,8,2,15,10,13,14,1,7,4,12,9,6,0),
    (12,8,2,1,13,4,15,6,7,0,10,5,3,14,9,11),
    (7,15,5,10,8,1,6,13,0,9,3,14,11,4,2,12),
    (5,13,15,6,9,2,12,10,11,7,8,1,4,3,14,0),
    (8,14,2,5,6,9,1,12,15,4,11,0,13,10,3,7),
    (1,7,14,13,0,5,8,3,4,15,10,6,9,12,11,2),
)
MASK = 0xffffffff
MAGIC = b'MAGLAB2\x00'  # Метка формата учебной версии
HEADER_SIZE = 24  # Метка (8 байт) и IV (16 байт)

def substitute(value):
    """Восемь независимых замен 4 -> 4 бита."""
    result = 0
    for i in range(8):
        nibble = (value >> (4 * i)) & 15
        replacement = SBOX[i][nibble]
        result |= replacement << (4 * i)
    return result

def round_function(value, key):
    value = substitute((value + key) & MASK)
    return ((value << 11) | (value >> 21)) & MASK

class Magma:
    def __init__(self, key):
        if len(key) != 32:
            raise ValueError('Ключ должен содержать 32 байта')
        words = [int.from_bytes(key[i:i+4], 'big') for i in range(0,32,4)]
        self.keys = words * 3 + words[::-1]

    def encrypt_block(self, block):
        if len(block) != 8:
            raise ValueError('Блок должен содержать 8 байт')
        left = int.from_bytes(block[:4], 'big')
        right = int.from_bytes(block[4:], 'big')
        for key in self.keys[:-1]:
            left, right = right, left ^ round_function(right, key)
        # Последний раунд выполняется без обмена половин.
        left ^= round_function(right, self.keys[-1])
        return left.to_bytes(4,'big') + right.to_bytes(4,'big')

class CFB:
    def __init__(self, key, iv, decrypt=False):
        if len(iv) < 8 or len(iv) % 8:
            raise ValueError('IV должен иметь длину, кратную 8 байтам')
        self.cipher = Magma(key)
        self.register = iv
        self.decrypt = decrypt

    def process(self, block):
        """Один сегмент 1..8 байт; неполный сегмент допустим только последним."""
        if not 1 <= len(block) <= 8:
            raise ValueError('Сегмент должен содержать 1..8 байт')
        gamma = self.cipher.encrypt_block(self.register[:8])
        result = bytes(a ^ b for a,b in zip(block,gamma))
        feedback = block if self.decrypt else result
        self.register = self.register[len(block):] + feedback
        return result

def transform_file(source, destination, password, decrypt=False):
    """Прочитать файл, обработать сегменты CFB, записать результат."""
    source = Path(source)
    destination = Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Выберите для результата другой файл')
    if not password:
        raise ValueError('Введите пароль')

    # Учебный способ получить 256-битный ключ из пароля.
    # SHA-256 здесь не часть Магмы и не защита от перебора пароля.
    key = hashlib.sha256(password).digest()
    data = source.read_bytes()
    if decrypt:
        if len(data) < HEADER_SIZE or data[:8] != MAGIC:
            raise ValueError('Это не файл учебной версии Магмы')
        iv = data[8:24]
        data = data[24:]
    else:
        iv = os.urandom(16)

    mode = CFB(key, iv, decrypt)
    result = bytearray()
    for i in range(0, len(data), 8):
        block = data[i:i + 8]
        result.extend(mode.process(block))

    # При расшифровании заголовок повторно не записывается.
    if not decrypt:
        result = MAGIC + iv + result
    # Режим xb защищает от случайной перезаписи существующего файла.
    with destination.open('xb') as output:
        output.write(result)

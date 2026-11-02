"""Контрольные векторы и проверки файлового контейнера."""
import tempfile
import unittest
from pathlib import Path
from magma import Magma, CFB, transform_file, substitute

KEY = bytes.fromhex('ffeeddccbbaa99887766554433221100f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff')

class Tests(unittest.TestCase):
    def test_rfc8891(self):
        self.assertEqual(substitute(0xfdb97531),0x2a196f34)
        self.assertEqual(Magma(KEY).encrypt_block(bytes.fromhex('fedcba9876543210')).hex(),'4ee901e5c2d8ca3d')

    def test_gost_cfb(self):
        iv = bytes.fromhex('1234567890abcdef234567890abcdef1')
        plain = bytes.fromhex('92def06b3c130a59db54c704f8189d204a98fb2e67a8024c8912409b17b57e41')
        expected = bytes.fromhex('db37e0e266903c830d46644c1f9a089c24bdd2035315d38bbcc0321421075505')
        for decrypt,source,target in [(False,plain,expected),(True,expected,plain)]:
            mode = CFB(KEY,iv,decrypt)
            self.assertEqual(b''.join(mode.process(source[i:i+8]) for i in range(0,len(source),8)),target)

    def test_files(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for size in [0,1,7,8,9,1024,65539]:
                data = bytes(i % 256 for i in range(size))
                src,enc,dec = [base / f'{size}.{ext}' for ext in ['bin','magma','restored']]
                src.write_bytes(data)
                transform_file(src,enc,b'password')
                transform_file(enc,dec,b'password',True)
                self.assertEqual(dec.read_bytes(),data)
                self.assertEqual(enc.stat().st_size,size+24)
            enc = base/'1024.magma'
            bad = base/'bad.bin'
            # В CFB нет проверки пароля: результат сохраняется, но не совпадает.
            transform_file(enc,bad,b'wrong',True)
            self.assertNotEqual(bad.read_bytes(), (base/'1024.bin').read_bytes())
            invalid = base/'invalid.magma'
            invalid.write_bytes(b'not a magma file')
            with self.assertRaises(ValueError):
                transform_file(invalid,base/'unused.bin',b'password',True)
            self.assertFalse((base/'unused.bin').exists())
            with self.assertRaises(ValueError):
                transform_file(src,base/'empty.bin',b'')
            with self.assertRaises(ValueError): transform_file(src,src,b'password')
            with self.assertRaises(FileExistsError): transform_file(src,dec,b'password')
            self.assertEqual(len(list(base.glob('tmp*'))),0)

if __name__ == '__main__': unittest.main(verbosity=2)

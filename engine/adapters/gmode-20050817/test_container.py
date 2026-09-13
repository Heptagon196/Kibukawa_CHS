import io
import struct
import unittest
import zipfile
from container import scenarios


def fixture(version=b'20050817', labels=(0,), declared_size=None):
    payload = version + b'\0\0\0' + struct.pack('<H', len(labels))
    payload += b''.join(struct.pack('<H', n) for n in labels) + b'\x22\0'
    raw = b'\xff\xff' + struct.pack('<H', len(payload) if declared_size is None else declared_size) + payload
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('test.bin', raw)
    jar = output.getvalue()
    return b'\x01test.jar\0' + struct.pack('>HH', 0, len(jar)) + jar


class ContainerTests(unittest.TestCase):
    def test_scenario_boundaries(self):
        result = scenarios(fixture())[0]
        self.assertEqual(result['script'], b'\x22\0')
        self.assertEqual(result['labels'], [0])
        self.assertEqual(result['raw'][result['script_offset']:], result['script'])

    def test_rejects_corrupt_inputs(self):
        for data in [fixture()[:-1], fixture()+b'\0', fixture(version=b'20050818'),
                     fixture(labels=(3,)), fixture(declared_size=1)]:
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                scenarios(data)


if __name__ == '__main__':
    unittest.main()

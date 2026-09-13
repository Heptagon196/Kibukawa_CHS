import struct
import unittest
from container import entries, scenario_names, scenarios


def fixture(members=((b'c5_00.bin', b'20050117\0\0\0\0\0'), (b'bg00.jpg', b'\xff\xd8'))):
    data = bytearray([len(members)])
    table = b''
    offset = 0
    for name, payload in members:
        table += name + b'\0' + struct.pack('>HH', offset % 65536, len(payload))
        offset += len(payload)
    for _, payload in members:
        data += payload
    return bytes(data[:1]) + table + bytes(data[1:])


class ContainerTests(unittest.TestCase):
    def test_member_boundaries(self):
        result = entries(fixture())
        self.assertEqual([name for name, _ in result], ['c5_00.bin', 'bg00.jpg'])
        self.assertEqual(result[0][1], b'20050117\0\0\0\0\0')
        self.assertEqual(result[1][1], b'\xff\xd8')

    def test_scenario_filtering(self):
        self.assertEqual(scenario_names(fixture()), ['c5_00.bin'])
        self.assertEqual([item['raw'] for item in scenarios(fixture())], [b'20050117\0\0\0\0\0'])

    def test_rejects_corrupt_inputs(self):
        good = fixture()
        cases = {
            'empty': b'',
            'truncated': good[:-1],
            'trailing': good + b'\0',
            'count': bytes([9]) + good[1:],
            'offset': good[:len(good) - 4].replace(b'\0\x02', b'\0\x03', 1),
            'duplicate': fixture(((b'a.bin', b'x'), (b'a.bin', b'y'))),
            'path': fixture(((b'dir/a.bin', b'x'),)),
        }
        for label, data in cases.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                entries(data)


if __name__ == '__main__':
    unittest.main()

"""Content fingerprints for QA exceptions that were reviewed in context.

An exception is accepted only while both its source and translation are byte-for-byte
identical to the reviewed pair.  Editing either side makes the release gate ask for a
new review instead of silently carrying the exception forward.
"""

# These translations deliberately restructure an ellipsis rather than losing a pause.
# Values are sha256(source + "\0" + target).
ELLIPSIS = {
    'scratch4.dat/s01:17265': '0a4dcdae22b657889c236df4261e47bf376fc85dd81957791efdf9a6a6bcfa14',
    'scratch4.dat/s01:18433': '569d96884185b07944f23d4eafd027e5d2ac6f97cb17ab7f44e302071bf5c669',
    'scratch4.dat/s01:21531': '8eb06c0be41176f5956f6a016e781970634e8340f9a857cf454d3c8a34857822',
    'scratch4.dat/s01:39877': 'b5e1f457b660f577ca79b59d7a0f63279584f4a55fc39ca8b4ef931607c5657d',
    'scratch4.dat/s01:43679': '29c3c74f45c7a7e442f349d123f8ae044cd3058b2760b1a0d364d585ad38b508',
    'scratch4.dat/s01-1:538': '09ef7f2d3b3bc47c7ab7c975e34a6f253095fd7fabfa0fda121d29b6f0d79d66',
    'scratch4.dat/s01-1:10121': '2156c996d4437c8f9deaa791e8b70621739a1d85467932c2d296459d83cdb5d5',
    'scratch4.dat/s01-1:14798': '996de01d63ffd0a33dead39042dc5c8979f9c7cbff85d84e23f77b839bc16a33',
    'scratch4.dat/s01-1:16552': '028ad7433e4008abbc3fb73cadcd7f58a069c77f66591d3ee895fd48b75960eb',
    'scratch4.dat/s02:6332': 'e39dd16575d95d0771ca8ece6e69ab3e8c59bbe21686a396f0df692d92dfcf84',
    'scratch4.dat/s02:12616': '4f4e7f388677402265301b033f29ce348e281d523c12d29a3f65cce71cc74ab9',
    'scratch4.dat/s02:13519': '95e2eefcd3833e6118a865cfb6d88e31dcf0fae5e21cda058fad6c36f40e2b01',
    'scratch4.dat/s02:18177': 'ba3273acecac25c8f68dd69b8de33484aa7e5a906c7667ef3c3d4099f0c5b56a',
    'scratch4.dat/s02:18344': 'b65f7a1c01489ccb383435504366207b24d21b07e954f0cf85d09c9f8d7a7215',
    'scratch4.dat/s02:27798': '9b459303c4c342f8ed53afc5fddcf85cd29f2a8dfbd8487c0391b4d759ac5406',
    'scratch4.dat/s02:38975': 'cfe3d8a5cdf336d109650078c2b4da7c4d527d9b0d4d7350efc9d62ed15b4820',
    'scratch4.dat/s02:42484': 'be303c71ba6749526d831ba2855599f41adda15d54b04894c47a3f1afe3af38d',
    'scratch4.dat/s04-1:886': 'ecb1eeb103c04032c601665ff9b52e02c9cbca29a93695ff2a188e01efe61ebc',
    'scratch4.dat/s04-1:4674': '30e585f6a92c19267464669b576c86805667c9b2116176d0bd078bcd97c4d33c',
    'scratch4.dat/s05:3439': '73b35b878d1c3b08d9d4ed9608c9dc88040bc7888105636cc1ac4484079bd142',
    'scratch4.dat/s05:8864': '3e1984c82759556d3da2395db4adb12389d25227b93f249f6df74d5068dd11f0',
    'scratch4.dat/s05:20878': 'eca3295cbfa56bed0c256f680b8b6c4106da1001feaf03cf2a6d4892a849cd36',
    'scratch4.dat/s07:3453': '2e84f56756c82e803bf7d6c0f26b1d587beac18735559d5593b5310016eacae7',
    'scratch4.dat/s07:5436': '0ec1576868ea9cc041c2b150d91279fa63579146c1206022d59a364db1687e2d',
    'scratch4.dat/s11:1108': '7fa722f81aa35eaec4c7015603e7209256db5147b9cae3a454015e81a8c0b192',
    'scratch4.dat/s11:12019': 'a4226d4a268e4e3c178b3c2bd5469197b3a35be73e3f4927296be08a1170a781',
    'scratch4.dat/s11:13451': '72de4556fbc0ac8c9d79c2a6820140f52aecfd8144949a25bfd68e0c36d8905d',
    'scratch4.dat/s12:6398': '6b1866196cdd601b7870f3f536b7fc0cedced5c854a7cf35c069ae8ed37085c9',
    'scratch4.dat/s12:7217': '08f90af56529059b8ce58ca0e9c4cd6c9417f1cfd28506c83a6e10f58193fc65',
    'scratch4.dat/s12:7680': '4f7a1da2c91d2ed9974e85661b5d768110de57e3f3c86d4e6e535d15642e6747',
    'scratch4.dat/s12:10631': '4f05c7f5cdf7b5eb251328c6b9640ea1f0ce9c73e0aafabe76c293438a1bf364',
    'scratch4.dat/s12:12492': 'ea18a035eb094f5ea79c03cbd97247815486aaab6c384e2cc57420f0fc9d0917',
    'scratch4.dat/s12:20863': 'bdce4355238053d497cb2bbd85fa70365b5cda335222e12faed0cde168b37242',
    'scratch4.dat/s12:21243': '26cb0bd50ab57f6698a72f460766c26e449dd180a6dfd4773dd7d6727f4bce59',
    'scratch4.dat/s12:30776': 'f2ca631940e8f453ba67e76635e523f7a592a0f3efedc8286cf321b6acb646f1',
    'scratch4.dat/s21:14322': 'a689ac6d6076c363a0f7eac6b0a7b9b809cc36e80e1bd5ac14f6321ad073e50d',
    'scratch4.dat/s23:9721': '1f888287a7865b9e775cd3ca3da71c0c62aecaac213d4dfd7d1b966bb3c232b0',
    'scratch4.dat/s25:5760': 'bad815130960f4899cb398e699e0df381ba7a0b158071fdff6347bb6538b6126',
    'scratch4.dat/s27:9265': '7863a307a39439842c65b58a768e56ce664bbbbe9fbff814076528d396430179',
    'scratch4.dat/s31:4748': 'b73bf26bdba0d37b7e429ef932a3aeda1d9a9c6429a1f140be2d444e455941de',
    'scratch4.dat/s33:13669': '0553dda41f66e9092c915af0216f9dc2a050abb077aaf6ce315633bd08986a92',
    'scratch4.dat/s35:15130': '55e808512a3b33d83fad2d68365e5183a4428ec60f9c16b8f89ecf6d02193831',
    'scratch4.dat/s35-1:44357': 'd8f1673e78b17c277633c72afc81f7f41f4a3d57ca48d5ba8ba167bba81cb9df',
    'scratch4.dat/s35-2:12822': '75bec49ad12cbf0dcf18bfa23953f10035fd9221893cdee8024eefb17f68e8ee',
    'scratch4.dat/s35-2:46644': '7eb8a6a5e1adce3b11a0dc2f2a5517ec622d144c9bfcdb912dbde89ce510a39d',
    'scratch4.dat/s36:23646': '498a08ff7960d972d539939cd470140717486df905a1ef7298e0e2ddd2f6d15d',
    'scratch4.dat/s36:36360': '517a0b25c6cef55ab294c7fee75ef9492ea6fa9049a7de8a83003710f8174411',
    'scratch4.dat/s37:1858': '6d96158f604a7eb8cc8f4472592b7430b7741dac644e20dcdaca51164cc27425',
    'scratch4.dat/s37:13854': '1deb04f67483ebbd002232cbc30527e565ffb0d1b4fb36027f61762470855fca',
    'file/append:5843': '97ef71440412ad4a66ff3f28ba89c5a193a5df897d981c02b249b09f02e3228e',
    'file/append:5998': '97ef71440412ad4a66ff3f28ba89c5a193a5df897d981c02b249b09f02e3228e',
    'file/help:3156': '14b9e6629caef13b8f04dc18698131b41370b4635ff2d98fac91acb1ba188840',
}

# Chinese punctuation was deliberately moved into these highlighted clauses.
# All other newly highlighted terminal punctuation must be reviewed.
COLOR_PUNCTUATION = {
    'scratch4.dat/s01:20739:token2': '89919dd20e34423c517349d36cbd5027a5c94d1dbd6c0360d1d37e9866baa6de',
    'scratch4.dat/s01:20739:token8': '600f363fae10a5e9d988dcdead73a5bfdc67da7532e9ae3e67d2395d51659a4d',
    'scratch4.dat/s01:20739:token14': '4f2c4633126d7822a9df7201005899e471c5846c86e56715819e3b946fd74a60',
    'scratch4.dat/s03:21394:token6': '70bb5f83189e384db8bda5c03283ceb7e00ca29428c706d67ca468d008782c17',
    'scratch4.dat/s12:8027:token6': '036afbd2b6782c9aa9d162cb52e0d63d36375afa1a0b2a158017cdab72db8897',
    'scratch4.dat/s12:32565:token8': '75c7f423bc661c94c69cf918c4ac21daca1ae3d9d26126f1627e283dca60ddc8',
    'scratch4.dat/s27:20252:token6': '2116fe4aff600abcd8ee4d7dd9c67e75caa36608714f67c41c66c3bc31751b92',
    'scratch4.dat/s34:10089:token8': 'f60105062124c7dfc3c08f7d83fd742459538f1fb32c3f59059958648d909c7c',
    'scratch4.dat/s34:10280:token8': '6b01f69935c8d1f128eb4b3f8126396cff931f1f624ac9cfcfba2c41881f83d3',
    'scratch4.dat/s36:27692:token6': '6177b3982e425d02d2d06f7e7bb82b396dc60c7911b8482c1346c18c49dab6c2',
}

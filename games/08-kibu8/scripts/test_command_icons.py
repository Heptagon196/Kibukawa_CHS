"""Approved 10px artwork regression: all ten native action pairs."""
import hashlib, io, unittest, zipfile
from PIL import Image
import pipeline as p
from build_pixel_font import dependency, parse_bdf
from build_command_icons import LABELS, resolve_asset
from command_icons import render_command
from image_resources import scratch_resources

EXPECTED = ['776bf4657299ec7a0a9a84c073db41aee474fea862d50a4f14e9bc293b170384', 'bbef9c8a9da7f7ccf6c51db6c069d071010467eef2444d7364a4b8d0c5c20033', '52ef231ca05a022a51475573ddc419e64b870a0efcdd63209ca770ec0132b259', '4029c5be22c5e42e5b93f2ebca3a23f3fca095d93e336b8cdd755d14271d4903', '0e6248196d1ccd58fd379f36e315f057d75fc143279f7b8ce304ff6fc9ef1910', '37bde2dcac7abaa98d544b3421f83d20917961eb00b7c95144e014176ce8bd8e', '671f235c184b3f5beb4903dcb15677a612f63ced6be0ca3edda769ef9731b531', 'ec4e79cf73c6fd338e48ffeebf59325a34d60928079f2e63384b686a87e69887', '8333dae9ba53454b1fee9126d8ba42e909d8bf05a694e5a3e3df68241940ef03', 'cc690f8f495d47f6261d198e495d705629a5e9990fba6a56d052130c05226d47']

class ApprovedCommands(unittest.TestCase):
    def test_all_twenty_states(self):
        lock=p.load(p.WORK/'bepinex/fusion-icon-font-dependency.lock.json')
        with zipfile.ZipFile(dependency(lock['dependencies']['bdf'])) as archive:
            glyphs=parse_bdf(archive.read('fusion-pixel-10px-monospaced-zh_hans.bdf'),(5,10))
        sources=scratch_resources(p.GAME/'kibu8_Data/StreamingAssets/scratchpad')
        blank=Image.open(resolve_asset('classic-240/command-backgrounds')[0]).convert('RGBA')
        for i,label in enumerate(LABELS):
            with self.subTest(button=i):
                source=Image.open(io.BytesIO(sources[f'cmd{i}.gif'])).convert('RGBA')
                x=(i%2)*48;y=(i//2)*24
                image=render_command(source,blank.crop((x,y,x+48,y+24)),label,glyphs)
                self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(),EXPECTED[i])

if __name__=='__main__':unittest.main()

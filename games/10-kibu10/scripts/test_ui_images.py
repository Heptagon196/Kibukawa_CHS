"""Real asset and IL checks for named-resource coverage and title animation."""
import unittest,sys,json,struct
from PIL import Image
import pipeline as p
from inspect_image_coverage import resource_inventory
from build_ui_images import build,MENUS,NATIVE_NAMEPLATES,NATIVE_STATUS_LABELS

class ImageTests(unittest.TestCase):
    def test_character_nameplates_retain_complete_native_images(self):
        routes=build()
        self.assertFalse(set(NATIVE_NAMEPLATES)&{entry['id'] for entry in routes})
        for key in NATIVE_NAMEPLATES:
            self.assertFalse((p.WORK/'images/ui'/(key+'.png')).exists())
        evidence=p.load(p.WORK/'images/ui-labels.reviewed.json')
        self.assertEqual({item['id'] for item in evidence['native_nameplates']},set(NATIVE_NAMEPLATES))
        self.assertTrue(all(item['disposition']=='retain_complete_native_image' for item in evidence['native_nameplates']))

    def test_completed_badge_retains_complete_native_image(self):
        routes=build()
        self.assertFalse(set(NATIVE_STATUS_LABELS)&{entry['id'] for entry in routes})
        for key in NATIVE_STATUS_LABELS:
            self.assertFalse((p.WORK/'images/ui'/(key+'.png')).exists())
        evidence=p.load(p.WORK/'images/ui-labels.reviewed.json')
        self.assertEqual({item['id'] for item in evidence['native_status_labels']},set(NATIVE_STATUS_LABELS))
        self.assertTrue(all(item['disposition']=='retain_complete_native_image' for item in evidence['native_status_labels']))

    def test_menu_background_is_preserved_from_whole_master(self):
        from build_title_components import compose
        from title_art_parts import MASTER
        out=compose()
        master=Image.open(MASTER).convert('RGBA').resize((240,240),Image.Resampling.LANCZOS)
        for name in ('title1-zh.png','title2-zh.png','title-scratch-zh.png'):
            actual=Image.open(out/name).convert('RGBA')
            self.assertEqual(actual.crop((27,34,103,125)).tobytes(),master.crop((27,34,103,125)).tobytes(),name)

    def test_all_15_panels_preserve_pixels_outside_selected_lettering(self):
        from build_title_panels import build as panels,menu_mask,PANEL_BOX,KEYS
        from title_art_parts import MASTER
        files=panels()
        self.assertEqual(len(files),15)
        base=Image.open(MASTER).convert('RGBA').resize((240,240),Image.Resampling.LANCZOS).crop(PANEL_BOX)
        for selected,key in enumerate(KEYS):
            mask=menu_mask(key)
            for state in range(5):
                panel=Image.open(p.WORK/f'images/ui/title-panel-{selected}-{state}.png').convert('RGBA')
                self.assertEqual(panel.size,base.size)
                self.assertEqual(panel.getchannel('A').getextrema(),(255,255))
                changed=0
                for y in range(base.height):
                    for x in range(base.width):
                        if mask.getpixel((x,y))==0:self.assertEqual(panel.getpixel((x,y)),base.getpixel((x,y)))
                        elif panel.getpixel((x,y))!=base.getpixel((x,y)):changed+=1
                self.assertGreater(changed,0)

    def test_resource_routes_are_real_and_have_native_dimensions(self):
        native=resource_inventory()
        for entry in build():
            name='/'+entry['id']+'.gif'
            self.assertEqual(native[name]['size'],entry['size'])
            with Image.open(p.WORK/'images'/entry['png']) as image:
                self.assertEqual(list(image.size),entry['size'])

    def test_all_five_title_animation_states_have_identical_size_and_opaque_background(self):
        build()
        for name,(_,size) in MENUS.items():
            for suffix in ('','-900','-700','-500','-400','-0'):
                with Image.open(p.WORK/'images/ui'/(name+suffix+'.png')) as im:
                    self.assertEqual(im.size,size)
                    self.assertEqual(im.getchannel('A').getextrema(),(255,255))

    def test_title_sources_and_dimmed_loaders_match_actual_il(self):
        methods=p.load(p.WORK/'research/kibu10-assembly.json')['methods']
        il=methods['System.Void CanvasEx::Game_title()']['il']
        self.assertIn('ldstr /title1.gif',il);self.assertIn('ldstr /title2.gif',il)
        for name in MENUS:
            self.assertEqual(il.count('ldstr resource:///'+name+'.gif.bytes'),4)
        dim=methods['Socotra.UI.Image CanvasEx::LoadGraphic2(System.String,System.Int32)']['il']
        self.assertIn('ldc.i4 1024',dim)

    def test_title_variants_share_identical_master_pixels_and_no_bg21_override(self):
        from build_title_components import compose
        out=compose()
        titles=[Image.open(out/name).convert('RGBA') for name in ('title1-zh.png','title2-zh.png','title-scratch-zh.png')]
        for y in range(220):
            for x in range(240):
                if 84<=x<109 and 173<=y<220:continue
                self.assertEqual(len({im.getpixel((x,y)) for im in titles}),1)
        self.assertNotIn('Add("bg21.jpg"',(p.WORK/'bepinex/images/NativeArtwork.cs').read_text('utf-8'))

    def test_help_translation_is_complete(self):
        spec=p.load(p.WORK/'images/help-pages.translation.json')
        self.assertEqual(len(spec['pages']),4)
        for page in spec['pages'][:2]:
            self.assertEqual(len(page['translation']['rows']),5)
            self.assertEqual(page['translation']['rows'][-1][1],'游戏菜单')

    def test_all_decoded_assets_have_review_disposition(self):
        inventory=p.load(p.WORK/'images/inventory/inventory.json')
        coverage=p.load(p.WORK/'images/coverage.reviewed.json')
        self.assertEqual([(x['id'],x['sha']) for x in inventory],[(x['id'],x['source_rgba_sha256']) for x in coverage['images']])
        self.assertTrue(all(x['disposition'] for x in coverage['images']))

if __name__=='__main__':unittest.main()

import io, unittest
from PIL import Image
from image_compression import compress_image, THRESHOLD

class CompressionTests(unittest.TestCase):
    def encode(self, image, fmt='PNG', **kw):
        out=io.BytesIO(); image.save(out,fmt,**kw); return out.getvalue()

    def test_threshold(self):
        for n in (0, THRESHOLD-1, THRESHOLD):
            data=b'x'*n
            self.assertEqual(compress_image(data),(data,''))

    def test_png_pixels_alpha_and_text(self):
        from PIL.PngImagePlugin import PngInfo
        metadata=PngInfo(); metadata.add_text('note','Readable text')
        image=Image.new('RGBA',(1000,1000),(20,40,60,120))
        data=self.encode(image,compress_level=0,pnginfo=metadata)
        result,note=compress_image(data)
        self.assertLess(len(result),len(data)); self.assertTrue(note)
        with Image.open(io.BytesIO(result)) as decoded:
            self.assertEqual(decoded.tobytes(),image.tobytes())
            self.assertEqual(decoded.info['note'],'Readable text')

    def test_jpeg_dimensions_orientation_profile(self):
        image=Image.effect_noise((1600,1600),70).convert('RGB')
        exif=Image.Exif(); exif[274]=6
        data=self.encode(image,'JPEG',quality=100,subsampling=0,exif=exif,icc_profile=b'test-profile')
        result,_=compress_image(data)
        self.assertLess(len(result),len(data))
        with Image.open(io.BytesIO(result)) as decoded:
            self.assertEqual(decoded.size,image.size)
            self.assertEqual(decoded.getexif()[274],6)
            self.assertEqual(decoded.info['icc_profile'],b'test-profile')
            from PIL.JpegImagePlugin import get_sampling
            self.assertEqual(get_sampling(decoded),0)

    def test_animation_and_corrupt(self):
        image=Image.new('RGB',(600,600),'red')
        data=self.encode(image,save_all=True,append_images=[Image.new('RGB',(600,600),'blue')],compress_level=0)
        self.assertGreater(len(data),THRESHOLD)
        self.assertEqual(compress_image(data)[0],data)
        data=b'broken'*(THRESHOLD//6+1)
        self.assertEqual(compress_image(data)[0],data)

    def test_no_growth_and_unsupported(self):
        image=Image.new('RGB',(1000,1000),'white')
        data=self.encode(image,'BMP')
        self.assertEqual(compress_image(data)[0],data)
        data=self.encode(image,compress_level=9)+b'\0'*THRESHOLD
        result,_=compress_image(data)
        self.assertLessEqual(len(result),len(data))

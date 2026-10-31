"""Conservative, in-memory image optimization; never resize or overwrite originals."""
import io
import pathlib
import sys
import warnings

THRESHOLD = 1_000_000  # decimal MB, not MiB


def compress_image(data):
    """Return (bytes, note). Keep format, pixels, alpha, orientation and profiles.

    Unsupported, animated, multi-page or unsafe images pass through unchanged.
    JPEG is deliberately not chased down to a byte target: text matters more.
    """
    if len(data) <= THRESHOLD:
        return data, ''
    if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')
            or (data.startswith(b'RIFF') and data[8:12] == b'WEBP')):
        return data, ''
    # Import only for large images; the installer keeps Pillow inside the bundle.
    vendor = str(pathlib.Path(__file__).resolve().parent / 'vendor')
    if vendor not in sys.path: sys.path.insert(0, vendor)
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        return data, 'сжатие недоступно: переустановите действие'
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                fmt = image.format
                if fmt not in ('PNG', 'JPEG', 'WEBP') or getattr(image, 'n_frames', 1) != 1:
                    return data, ''
                # Do not silently reduce 16-bit PNG or unusual color modes.
                if image.mode not in ('1', 'L', 'LA', 'P', 'RGB', 'RGBA', 'CMYK'):
                    return data, ''
                image.load()
                options = {}
                for key in ('icc_profile', 'exif'):
                    if image.info.get(key): options[key] = image.info[key]
                if fmt == 'PNG':
                    from PIL.PngImagePlugin import PngInfo
                    metadata = PngInfo()
                    for key, value in image.info.items():
                        if isinstance(value, str): metadata.add_itxt(key, value)
                    options.update(optimize=True, pnginfo=metadata)
                    for key in ('transparency', 'dpi'):
                        if key in image.info: options[key] = image.info[key]
                elif fmt == 'JPEG':
                    options.update(quality=95, subsampling=0, optimize=True)
                    if image.info.get('dpi'): options['dpi'] = image.info['dpi']
                else:
                    options.update(lossless=True, method=6, exact=True)
                out = io.BytesIO()
                image.save(out, format=fmt, **options)
                result = out.getvalue()
                if len(result) < len(data):
                    return result, f'{len(data):,} → {len(result):,} байт (−{100 - len(result)*100//len(data)}%)'
                return data, 'исходник уже компактнее; оставлен без изменений'
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return data, 'изображение оставлено без изменений (формат или безопасный лимит)'

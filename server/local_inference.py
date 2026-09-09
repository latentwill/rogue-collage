"""CPU-only image operations; no artwork is sent to a remote service."""
import importlib.util
import io
import math
import os
import threading
from pathlib import Path

_session = None
_lock = threading.Lock()


def model_directory(data):
    return Path(data) / 'models' / 'rembg'


def model_cached(data):
    directory = model_directory(data)
    return any(p.is_file() for p in (directory / 'u2net.onnx', directory / 'models' / 'u2net' / 'u2net.onnx'))


def status(data):
    installed = all(importlib.util.find_spec(p) for p in ('rembg', 'onnxruntime', 'PIL'))
    cached = model_cached(data)
    return {'installed': bool(installed), 'cutout_ready': bool(installed and cached),
            'upscale_ready': importlib.util.find_spec('PIL') is not None,
            'model': 'U²-Net', 'model_download_mb': 176,
            'message': ('CPU tools installed. Background removal is ready.' if cached else
                        'CPU tools installed. First background removal downloads U²-Net (176 MB); later runs work offline.')
                       if installed else 'Run ./scripts/setup.sh to install local CPU image tools.'}


def process(operation, content, params, data, progress):
    try:
        from PIL import Image, ImageFilter, ImageOps, ImageChops
    except ImportError as e:
        raise ValueError('Local tools are not installed. Run ./scripts/setup.sh and restart Rogue Collage.') from e
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(content))).convert('RGBA')
    except Exception as e:
        raise ValueError('Local processing needs a readable still image.') from e
    if operation == 'cutout':
        global _session
        progress('Preparing local CPU background removal')
        try:
            from rembg import new_session, remove
        except ImportError as e:
            raise ValueError('Background removal dependencies are missing. Run ./scripts/setup.sh and restart.') from e
        with _lock:
            if _session is None:
                directory = model_directory(data)
                directory.mkdir(parents=True, exist_ok=True)
                os.environ['U2NET_HOME'] = str(directory)
                progress('Loading U²-Net on CPU' if model_cached(data) else 'Downloading U²-Net · 176 MB · first use only')
                try:
                    _session = new_session('u2net', providers=['CPUExecutionProvider'])
                except Exception as e:
                    raise ValueError('Could not prepare U²-Net. Check internet access for the first 176 MB model download, then retry.') from e
            progress('Removing background on CPU')
            mask = remove(image.convert('RGB'), session=_session, only_mask=True)
            image.putalpha(ImageChops.multiply(image.getchannel('A'), mask.convert('L')))
    elif operation == 'upscale':
        try:
            scale = float(params.get('scale', 2))
            if not math.isfinite(scale) or scale < 1:
                raise ValueError()
            size = (round(image.width * scale), round(image.height * scale))
            if size[0] * size[1] > 67_108_864:
                raise ValueError()
        except (TypeError, ValueError, OverflowError) as e:
            raise ValueError('CPU upscale needs a scale of at least 1 and output no larger than 64 megapixels.') from e
        progress('Upscaling on CPU · Lanczos')
        image = image.resize(size, Image.Resampling.LANCZOS)
        if params.get('sharpen', True):
            alpha = image.getchannel('A')
            image = image.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=3)).convert('RGBA')
            image.putalpha(alpha)
    else:
        raise ValueError('Local provider supports background removal and Lanczos upscale.')
    progress('Saving local result')
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()

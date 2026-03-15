"""
Tasarım görseline filigran ekleme (Pillow ile).
"""
import io
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

WATERMARK_TEXT = "marifetli.com.tr"


def add_watermark_to_image(image_file, format_from_name="PNG"):
    """
    Görsel dosyasına 'marifetli.com.tr' filigranı ekler.
    image_file: django UploadedFile veya file-like object.
    format_from_name: kaydederken kullanılacak format (PNG, JPEG).
    Returns: (bytes, content_type) veya (None, None) hata durumunda.
    """
    try:
        img = Image.open(image_file).convert("RGBA")
    except Exception as e:
        logger.warning("Design watermark: image open failed: %s", e)
        return None, None

    width, height = img.size
    font_size = max(14, min(width, height) // 18)
    font = None
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    try:
        bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    except AttributeError:
        text_w = int(len(WATERMARK_TEXT) * font_size * 0.6)
        text_h = int(font_size * 1.2)
        bbox = (0, 0, text_w, text_h)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = width - text_w - max(10, width // 40)
    y = height - text_h - max(10, height // 40)

    # Gölge + beyaz metin
    for dx, dy in [(1, 1), (1, 0), (0, 1)]:
        draw.text((x + dx, y + dy), WATERMARK_TEXT, fill=(0, 0, 0, 180), font=font)
    draw.text((x, y), WATERMARK_TEXT, fill=(255, 255, 255, 220), font=font)

    out = io.BytesIO()
    if format_from_name.upper() == "JPEG" or format_from_name.upper() == "JPG":
        img = img.convert("RGB")
        img.save(out, format="JPEG", quality=90)
        content_type = "image/jpeg"
    else:
        img.save(out, format="PNG")
        content_type = "image/png"
    out.seek(0)
    return out.read(), content_type

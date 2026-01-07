from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

def compress_image(image, quality=70, max_width=1280):
    img = Image.open(image)

    # Convert ke RGB (untuk PNG / RGBA)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Resize jika terlalu besar
    if img.width > max_width:
        ratio = max_width / float(img.width)
        height = int(float(img.height) * ratio)
        img = img.resize((max_width, height), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)

    return ContentFile(buffer.getvalue(), name=image.name)

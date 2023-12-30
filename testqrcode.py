from pyzbar.pyzbar import decode
from PIL import Image
import io
import base64


def image2byte(image):
    img_bytes = io.BytesIO()
    image = image.convert("RGB")
    image.save(img_bytes, format="JPEG")
    image_bytes = img_bytes.getvalue()
    return image_bytes

def byte2image(byte_data):
    image = Image.open(io.BytesIO(byte_data))
    return image

if __name__ == "__main__":
    imgori = Image.open("static/images/test.png")
    decocdeQR = decode(imgori)
    print(decocdeQR[0].data.decode('ascii'))

    byte_data = image2byte(imgori)
    print(byte_data)
    image2 = byte2image(byte_data)
    decocdeQR = decode(image2)
    print(decocdeQR[0].data.decode('ascii'))

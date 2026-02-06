from PIL import Image

try:
    img = Image.open("logo_ria_desktop.png")
    # Save as .ico containing multiple sizes for best OS support
    img.save("logo_ria.ico", format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")

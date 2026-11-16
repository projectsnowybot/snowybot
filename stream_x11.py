import socket
import struct
import time
import subprocess
import io
from PIL import Image, ImageDraw, ImageFont

def main():
    print("Starting Termux X11 Streamer to Android App (127.0.0.1:6000)...")
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 6000))
            print("Connected to Android App Display Server!")

            counter = 0
            while True:
                counter += 1
                # Create a dynamic visualization frame representing Termux X11 output
                img = Image.new('RGB', (1024, 768), color=(10, 15, 30))
                d = ImageDraw.Draw(img)

                # Draw terminal-like UI representation
                d.rectangle([20, 20, 1004, 748], outline=(0, 255, 128), width=3)
                d.text((40, 40), f"Termux X11 Virtual Display Active - Frame #{counter}", fill=(255, 255, 255))
                d.text((40, 80), "Running: xterm / bash / proot-distro", fill=(0, 255, 255))
                d.text((40, 120), f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}", fill=(200, 200, 200))

                # Draw simulated terminal text lines
                for i in range(15):
                    d.text((40, 180 + (i * 30)), f"root@android-termux:~# process_task_{counter + i} --status=running", fill=(100, 255, 100))

                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=85)
                data = buf.getvalue()

                # Send length-prefixed frame
                s.sendall(struct.pack('>I', len(data)) + data)
                time.sleep(0.1) # ~10 FPS

        except Exception as e:
            print("Connection error / reconnecting in 2s:", e)
            time.sleep(2)

if __name__ == '__main__':
    main()

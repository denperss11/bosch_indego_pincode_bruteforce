from PyV4L2Camera.camera import Camera
import numpy as np
import time
import csv

from enum import Enum
class Button(Enum):
    NextDigit = 0
    PrevDigit = 1
    Increase = 3
    Decrease = 4
    Fertig = 5

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

pin = 0
videodev = '/dev/video2'
ROI = (605, 150, 605+289, 150+80)

pinlist = []

def set_power_state(power_on):
    if (power_on == True):
        print("Power ON")
    else:
        print("Power OFF")

def press_button(button):
    print("Press button: ", button)

def take_image_and_ocr():
    camera = Camera(videodev)
    camera.width = 1280
    camera.height = 720
    frame = camera.get_frame()
    camera.close()
    image = Image.frombytes('RGB', (camera.width, camera.height), frame, 'raw', 'RGB')
    image = image.crop(ROI)
    image.save("/tmp/out.png")
    ret = pytesseract.image_to_string(image, 'deu')
    print(ret)
    return ret


def enter_number(num):
    print("Entering pin: ", num)
    digits = []
    digits.append(num // 1000)
    digits.append((num % 1000) // 100)
    digits.append((num % 100) // 10)
    digits.append((num % 10))

    for digit in digits:
        print("Entering digit: ", digit)
        for step in range(digit):
            press_button(Button.Increase)
            time.sleep(0.01)
        press_button(Button.NextDigit) # jump to next digit
        time.sleep(0.01)
    press_button(Button.Fertig)


if __name__ == '__main__':
    with open('four-digit-pin-codes-sorted-by-frequency-withcount.csv', newline='') as csvfile:
        pins_w_probability = csv.reader(csvfile, delimiter=',')
        for row in pins_w_probability:
            pinlist.append(int(row[0]))

    while pin < len(pinlist):
        set_power_state(True)
        #time.sleep(5)
        press_button(Button.Fertig) # Fertig
        pinfound = False
        for retry in range(3):
            enter_number(pinlist[pin])
            ocr = take_image_and_ocr()
            if not 'Fehler' in ocr and not 'Tasten' in ocr:
                pinfound = True
                break
            pin = pin + 1
            press_button(Button.Fertig)
            time.sleep(2)
        if pinfound:
            print("Pin found? ", pin)
            break
        set_power_state(False)

import sys

from PyV4L2Camera.camera import Camera
from PyV4L2Camera.controls import ControlIDs
import numpy as np
import time
import csv
import readchar
from enum import IntEnum
import RPi.GPIO as GPIO
import os
import glob

from enum import Enum
class Button(IntEnum):
    NextDigit = 3
    Increase = 4
    Fertig = 14

PowerEn = 18
DockPowerEn = 15

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

videodev = '/dev/video0'
ROI = (0, 0, 1280, 720)
ROI = (396, 321, 970, 400)
ROI_b = (374, 311, 980, 405)


pinlist = []
power = False
dockPower = False
camera = None

def gpio_init(turnOffPower) :
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(3, GPIO.OUT)
    GPIO.setup(4, GPIO.OUT)
    GPIO.setup(14, GPIO.OUT)
    GPIO.setup(PowerEn, GPIO.OUT)
    GPIO.setup(DockPowerEn, GPIO.OUT)
    if (turnOffPower):
        GPIO.output(PowerEn, GPIO.LOW)
        GPIO.output(DockPowerEn, GPIO.LOW)

def set_power_state(power_on):
    global power
    power = power_on
    if (power_on == True):
        print("Power ON")
        GPIO.output(PowerEn, GPIO.HIGH)
    else:
        print("Power OFF")
        GPIO.output(PowerEn, GPIO.LOW)

def set_dock_power_state(power_on):
    global dockPower
    dockPower = power_on
    if (power_on == True):
        print("Dock Power ON")
        GPIO.output(DockPowerEn, GPIO.HIGH)
    else:
        print("Dock Power OFF")
        GPIO.output(DockPowerEn, GPIO.LOW)

def press_button(button):
    #print("Press button: ", button)
    GPIO.output(int(button), GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(int(button), GPIO.LOW)

def take_image_and_ocr(savename, do_ocr, ROI_):
    camera = Camera(videodev, 1280, 720)
    #global camera
    frame = camera.get_frame()
    image = Image.frombytes('RGB', (camera.width, camera.height), frame, 'raw', 'RGB')
    del frame
    camera.close()
    image = image.crop(ROI_)
    image.save(str(savename) + ".png")
    if (do_ocr):
        tessconf = r'--dpi 300'
        ret = pytesseract.image_to_string(image, lang='deu', config=tessconf)
        del image
        print(ret)
        return ret.lower().translate(str.maketrans('', '', ' \n\t\r'))
    del image
    return ''

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
            time.sleep(0.1)
        press_button(Button.NextDigit) # jump to next digit
        time.sleep(0.1)
    press_button(Button.Fertig)

def dictionary_init(startPIN) :
    global pinlist
    skipStartPIN = False
    if (startPIN == ''):
        folder_path = "."
        files_path = os.path.join(folder_path, '*.png')
        files = sorted(glob.iglob(files_path), key=os.path.getctime, reverse=True)
        skipStartPIN = True
        startPIN = os.path.basename(files[0]).split('.')[0]
        print(startPIN)

    with open('four-digit-pin-codes-sorted-by-frequency-withcount.csv', newline='') as csvfile:
        pins_w_probability = csv.reader(csvfile, delimiter=',')

        firstPinFound = (len(startPIN) == 0)
        for row in pins_w_probability:
            if (firstPinFound) :
                pinlist.append(int(row[0]))
            else :
                if (int(row[0]) == int(startPIN)):
                    firstPinFound = True
                    if (not skipStartPIN) :
                        pinlist.append(int(row[0]))
        print("Loaded %d PINS" % len(pinlist))

def camera_init():
    os.system("v4l2-ctl -d 0 -c exposure_auto=0")
    os.system("v4l2-ctl -d 0 -c exposure_auto=1")
    os.system("v4l2-ctl -d 0 -c focus_auto=0")
    os.system("v4l2-ctl -d 0 -c focus_absolute=18")

def do_bruteforce() :
    global camera
    camera_init()
    #camera = Camera(videodev, 1280, 720)
    pin_index = 0
    while pin_index < len(pinlist):
        set_dock_power_state(True)
        time.sleep(5) # delay between the dock and power
        set_power_state(True)
        time.sleep(30) # boot time at the beginning
        press_button(Button.Fertig) # Fertig
        time.sleep(2)
        pin_found = False
        for retry in range(3):
            enter_number(pinlist[pin_index])
            time.sleep(2)
            ocr = take_image_and_ocr(pinlist[pin_index], True, ROI_b if retry == 2 else ROI)
            if not 'hler' in ocr \
                    and not 'ast' in ocr \
                    and not 'ind' in ocr \
                    and not 'esp' in ocr \
                    and not 'tte' in ocr \
                    and not 'onta' in ocr \
                    and not 'feh' in ocr \
                    and not 'erv' in ocr \
                    and not 'serv' in ocr:
                pin_found = True
                try:
                    input("Press enter to continue")
                except SyntaxError:
                    pass
                break
            pin_index = pin_index + 1
            press_button(Button.Fertig)
            time.sleep(1)
        if pin_found:
            print("Pin found?", pin_index, )
            break
        set_power_state(False)
        time.sleep(3)
        set_dock_power_state(False)
        time.sleep(5)

def button_test():
    global power
    global dockPower
    while True:
        c = readchar.readchar()
        if c == 'p':
            set_power_state(not power)
        elif c == 'd':
            set_dock_power_state(not dockPower)
        elif c == 'f':
            press_button(Button.Fertig)
        elif c == 'q':
            break
        elif c == '+':
            press_button(Button.Increase)
        elif c == 'n':
            press_button(Button.NextDigit)
        time.sleep(0.05)

if __name__ == '__main__':
    if (len(sys.argv) == 1 or sys.argv[1] == "bruteforce"):
        gpio_init(True)
        startPin = ''
        if (len(sys.argv) == 3):
            startPin = sys.argv[2]
        dictionary_init(startPin)
        do_bruteforce()
    else:
        if (sys.argv[1] == 'button_test'):
            gpio_init(False)
            button_test()
        elif (sys.argv[1] == 'take_image'):
            camera_init()
            take_image_and_ocr("test", False, ROI)
        elif (sys.argv[1] == 'take_image_b'):
            camera_init()
            take_image_and_ocr("test", False, ROI_b)
        elif (sys.argv[1] == 'take_image_ocr'):
            camera_init()
            take_image_and_ocr("test", True, ROI)
        elif (sys.argv[1] == 'take_image_ocr_b'):
            camera_init()
            take_image_and_ocr("test", True, ROI_b)
        else:
            print("Usage:")
            print(" No arguments: start brute force")
            print(" bruteforce [start_pin]: start brute force from the pin passed in the 2nd arg")
            print(" button_test: test the GPIO interface")
            print("              Supported keys:")
            print("              - q: exit")
            print("              - f: 'Fertig'")
            print("              - +: increase digit")
            print("              - n: next digit")
            print("              - p: toggle power")
            print("              - d: toggle dock power")
            print(" take_image:  Take a test image and write it to test.png")
            print(" take_image_ocr:  Take a test image and write it to test.png and OCR it")

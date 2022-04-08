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


class Target(IntEnum):
    Bosch_Indego = 0,
    Husqvarna = 1

target = Target.Bosch_Indego # TODO add cmd line arg

from enum import Enum
class Button(IntEnum):
    NextDigit = 4
    Increase = 3
    Fertig = 14
    Btn_0 = Increase
    Btn_1 = NextDigit
    Btn_2 = 7
    Btn_3 = 8
    Btn_4 = 9
    Btn_5 = 10
    Btn_6 = 11
    Btn_7 = 12
    Btn_8 = 13
    Btn_9 = 16


DockPowerEn = 15
PowerEn = 18

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

videodev = '/dev/video0'
ROI = (0, 0, 1280, 720)
ROI = (280, 170, 760, 370)
#ROI_b = (374, 311, 980, 405)


pinlist = []
power = False
dockPower = False
camera = None

def gpio_init(turnOffPower) :
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(3, GPIO.OUT)
    GPIO.setup(4, GPIO.OUT)
    GPIO.setup(5, GPIO.OUT)
    GPIO.setup(7, GPIO.OUT)
    GPIO.setup(8, GPIO.OUT)
    GPIO.setup(9, GPIO.OUT)
    GPIO.setup(10, GPIO.OUT)
    GPIO.setup(11, GPIO.OUT)
    GPIO.setup(12, GPIO.OUT)
    GPIO.setup(13, GPIO.OUT)
    GPIO.setup(14, GPIO.OUT)
    GPIO.setup(16, GPIO.OUT)
    GPIO.output(3, GPIO.LOW)
    GPIO.output(4, GPIO.LOW)
    GPIO.output(5, GPIO.LOW)
    GPIO.output(7, GPIO.LOW)
    GPIO.output(8, GPIO.LOW)
    GPIO.output(9, GPIO.LOW)
    GPIO.output(10, GPIO.LOW)
    GPIO.output(11, GPIO.LOW)
    GPIO.output(12, GPIO.LOW)
    GPIO.output(13, GPIO.LOW)
    GPIO.output(14, GPIO.LOW)
    GPIO.output(16, GPIO.LOW)
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
    print("Press button: ", button)
    GPIO.output(int(button), GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(int(button), GPIO.LOW)

def take_image_and_ocr(savename, do_ocr, ROI_):
    camera_init()
    camera = Camera(videodev, 1280, 720)
    time.sleep(2)
    #global camera
    frame = camera.get_frame()
    image = Image.frombytes('RGB', (camera.width, camera.height), frame, 'raw', 'RGB')
    del frame
    camera.close()
    image = image.crop(ROI_)
    image.save(str(savename) + ".png")
    if (do_ocr):
        tessconf = r'--dpi 400'
        ret = pytesseract.image_to_string(image, lang='deu', config=tessconf).lower().translate(str.maketrans('', '', ' \n\t\r'))
        del image
        print(ret)
        return ret
    del image
    return ''

def enter_number_bosch(num):
    press_button(Button.Fertig)
    time.sleep(1)
    print("Entering pin: ", num)
    digits = []
    digits.append(num // 1000)
    digits.append((num % 1000) // 100)
    digits.append((num % 100) // 10)
    digits.append((num % 10))

    for digit in digits:
        #print("Entering digit: ", digit)
        for step in range(digit):
            press_button(Button.Increase)
            time.sleep(0.1)
        press_button(Button.NextDigit) # jump to next digit
        time.sleep(0.1)
    press_button(Button.Fertig)

def enter_number_husqvarna(num):
    print("Entering pin: ", num)
    digits = []
    digits.append(num // 1000)
    digits.append((num % 1000) // 100)
    digits.append((num % 100) // 10)
    digits.append((num % 10))

    for digit in digits:
        if (digit == 0) :
            press_button(Button.Increase)
        elif (digit == 1) :
            press_button(Button.NextDigit)
        elif (digit == 2):
            press_button(Button.Btn_2)
        elif (digit == 3):
            press_button(Button.Btn_3)
        elif (digit == 4):
            press_button(Button.Btn_4)
        elif (digit == 5):
            press_button(Button.Btn_5)
        elif (digit == 6):
            press_button(Button.Btn_6)
        elif (digit == 7):
            press_button(Button.Btn_7)
        elif (digit == 8):
            press_button(Button.Btn_8)
        elif (digit == 9):
            press_button(Button.Btn_9)

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
        if (len(pinlist) <= 1) :
            input("All entries tried.... Press enter to continue")

def camera_init():
    os.system("v4l2-ctl -d 0 -c exposure_auto=0")
    os.system("v4l2-ctl -d 0 -c exposure_auto=1")
    os.system("v4l2-ctl -d 0 -c focus_auto=0")
    os.system("v4l2-ctl -d 0 -c focus_absolute=18")

def do_bruteforce_husq() :
    global camera
    global target
    camera_init()
    pin_index = 0
    while pin_index < len(pinlist):
        set_dock_power_state(True)
        time.sleep(8) # delay between the dock and power
        pin_found = False
        if (target == Target.Bosch_Indego) :
            enter_number_bosch(pinlist[pin_index])
        elif (target == Target.Husqvarna) :
            enter_number_husqvarna(pinlist[pin_index])
        time.sleep(1)

        ocr = take_image_and_ocr(pinlist[pin_index], False, ROI)
        '''if not 'akc' in ocr \
                and not 'ept' in ocr \
                and not 'nic' in ocr \
                and not 'iert' in ocr \
                and not 'akz' in ocr \
                and not 'kze' in ocr \
                and not 'icht' in ocr:
            pin_found = False
            try:
                input("Press enter to continue")
            except SyntaxError:
                pass
            break'''
        pin_index = pin_index + 1

        if pin_found:
            print("Pin found?", pin_index, )
            break
        set_dock_power_state(False)
        time.sleep(1)

def do_bruteforce():
    global camera
    global target
    camera_init()
    pin_index = 0
    rebootCounter = 0
    set_dock_power_state(True)
    time.sleep(1)
    set_power_state(True)
    time.sleep(1)
    set_power_state(False)
    time.sleep(15)


    while pin_index < len(pinlist):
        enter_number_bosch(pinlist[pin_index])
        ocr = take_image_and_ocr(pinlist[pin_index], False, ROI)
        pin_index = pin_index + 1
        rebootCounter = rebootCounter + 1
        if (rebootCounter == 3) :
            rebootCounter = 0
            set_dock_power_state(False)
            time.sleep(2)
            set_dock_power_state(True)
            time.sleep(1)
            set_power_state(True)
            time.sleep(1)
            set_power_state(False)
            time.sleep(15)

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
        elif (ord('0') <= ord(c) and ord(c) <= ord('9')) :
            if (c == '9') :
                press_button(Button.Btn_9)
            elif (c == '0') :
                press_button(Button.Btn_0)
            elif (c == '1') :
                press_button(Button.Btn_1)
            else :
                press_button(Button.Btn_2 + ord(c) - ord('2'))
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
        elif (sys.argv[1] == 'take_image_ocr'):
            camera_init()
            take_image_and_ocr("test", True, ROI)
        else:
            print("Usage:")
            print(" No arguments: start brute force")
            print(" bruteforce [start_pin]: start brute force from the pin passed in the 2nd arg")
            print(" button_test: test the GPIO interface")
            print("              Supported keys:")
            print("              - q: exit")
            print("              - f: 'Fertig' / Enter at Husqvarna")
            print("              - +: increase digit")
            print("              - n: next digit")
            print("              - 0-9: enter digit (Husqvarna only)")
            print("              - p: toggle power")
            print("              - d: toggle dock power")
            print(" take_image:  Take a test image and write it to test.png")
            print(" take_image_ocr:  Take a test image and write it to test.png and OCR it")

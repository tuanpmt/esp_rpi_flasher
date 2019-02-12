#! /usr/bin/env python
import argparse
import configparser
import glob
import os
import os.path
import RPi.GPIO as GPIO
import serial
import subprocess
import sys
import threading
from time import sleep

PYTHON=sys.executable

configFilePath = ("/boot/code/config.ini")
config = configparser.ConfigParser()
config.read(configFilePath)

projectPath = config.get('DEFAULT', 'projectPath')
isEncrypt = config.get('DEFAULT', 'isEncrypt')
if isEncrypt == 'True':
    bootloaderPath = config.get('ENCRYPT', 'bootloaderPath')
    partitionsPath = config.get('ENCRYPT', 'partitionsPath')
    otaDataPath = config.get('ENCRYPT', 'otaDataPath')
    appDataPath = config.get('ENCRYPT', 'appDataPath')
    secureBootloaderKeyPath = config.get('ENCRYPT', 'secureBootloaderKeyPath')
    flashEcryptionKeyPath = config.get('ENCRYPT', 'flashEcryptionKeyPath')
else:
    bootloaderPath = config.get('DEFAULT', 'bootloaderPath')
    partitionsPath = config.get('DEFAULT', 'partitionsPath')
    otaDataPath = config.get('DEFAULT', 'otaDataPath')
    appDataPath = config.get('DEFAULT', 'appDataPath')
    secureBootloaderKeyPath = config.get('DEFAULT', 'secureBootloaderKeyPath')
    flashEcryptionKeyPath = config.get('DEFAULT', 'flashEcryptionKeyPath')

flashButton = int(config.get('DEFAULT', 'flashButton'))
reFlashButton = int(config.get('DEFAULT', 'reFlashButton'))
rebootButton = int(config.get('DEFAULT', 'rebootButton'))
flashingLED = int(config.get('DEFAULT', 'flashingLED'))
reFlashLED = int(config.get('DEFAULT', 'reFlashLED'))
readyLED = int(config.get('DEFAULT', 'readyLED'))
# config LED and button
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(flashButton, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
GPIO.setup(reFlashButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(rebootButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)  
GPIO.setup(flashingLED, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(reFlashLED, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(readyLED, GPIO.OUT, initial=GPIO.LOW)

reFlashPorts = []  # list reflash port
flashFlag = False
reFlashFlag = False
rebootFlag = False

def _get_args(type, esptool_path, port, baud):
    if type == "burn_secure_key":
        result = [ PYTHON, esptool_path ]
        result += [ "--port", port ]
        result += [ "--do-not-confirm" ]
        result += [ "--before", "default_reset" ]
        result += [ "burn_key" ]
        result += [ "secure_boot", secureBootloaderKeyPath ]
        return result
    elif type == "burn_flash_encryption_key":
        result = [ PYTHON, esptool_path ]
        result += [ "--port", port ]
        result += [ "--do-not-confirm" ]
        result += [ "--before", "default_reset" ]
        result += [ "burn_key" ]
        result += [ "flash_encryption", flashEcryptionKeyPath ]
        return result
    elif type == "burn_efuse_cnt":
        result = [ PYTHON, esptool_path ]
        result += [ "--port", port ]
        result += [ "--do-not-confirm" ]
        result += [ "--before", "default_reset" ]
        result += [ "burn_efuse" ]
        result += [ "FLASH_CRYPT_CNT", "1" ]
        return result
    elif type == "burn_efuse_config":
        result = [ PYTHON, esptool_path ]
        result += [ "--port", port ]
        result += [ "--do-not-confirm" ]
        result += [ "--before", "default_reset" ]
        result += [ "burn_efuse" ]
        result += [ "FLASH_CRYPT_CONFIG", "0xf" ]
        return result
    elif type == "flash":
        result = [ PYTHON, esptool_path ]
        result += [ "--chip", "esp32" ]
        result += [ "--port", port ]
        result += [ "--baud", str(baud) ]
        result += [ "--before", "default_reset" ]
        result += [ "--after", "hard_reset" ]
        result += [ "write_flash", "-z" ]
        result += [ "--flash_mode", "dio" ]
        result += [ "--flash_freq", "40m" ]
        result += [ "--flash_size", "detect" ]
        result += [ "0x10000", appDataPath ]
        result += [ "0x8000", partitionsPath ]
        result += [ "0x0", bootloaderPath ]
        result += [ "0xe000", otaDataPath ]
        return result
    elif type == "erase_flash":
        result = [ PYTHON, esptool_path ]
        result += [ "--port", port ]
        result += [ "erase_flash" ]
        return result
    else:
        return 0

# get current USB ports
def _get_ports():
    if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[Uu]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.U*')
    else:
        raise EnvironmentError('Unsupported platform')
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


def _run_tool(tool_name, args1, args2, args3, args4, args5):
    def quote_arg(arg):
        " Quote 'arg' if necessary "
        if " " in arg and not (arg.startswith('"') or arg.startswith("'")):
            return "'" + arg + "'"
        return arg
    def display_command(command):
        display_args = " ".join(quote_arg(arg) for arg in command)
        print("Running %s in directory %s" % (tool_name, quote_arg(projectPath)))
        print('Executing "%s"...' % display_args)
    
    if isEncrypt == 'True':
        burnKeyFlag = True
        try:
            display_command(args1)
            subprocess.check_call(args1, env=os.environ, cwd=projectPath)
        except subprocess.CalledProcessError as e:
            burnKeyFlag = False
            print("%s failed with exit code %d" % (tool_name, e.returncode))
        try:
            display_command(args2)
            subprocess.check_call(args2, env=os.environ, cwd=projectPath)
        except subprocess.CalledProcessError as e:
            burnKeyFlag = False
            print("%s failed with exit code %d" % (tool_name, e.returncode))
        if burnKeyFlag:
            try:
                display_command(args3)
                subprocess.check_call(args3, env=os.environ, cwd=projectPath)
            except subprocess.CalledProcessError as e:
                print("%s failed with exit code %d" % (tool_name, e.returncode))
            try:
                display_command(args4)
                subprocess.check_call(args4, env=os.environ, cwd=projectPath)
            except subprocess.CalledProcessError as e:
                print("%s failed with exit code %d" % (tool_name, e.returncode))
                
    try:
        display_command(args5)
        subprocess.check_call(args5, env=os.environ, cwd=projectPath)
    except subprocess.CalledProcessError as e:
        print("%s failed with exit code %d" % (tool_name, e.returncode))
        GPIO.output(reFlashLED, GPIO.HIGH)   # turn on reflash LED
        if (args5[5] in reFlashPorts) == False:
            reFlashPorts.append(args5[5]) # add false flash port into reFlashPorts list.
        print("%s" % reFlashPorts)
    sleep(1)
    print("Done")
    return 0

def _flash_callback(channel):  
    print("Flash button is pressed")
    global flashFlag
    flashFlag = True # enable flash

def _flash():
    print("Number of threads: %s" %threading.active_count())
    del reFlashPorts[:]  # delete old reflash ports
    GPIO.output(flashingLED, GPIO.HIGH) # turn on flashing LED (flashing...)
    GPIO.output(reFlashLED, GPIO.LOW)   # turn off reflash LED
    ports = _get_ports() # list current ports
    threads = []
    for x in ports:
        args1 = _get_args("burn_secure_key", os.path.join(projectPath, "esptool/espefuse.py"), x, 2000000)
        args2 = _get_args("burn_flash_encryption_key", os.path.join(projectPath,"esptool/espefuse.py"), x, 2000000)
        args3 = _get_args("burn_efuse_cnt", os.path.join(projectPath,"esptool/espefuse.py"), x, 2000000)
        args4 = _get_args("burn_efuse_config", os.path.join(projectPath,"esptool/espefuse.py"), x, 2000000)
        args5 = _get_args("flash", os.path.join(projectPath,"esptool/esptool.py"), x, 2000000)
        flashThread = threading.Thread(target=_run_tool, args=("esptool.py", args1, args2, args3, args4, args5))
        threads.append(flashThread)
    for x in threads:
        x.start()
    for x in threads:
        x.join()
    GPIO.output(flashingLED, GPIO.LOW)  # turn off flashing LED (flash completed)
    global flashFlag
    flashFlag = False # disable flash

def _reflash_callback(channel):  
    print("Reflash button is pressed")
    global reFlashFlag
    reFlashFlag = True # enable reflash

def _reflash():
    threads = []
    GPIO.output(flashingLED, GPIO.HIGH) # turn on flashing LED (flashing...)
    GPIO.output(reFlashLED, GPIO.LOW)
    for x in reFlashPorts:
        args1 = _get_args("burn_secure_key", os.path.join(projectPath, "esptool/espefuse.py"), x, 2000000)
        args2 = _get_args("burn_flash_encryption_key", os.path.join(projectPath,"esptool/espefuse.py"), x, 2000000)
        args3 = _get_args("burn_efuse_cnt", os.path.join(projectPath,"esptool/espefuse.py"), x, 2000000)
        args4 = _get_args("burn_efuse_config", os.path.join(projectPath,"esptool/espefuse.py"), x, 2000000)
        args5 = _get_args("flash", os.path.join(projectPath,"esptool/esptool.py"), x, 2000000)
        reFlashThread = threading.Thread(target=_run_tool, args=("esptool.py", args1, args2, args3, args4, args5))
        threads.append(reFlashThread)
    del reFlashPorts[:]  # delete old reflash ports
    for x in threads:
        x.start()
    for x in threads:
        x.join()
    global reFlashFlag
    reFlashFlag = False # disable reflash
    GPIO.output(flashingLED, GPIO.LOW)  # turn off flashing LED (flash completed)

def _reboot_callback(channel):  
    print("Reboot button is pressed")
    GPIO.output(readyLED, GPIO.LOW)
    sleep(1)
    global rebootFlag
    rebootFlag = True # enable reboot

def _reboot():
    os.system("sudo reboot")

# add event detect buttons
GPIO.add_event_detect(reFlashButton, GPIO.FALLING, callback=_reflash_callback, bouncetime=2000)  
GPIO.add_event_detect(flashButton, GPIO.FALLING, callback=_flash_callback, bouncetime=2000)  
GPIO.add_event_detect(rebootButton, GPIO.FALLING, callback=_reboot_callback, bouncetime=2000)  

try:
    GPIO.output(readyLED, GPIO.HIGH)
    while True:
        if flashFlag == True:
            _flash()
        if reFlashFlag == True:
            _reflash()
        if rebootFlag == True:
            _reboot()
except KeyboardInterrupt:  
    GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
GPIO.cleanup()           # clean up GPIO on normal exit  
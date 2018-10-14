import configparser
import subprocess
import sys
import argparse
import os
import os.path
import threading 


PYTHON=sys.executable
CWD = os.getcwd() 

config = configparser.ConfigParser()
config.read('config.ini')
bootloaderPath = config['DEFAULT']['bootloaderPath']
partitionsPath = config['DEFAULT']['partitionsPath']
otaDataPath = config['DEFAULT']['otaDataPath']
appDataPath = config['DEFAULT']['appDataPath']



def _run_tool(tool_name, args):
    def quote_arg(arg):
        " Quote 'arg' if necessary "
        if " " in arg and not (arg.startswith('"') or arg.startswith("'")):
            return "'" + arg + "'"
        return arg
    display_args = " ".join(quote_arg(arg) for arg in args)
    print("Running %s in directory %s" % (tool_name, quote_arg(CWD)))
    print('Executing "%s"...' % display_args)
    try:
        # Note: we explicitly pass in os.environ here, as we may have set IDF_PATH there during startup
        subprocess.check_call(args, env=os.environ, cwd=CWD)
    except subprocess.CalledProcessError as e:
        raise FatalError("%s failed with exit code %d" % (tool_name, e.returncode))

def _get_args(esptool_path, port, baud):
	result = [ PYTHON, esptool_path ]
	result += [ "--port", port ]
	result += [ "--baud", str(baud) ]
	result += [ "write_flash" ]
	result += [ "0xe000", otaDataPath ]
	result += [ "0x1000", bootloaderPath ]
	result += [ "0x10000", appDataPath ]
	result += [ "0x8000", partitionsPath ]
	return result


args1 = _get_args(os.path.join(CWD, "esptool/esptool.py"), "/dev/tty.SLAB_USBtoUART1", 2000000)
args2 = _get_args(os.path.join(CWD, "esptool/esptool.py"), "/dev/tty.SLAB_USBtoUART2", 2000000)
args3 = _get_args(os.path.join(CWD, "esptool/esptool.py"), "/dev/tty.SLAB_USBtoUART3", 2000000)
args4 = _get_args(os.path.join(CWD, "esptool/esptool.py"), "/dev/tty.SLAB_USBtoUART4", 2000000)
# _run_tool("esptool.py", args, cwd)

threading.Thread(target=_run_tool, args=("esptool.py", args1)).start()
threading.Thread(target=_run_tool, args=("esptool.py", args2)).start()
threading.Thread(target=_run_tool, args=("esptool.py", args3)).start()
threading.Thread(target=_run_tool, args=("esptool.py", args4)).start()

# setup button1, 2, 3, 4 => fun thread 1, 2, 3, 4
# setup button ALL run 4 threads
# setup LED to pass the argurment

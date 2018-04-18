from setuptools import  find_packages, setup, Executable




import sys
base = None  

if sys.platform == "win32":
    base = "Win32GUI"

import os.path
PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))



executables = [Executable("vintel.py", base=base,icon="icon.ico")]

packages = ["appdirs","packaging.version","packaging.specifiers","packaging","pyglet","pyqt5","pyttsx3"]

package_data = {'ui' : ['vi/ui/*']} 

options = {
    'build_exe': {    
        'packages':packages,
		'optimize':2,
		 
    },    
}

setup(
    name = "VINTEL",
    options = options,
    version = "1.2.4",
    description = 'Intel chat analyzer',
    executables = executables,
	include_package_data=True,
	package_data = {'' : ['*.ui','*.png','*.svg','*.wav']},
	
)
from setuptools import  find_packages
from cx_Freeze import  setup, Executable

import sys
base = None  

import os.path
PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')


executables = [Executable("vintel.py", base=base)]

packages = ["idna","appdirs","packaging.version","packaging.specifiers","packaging","pyglet"]

package_data = {'ui' : ['vi/ui/*']} 

options = {
    'build_exe': {    
        'packages':packages,
		'include_files':[
            os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tk86t.dll'),
            os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tcl86t.dll'),
         ],
    },    
}

setup(
    name = "VINTEL",
    options = options,
    version = "1.2.4",
    description = 'Intel chat analyzer',
    executables = executables,
	include_package_data=True,
	package_data = {'' : ['*.ui','*.png','*.svg','*.wav']}
)
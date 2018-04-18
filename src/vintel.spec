# -*- mode: python -*-

import os
import ntpath 
import PyQt5 

block_cipher = None


a = Analysis(['vintel.py'],
             pathex=['E:\\work\\Repositories\\vintel\\src',os.path.join(ntpath.dirname(PyQt5.__file__), 'Qt', 'bin')],
             binaries=[('avbin.dll','.'),],
             datas=[
			        ('vi/ui/*.ui','vi/ui'),
			        ('vi/ui/res/*','vi/ui/res')],
             hiddenimports=[
				'pyttsx3.drivers',
				'pyttsx3.drivers.dummy',
				'pyttsx3.drivers.espeak',
				'pyttsx3.drivers.nsss',
				'pyttsx3.drivers.sapi5',
				],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='vintel',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='vintel')

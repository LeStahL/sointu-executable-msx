# -*- mode: python ; coding: utf-8 -*-
from os.path import abspath, join
from zipfile import ZipFile
from platform import system

moduleName = 'sointuexemsx'
rootPath = abspath('.')
buildPath = join(rootPath, 'build')
distPath = join(rootPath, 'dist')
sourcePath = join(rootPath, moduleName)

block_cipher = None

a = Analysis([
        join(sourcePath, '__main__.py'),
    ],
    pathex=[],
    binaries=[],
    datas=[
        (join(sourcePath, 'play.asm'), moduleName),
        (join(sourcePath, 'wav.asm'), moduleName),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{}'.format(moduleName),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=join(rootPath, 'team210.ico'),
)

exeFileName = '{}{}'.format(moduleName, '.exe' if system() == 'Windows' else '')
zipFileName = '{}-{}.zip'.format(moduleName, system())
zipFile = ZipFile(join(distPath, zipFileName), mode='w')
zipFile.write(join(distPath, exeFileName), arcname=join(moduleName, exeFileName))
zipFile.write(join(rootPath, 'LICENSE'), arcname=join(moduleName, 'LICENSE'))
zipFile.write(join(rootPath, 'README.md'), arcname=join(moduleName, 'README.md'))
zipFile.close()

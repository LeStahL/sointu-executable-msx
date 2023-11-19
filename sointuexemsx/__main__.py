from argparse import (
    ArgumentParser,
    Namespace,
)
from importlib.resources import files
import sointuexemsx
from cached_path import cached_path
from pathlib import Path
from winreg import (
    ConnectRegistry,
    OpenKey,
    HKEY_LOCAL_MACHINE,
    HKEYType,
    QueryValueEx,
)
from subprocess import (
    run,
    CompletedProcess,
)
from tempfile import TemporaryDirectory
from os.path import (
    basename,
    splitext,
    exists,
)
from zipfile import ZipFile
from sys import exit

if __name__ == '__main__':
    # Parse command line arguments.
    parser: ArgumentParser = ArgumentParser("sointu-executable-msx", description="Easy-to-use tool to create executable music using Sointu.")
    parser.add_argument(nargs=1, dest='input', help='Track file to compile.')
    parser.add_argument('-b,--brutal', dest='brutal', action='store_true', help='Use brutal Crinkler settings (takes much longer, but executable will be smaller).')
    parser.add_argument('-n,--nfo', dest='nfo', default=None, help='Add a NFO to the release archive.')
    parser.add_argument('-d,--delay', dest='delay', default=0, type=int, help='Add a delay in ms before starting to play the track (useful for computationally heavy tracks).')
    args: Namespace = parser.parse_args()

    # Check argument sanity
    if args.input is None or type(args.input) != list or len(args.input) != 1:
        print('Input argument missing or wrong format:', args.input)
        exit(1)

    if not exists(args.input[0]):
        print("Input file does not exist:", args.input[0])
        exit(1)

    if args.nfo is not None and not exists(args.nfo):
        print("NFO file does not exist:", args.nfo)

    # Download dependencies.
    crinkler: Path = cached_path(
        url_or_filename='https://github.com/runestubbe/Crinkler/releases/download/v2.3/crinkler23.zip!crinkler23/Win64/Crinkler.exe',
        extract_archive=True,
    )
    nasm: Path = cached_path(
        url_or_filename='https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip!nasm-2.16.01/nasm.exe',
        extract_archive=True,
    )
    sointu: Path = cached_path(
        'https://github.com/vsariola/sointu/releases/download/v0.3.0/sointu-Windows.zip!sointu-windows/sointu-compile.exe',
        extract_archive=True,
    )
    
    # Find Windows SDK path.
    registry: HKEYType = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
    windowsSdkKey: HKEYType = OpenKey(registry, r'SOFTWARE\WOW6432Node\Microsoft\Microsoft SDKs\Windows\v10.0')
    windowsSdkProductVersion, _ = QueryValueEx(windowsSdkKey, r'ProductVersion')
    windowsSdkInstallFolder, _ = QueryValueEx(windowsSdkKey, r'InstallationFolder')
    windowsSdkKey.Close()
    registry.Close()
    windowsSdkLibPath: Path = Path(windowsSdkInstallFolder) / 'Lib' / '{}.0'.format(windowsSdkProductVersion) / 'um' / 'x86'

    # Determine track base name without extension.
    base, _ = splitext(basename(args.input[0]))

    # Run sointu-compile on the track.
    with Path(TemporaryDirectory().name) as outputDirectory:
        print('Exporting to:', outputDirectory)

        # Run sointu-compile to convert the track to assembly.
        result: CompletedProcess = run([
            sointu,
            '-arch', '386',
            '-e', 'asm,inc',
            '-o', outputDirectory / 'music.asm',
            args.input[0],
        ])

        if result.returncode != 0:
            print("Could not compile track with Sointu.")
        else:
            print("Compiled sointu track.")

        # Assemble the wav writer.
        result: CompletedProcess = run([
            nasm,
            '-f', 'win32',
            '-I', outputDirectory,
            files(sointuexemsx) / 'wav.asm',
            '-DTRACK_INCLUDE="{}"'.format(outputDirectory / 'music.inc'),
            '-DFILENAME="{}"'.format('music.wav'),
            '-o', outputDirectory / 'wav.obj',
        ])

        if result.returncode != 0:
            print("Could not assemble wav writer.")
        else:
            print("Assembled wav writer.")

        # Assemble the player.
        result: CompletedProcess = run([
            nasm,
            '-f', 'win32',
            '-I', outputDirectory,
            files(sointuexemsx) / 'play.asm',
            '-DTRACK_INCLUDE="{}"'.format(outputDirectory / 'music.inc'),
            '-DDELAY' if args.delay != 0 else '',
            '-DDELAY_MS={}'.format(args.delay) if args.delay != 0 else '',
            '-o', outputDirectory / 'play.obj',
        ])

        if result.returncode != 0:
            print("Could not assemble player.")
        else:
            print("Assembled player.")

        # Assemble the track.
        result: CompletedProcess = run([
            nasm,
            '-f', 'win32',
            '-I', outputDirectory,
            outputDirectory / 'music.asm',
            '-o', outputDirectory/ 'music.obj',
        ])

        if result.returncode != 0:
            print("Could not assemble track.")
        else:
            print("Assembled track.")

        # Link wav writer.
        # Note: When using the list based api, quotes in arguments
        # are not escaped properly.
        result: CompletedProcess = run(' '.join(map(str,[
            crinkler,
            '/LIBPATH:"{}"'.format(outputDirectory),
            '/LIBPATH:"{}"'.format(windowsSdkLibPath),
            outputDirectory / 'wav.obj',
            outputDirectory / 'music.obj',
            '/OUT:{}'.format(outputDirectory / '{}-wav.exe'.format(base)),
            'Winmm.lib',
            'Kernel32.lib',
            'User32.lib',
            '/COMPMODE:VERYSLOW' if args.brutal else '/COMPMODE:FAST',
        ])), shell=True)

        # Link player.
        # Note: When using the list based api, quotes in arguments
        # are not escaped properly.
        result: CompletedProcess = run(' '.join(map(str,[
            crinkler,
            '/LIBPATH:"{}"'.format(outputDirectory),
            '/LIBPATH:"{}"'.format(windowsSdkLibPath),
            outputDirectory / 'play.obj',
            outputDirectory / 'music.obj',
            '/OUT:{}'.format(outputDirectory / '{}-play.exe'.format(base)),
            'Winmm.lib',
            'Kernel32.lib',
            'User32.lib',
            '/COMPMODE:VERYSLOW' if args.brutal else '/COMPMODE:FAST',
        ])), shell=True)

        # Create release archive.
        zipFile: ZipFile = ZipFile('{}.zip'.format(base), 'w')
        zipFile.write(filename=str(outputDirectory / '{}-wav.exe'.format(base)), arcname='{}/{}-wav.exe'.format(base, base))
        zipFile.write(filename=str(outputDirectory / '{}-play.exe'.format(base)), arcname='{}/{}-play.exe'.format(base, base))
        if args.nfo is not None:
            nfoBaseWithExt = basename(args.nfo)
            zipFile.write(filename=args.nfo, arcname='{}/{}'.format(base, nfoBaseWithExt))
        zipFile.close()

    exit(0)

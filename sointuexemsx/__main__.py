from argparse import (
    ArgumentParser,
    Namespace,
)
from typing import Optional
from importlib.resources import files
import sointuexemsx
from cached_path import (
    cached_path,
    get_cache_dir,
)
from pathlib import Path
from platform import system
if system() == 'Windows':
    from winreg import (
        ConnectRegistry,
        OpenKey,
        HKEY_LOCAL_MACHINE,
        HKEYType,
        QueryValueEx,
    )
elif system() == 'Linux':
    from stat import (
        S_IXUSR,
        S_IXGRP,
        S_IXOTH,
    )
from subprocess import (
    run,
    CompletedProcess,
)
from tempfile import TemporaryDirectory
from os.path import (
    basename,
    splitext,
    dirname,
    exists,
)
from zipfile import ZipFile
from sys import exit
from shutil import (
    copyfile,
    rmtree,
)
from enum import (
    IntEnum,
    auto,
)
from json import loads


class DependencyType(IntEnum):
    Crinkler = auto()
    Nasm = auto()
    SointuCompile = auto()
    Upx = auto()
    Ld = auto()


def clear_cached_path(
    url: str,
    cache_dir: Optional[str] = None,
):
    cache_root: Path = Path(cache_dir or get_cache_dir()).expanduser()
    result: list = []
    for metadata in cache_root.glob("*.json"):
        data: dict = {}
        try:
            data = loads(metadata.read_text())
        except Exception:
            continue

        if data.get("resource") == url.split('!')[0]:
            base = metadata.with_suffix("")
            for target in [
                base,
                metadata,
                cache_root / f"{base.name}-extracted"
            ]:
                if target.exists():
                    if target.is_dir():
                        rmtree(target)
                    else:
                        target.unlink()
                    result.append(target)
    return result


if __name__ == '__main__':
    # Parse command line arguments.
    parser: ArgumentParser = ArgumentParser("sointu-executable-msx", description="Easy-to-use tool to create executable music using Sointu.")
    parser.add_argument(nargs=1, dest='input', help='Track file to compile.')
    parser.add_argument('-b,--brutal', dest='brutal', action='store_true', help='Use brutal Crinkler settings (takes much longer, but executable will be smaller).')
    parser.add_argument('-n,--nfo', dest='nfo', default=None, help='Add a NFO to the release archive.')
    parser.add_argument('-d,--delay', dest='delay', default=0, type=int, help='Add a delay in ms before starting to play the track (useful for computationally heavy tracks).')
    parser.add_argument('-s,--sointu-compile', dest='sointuCompile', default=None, help='Override the sointu-compile executable to use.')
    parser.add_argument('-4,--4klang', dest='fourKlang', default=None, help='Use this 4klang.asm to pack a 4klang track.')
    parser.add_argument('--sample-type', dest='sampleType', default='float', choices=['float', 'pcm'], help='Enforce the sample type for 4klang builds.')
    parser.add_argument('--channel-count', dest='channelCount', default=2, help='Enforce channel count for 4klang builds.')
    parser.add_argument('--sample-size', dest='sampleSize', default=4, help='Enforce sample size for 4klang builds.')
    parser.add_argument('--force-download', dest='forceDownload', action='store_true', help='Force-redownload the cached dependencies.')
    parser.add_argument('--ld', dest='ld', default='ld', help='Use this ld binary instead of the one in the PATH variable.')
    parser.add_argument('--build-folder', dest='buildFolder', default=None, help='Use a specific build folder instead of a temporary dir.')
    parser.add_argument('--disable-upx', dest='disableUpx', action='store_true', help='Disable UPX for drop-in replacement compressing linkers for ld.')
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
        exit(1)

    if args.sointuCompile is not None and not exists(args.sointuCompile):
        print("Sointu override file could not be found:", args.sointuCompile)
        exit(1)

    if args.fourKlang is not None and not exists(args.fourKlang):
        print("4klang assembly file does not exist:", args.fourKlang)
        exit(1)

    # Download dependencies.
    downloadUrls = {}
    if system() == 'Windows':
        downloadUrls.update({
            DependencyType.Crinkler: 'https://github.com/runestubbe/Crinkler/releases/download/v2.3/crinkler23.zip!crinkler23/Win64/Crinkler.exe',
            DependencyType.Nasm: 'https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip!nasm-2.16.01/nasm.exe',
            DependencyType.SointuCompile: 'https://github.com/vsariola/sointu/releases/latest/download/sointu-Windows.zip!sointu-windows/sointu-compile.exe',
        })
    elif system() == 'Linux':
        downloadUrls.update({
            DependencyType.SointuCompile: 'https://github.com/vsariola/sointu/releases/latest/download/sointu-Linux.zip!sointu-Linux/sointu-compile',
        })

    if args.forceDownload:
        print("Clearing cache.")
        for url in downloadUrls.values():
            for deletedPath in clear_cached_path(url.value):
                print(f"Removing {deletedPath}")

    programs = {}
    for program in downloadUrls.keys():
        programs[program] = cached_path(
            url_or_filename=downloadUrls[program],
            extract_archive=True,
        )
        if system() == 'Linux':
            programs[program].chmod(programs[program].stat().st_mode | S_IXUSR | S_IXGRP | S_IXOTH)


    if args.sointuCompile is not None:
        programs[DependencyType.SointuCompile] = Path(args.sointuCompile)
            
    if system() == 'Linux':
        programs.update({
            DependencyType.Nasm: Path('nasm'),
            DependencyType.Upx: Path('upx'),
            DependencyType.Ld: Path(args.ld),
        })

    # Find required library paths
    libpaths = []
    if system() == 'Windows':
        # Find Windows SDK path.
        registry: HKEYType = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        windowsSdkKey: HKEYType = OpenKey(registry, r'SOFTWARE\WOW6432Node\Microsoft\Microsoft SDKs\Windows\v10.0')
        windowsSdkProductVersion, _ = QueryValueEx(windowsSdkKey, r'ProductVersion')
        windowsSdkInstallFolder, _ = QueryValueEx(windowsSdkKey, r'InstallationFolder')
        windowsSdkKey.Close()
        registry.Close()
        windowsSdkLibPath: Path = Path(windowsSdkInstallFolder) / 'Lib' / f'{windowsSdkProductVersion}.0' / 'um' / 'x86'
        libpaths.append(windowsSdkLibPath)

    # Determine track base name without extension.
    base, _ = splitext(basename(args.input[0]))
    dir = dirname(args.input[0])

    if args.buildFolder:
        Path(args.buildFolder).mkdir(exist_ok=True, parents=True)
    # Run sointu-compile on the track.
    with TemporaryDirectory(
        dir=args.buildFolder,
        delete=args.buildFolder is None,
    ) as temporaryDirectory:
        outputDirectory: Path = Path(temporaryDirectory)
        print('Exporting to:', outputDirectory)

        objectFileExtension: str = ""
        binaryFileExtension: str = ""
        platformPrefix: str = ""
        nasmAbi: str = ""
        if system() == 'Windows':
            objectFileExtension = '.obj'
            binaryFileExtension = '.exe'
            platformPrefix = 'win32'
            nasmAbi = 'win32'
        elif system() == 'Linux':
            objectFileExtension = '.o'
            binaryFileExtension = ''
            platformPrefix = 'elf32'
            nasmAbi = 'elf32'

        nasmArgs: list[str] = [
            str(programs[DependencyType.Nasm]),
            '-f', nasmAbi,
            '-I', str(outputDirectory),
            f'-DFILENAME="{base}.wav"',
            f'-DTRACK_INCLUDE="{outputDirectory / f'{base}.inc'}"',
        ]

        if args.delay != 0:
            nasmArgs += [
                '-DADD_DELAY',
                f'-DDELAY_MS={args.delay}',
            ]

        if args.fourKlang is not None:
            nasmArgs += [
                '-DUSE_4KLANG',
                f'-DCHANNEL_COUNT={args.channelCount}',
                f'-DSAMPLE_SIZE={args.sampleSize}',
            ]
            if args.sampleType == 'float':
                nasmArgs.append('-DSAMPLE_FLOAT')

            # Copy the track files to the output directory.
            print("copying:")
            print(args.fourKlang, "->", outputDirectory / f'{base}.asm')
            
            copyfile(args.fourKlang, outputDirectory / f'{base}.asm')
            copyfile(args.input[0], outputDirectory  / f'{base}.inc')
        else:
            # Run sointu-compile to convert the track to assembly.
            result: CompletedProcess = run([
                str(programs[DependencyType.SointuCompile]),
                '-arch', '386',
                '-e', 'asm,inc',
                '-o', outputDirectory / f'{base}.asm',
                args.input[0],
            ])

            if result.returncode != 0:
                print("Could not compile track with Sointu.")
            else:
                print("Compiled sointu track.")

        # Assemble the wav writer.
        result: CompletedProcess = run(nasmArgs + [
            str(files(sointuexemsx) / f'wav.{platformPrefix}.asm'),
            '-o', str(outputDirectory / f'wav{objectFileExtension}'),
        ])

        if result.returncode != 0:
            print("Could not assemble wav writer.")
        else:
            print("Assembled wav writer.")

        # Assemble the player.
        result: CompletedProcess = run(nasmArgs + [
            str(files(sointuexemsx) / f'play.{platformPrefix}.asm'),
            '-o', str(outputDirectory / f'play{objectFileExtension}'),
        ])

        if result.returncode != 0:
            print("Could not assemble player.")
        else:
            print("Assembled player.")

        # Assemble the track.
        result: CompletedProcess = run([
            str(programs[DependencyType.Nasm]),
            '-f', nasmAbi,
            '-I', outputDirectory,
            outputDirectory / f'{base}.asm',
            '-o', outputDirectory / f'{base}{objectFileExtension}',
        ])

        if result.returncode != 0:
            print("Could not assemble track.")
        else:
            print("Assembled track.")

        wavBinary = outputDirectory / f'{base}-wav{binaryFileExtension}'
        playBinary = outputDirectory / f'{base}-play{binaryFileExtension}'
        if system() == 'Windows':
            crinklerArgs: list[str] = [
                str(programs[DependencyType.Crinkler]),
                f'/LIBPATH:"{outputDirectory}"',
                *map(
                    lambda libpath: f'/LIBPATH:"{libpath}"',
                    libpaths,
                ),
                'Winmm.lib',
                'Kernel32.lib',
                'User32.lib',
                str(outputDirectory / f'{base}{objectFileExtension}'),
                '/COMPMODE:VERYSLOW' if args.brutal else '/COMPMODE:FAST',
            ]

            # Link wav writer.
            # Note: When using the list based api, quotes in arguments
            # are not escaped properly.
            result: CompletedProcess = run(' '.join(map(str, crinklerArgs + [
                outputDirectory / f'wav{objectFileExtension}',
                f'/OUT:{wavBinary}',
            ])), shell=True)
            if result.returncode != 0:
                print("Could not link wav writer.")
            else:
                print("Linked wav writer.")

            # Link player.
            # Note: When using the list based api, quotes in arguments
            # are not escaped properly.
            result: CompletedProcess = run(' '.join(map(str, crinklerArgs + [
                outputDirectory / f'play{objectFileExtension}',
                f'/OUT:{playBinary}',
            ])), shell=True)
            if result.returncode != 0:
                print("Could not link player.")
            else:
                print("Linked player.")
        elif system() == 'Linux':
            ldArgs: list[str] = [
                str(programs[DependencyType.Ld]),
                str(outputDirectory / f'{base}{objectFileExtension}'),
                '-no-pie',
                '-m', 'elf_i386',
                '-lc',
                '-e', 'main',
                '-I', '/usr/lib/i386-linux-gnu',
                '-dynamic-linker', '/lib/ld-linux.so.2',
            ]

            # Link wav writer.
            # Note: When using the list based api, quotes in arguments
            # are not escaped properly.
            result: CompletedProcess = run(' '.join(map(str, ldArgs + [
                outputDirectory / f'wav{objectFileExtension}',
                '-o', wavBinary,
            ])), shell=True)
            if result.returncode != 0:
                print("Could not link wav writer.")
            else:
                print("Linked wav writer.")

            # Link player.
            # Note: When using the list based api, quotes in arguments
            # are not escaped properly.
            result: CompletedProcess = run(' '.join(map(str, ldArgs + [
                outputDirectory / f'play{objectFileExtension}',
                '-o', playBinary,
                '-lasound',
            ])), shell=True)
            if result.returncode != 0:
                print("Could not link player.")
            else:
                print("Linked player.")

            if not args.disableUpx:
                # Compress wav writer using UPX.
                # Note: When using the list based api, quotes in arguments
                # are not escaped properly.
                result: CompletedProcess = run(' '.join(map(str, [
                    str(programs[DependencyType.Upx]),
                    '--best',
                    outputDirectory / f'{base}-wav{binaryFileExtension}',
                ])), shell=True)
                if result.returncode != 0:
                    print("Could not upx-compress wav writer.")
                else:
                    print("upx-compressed wav writer.")

                # Compress player using UPX.
                # Note: When using the list based api, quotes in arguments
                # are not escaped properly.
                result: CompletedProcess = run(' '.join(map(str, [
                    str(programs[DependencyType.Upx]),
                    '--best',
                    outputDirectory / f'{base}-play{binaryFileExtension}',
                ])), shell=True)
                if result.returncode != 0:
                    print("Could not upx-compress player.")
                else:
                    print("upx-compressed player.")

        # Create release archive.
        zipFile: ZipFile = ZipFile(f'{base}.zip', 'w')
        zipFile.write(filename=str(outputDirectory / f'{base}-wav{binaryFileExtension}'), arcname=f'{base}/{base}-wav{binaryFileExtension}')
        zipFile.write(filename=str(outputDirectory / f'{base}-play{binaryFileExtension}'), arcname=f'{base}/{base}-play{binaryFileExtension}')
        if args.nfo is not None:
            nfoBaseWithExt = basename(args.nfo)
            zipFile.write(filename=args.nfo, arcname='{}/{}'.format(base, nfoBaseWithExt))
        zipFile.close()

    exit(0)

# sointu-executable-msx
Easy-to-use tool to create executable music using Sointu.

It downloads nasm, Crinkler and Sointu automatically and runs them to generate an executable from Sointu track YAML files. For this purpose, it contains a small x86 assembly player and wav writer.

## Prequisites
You need a recent version of the Windows SDK installed. This can be achieved by installing either Visual Studio or MSVC build tools, and enabling the "Windows 10 SDK" workload in the installer.

## Usage
```
usage: sointu-executable-msx [-h] [-b,--brutal] [-n,--nfo NFO] [-d,--delay DELAY] input

Easy-to-use tool to create executable music using Sointu.

positional arguments:
  input             Track file to compile.

options:
  -h, --help        show this help message and exit
  -b,--brutal       Use brutal Crinkler settings (takes much longer, but executable will be smaller).
  -n,--nfo NFO      Add a NFO to the release archive.
  -d,--delay DELAY  Add a delay in ms before starting to play the track (useful for computationally heavy tracks).
```

# Build
Download and install Python 3.11 with pip (The official binary installer should do this).

Use pip to install poetry: `python -m pip install poetry`. Make sure that the Scripts subfolder of your Python installation is added to the system `PATH`. Then install the dependencies by running `poetry install`.

You can now debug the software using poetry: `poetry run python -m sointuexemsx -h`.

If you want to build the executable binary, do this by running `poetry run pyinstaller pyinstaller.spec`. The binary and release zip archive will be created in the `dist/` subfolder of the repository.

# Licenses
This program is (c) 2023 Alexander Kraus <nr4@z10.info> and licensed under GPLv3; see LICENSE for details. It downloads and uses (but does not repackage):
* Crinkler, which is copyright (c) 2005-2020 Aske Simon Christensen and Rune L. H. Stubbe. See https://github.com/runestubbe/Crinkler; or specifically https://github.com/runestubbe/Crinkler/blob/master/LICENSE.txt.
* Nasm, which is copyright (c) 1996-2010 the NASM Authors. See https://github.com/netwide-assembler/nasm; or specifically https://github.com/netwide-assembler/nasm/blob/master/LICENSE.
* Sointu, which is copyright (c) 2018 Dominik Ries and (c) 2020 Veikko Sariola. See https://github.com/vsariola/sointu; or specifically https://github.com/vsariola/sointu/blob/master/LICENSE.

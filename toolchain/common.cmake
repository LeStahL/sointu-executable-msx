# sointu-executable-msx
# Copyright (C) 2023  Alexander Kraus <nr4@z10.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


include("${CMAKE_CURRENT_LIST_DIR}/../external/cmake-find-or-download/find-or-download.cmake")

find_or_download_if_not_present(GO go.exe "https://go.dev/dl/go1.19.windows-amd64.zip" go1.19.windows-amd64.zip/go/bin/)
find_or_download_if_not_present(NASM nasm.exe "https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/win64/nasm-2.15.05-win64.zip" nasm-2.15.05/)

set(CMAKE_SIZEOF_VOID_P 4)

set(CMAKE_C_COMPILER clang)
set(CMAKE_ASM_NASM_COMPILER ${NASM})
set(CMAKE_ASM_NASM_FLAGS "-fwin32 -Ox")

set(CMAKE_ASM_NASM_LINK_LIBRARY_SUFFIX ".lib")
set(CMAKE_ASM_NASM_LINK_LIBRARY_FLAG "")
set(CMAKE_ASM_NASM_LIBRARY_PATH_FLAG "/libpath:")
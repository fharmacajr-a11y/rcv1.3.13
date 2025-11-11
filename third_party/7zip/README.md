# 7-Zip

**Version**: 24.09 (2024-11-25)  
**Architecture**: x64 (64-bit)  
**License**: GNU LGPL + unRAR restriction + BSD 3-clause  
**Official Website**: https://www.7-zip.org/

## About

7-Zip is a file archiver with a high compression ratio. This application includes the 7-Zip command-line binaries for extracting RAR and ZIP archives.

## Files Included

- `7z.exe` - 7-Zip command-line executable (x64)
- `7z.dll` - 7-Zip shared library (x64)

## Supported Formats (Unpacking)

7-Zip supports unpacking the following formats:
- **RAR** (including RAR5)
- **ZIP**
- **7z**
- **CAB, ARJ, LZH, CHM, ISO, WIM, Z, CPIO, RPM, DEB, NSIS**
- And many others

## License

7-Zip is free software distributed under the **GNU LGPL** license (with some parts under BSD 3-clause license).

The RAR decompression code is based on **unRAR** source code and has the following restriction:
> The unRAR sources cannot be used to re-create the RAR compression algorithm, which is proprietary.

For full license details, see `LICENSE.txt` in this directory.

## Source & Download

- **Homepage**: https://www.7-zip.org/
- **Source Code**: https://www.7-zip.org/download.html
- **License**: https://www.7-zip.org/license.txt

## Usage in This Project

The 7-Zip binaries are embedded in this application to provide RAR extraction capabilities without requiring users to install additional software. The binaries are automatically included during the PyInstaller build process.

## Copyright

Copyright (C) 1999-2024 Igor Pavlov

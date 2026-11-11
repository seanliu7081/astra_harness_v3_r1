# Frozen PNG encoder

`pillow-12.3.0-cp310-cp310-linux_x86_64.whl` preserves the baseline simulator's
Pillow 12.3.0 / zlib-ng 2.3.3 PNG output. It supports CPython 3.10 on Linux
x86_64 and is installed by `setup.sh` after the other simulator dependencies.
The ordinary PyPI wheel with the same Pillow version produces identical pixels
but different compressed PNG bytes, which fails the frozen observation hash.

SHA256: `7f3adb79c4f2ae36db0a44fe7748a4cb73e6e55ddd9669a36385eb63ae961c83`

The wheel contains the original Conda-forge Pillow build plus its 21 native
library dependencies. The only native binary changes are relative ELF RPATHs:
`$ORIGIN/.libs` for Pillow modules and `$ORIGIN` for bundled libraries. Wheel
metadata and RECORD were regenerated. Python source is unchanged. No original
environment path is needed at runtime; system glibc and Linux runtime libraries
remain prerequisites. This is a Linux wheel, not a manylinux compatibility claim.

`../../provenance/encoder_wheel_manifest.json` records the original Conda package
URLs and SHA256 values, library source and relocated hashes, and license names.
The wheel's `pillow-12.3.0.dist-info/licenses` directory contains Pillow's license
and all bundled native package licenses. GCC runtime libraries include the GCC
Runtime Library Exception. `../../provenance/encoder_relocation_validation.json`
records the independent extraction/import and exact initial-PNG checks.

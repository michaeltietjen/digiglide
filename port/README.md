# OS 1.12 port

DigiGlide targets Digitone II OS 1.12 (the owner's OS) and still builds for 1.11. See GLIDE_SPEC.md, "OS 1.12".

- `addrmap.py`: maps 1.11 addresses to 1.12 (code and image data by a masked byte match; RAM by the literals in
  the mapped code, every reference agreeing). `addr_1.12.json` is its checked output plus a few addresses set by
  hand, each with a reason. Addresses only: no Elektron bytes are stored here.
- `../mod/osver.py`: `DG_OS=1.12` (default) or `1.11`; `A(x)` maps a 1.11 address; `-DOSA_<1.11 hex>` for C / asm.
- `../mod/port_os.py`: sets the build tools' 1.11 constants (dnfw loader cave, area, parameter table) for 1.12.
- `harness_1.12.patch`: the emulator changes outside this repository (the skill's cfkit.py, digikit's device file).

Setup on a new machine, after the skill's `dn2setup.py`:

1. Put your own copy of `Digitone_II_OS1.12.syx` in `~/dn2-workspace/v112/` and extract sections 3 and 7 to
   `~/dn2-workspace/v112/extracted/` (dnfw: `load(read_image(path)).container.find(sid).unpack()`).
2. Apply `harness_1.12.patch` (cfkit.py, digikit's `devices/digitone-ii.toml`).
3. Make the 1.12 EMAC list: `cfdis.sh 0x40000400 0x401D0000 ~/dn2-workspace/v112/extracted/section_3.bin >
   ~/dn2-workspace/v112/extracted/section_3.dis`, then
   `cfemac.list_rows('.../v112/extracted/section_3.dis', '~/dn2-workspace/data/emac_rows_1.12.txt')`.
4. Build: `DG_OS=1.12 python3 mod/build_dg.py`; tests take `DG_OS` the same way.

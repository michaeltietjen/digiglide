"""Point the build tools (cfmod, dnfw's loader / area / paramtable) at the OS osver.OS selects.

dnfw and cfmod were written against OS 1.11 and hold its addresses as module constants. For 1.12 they are set here
from port/addr_1.12.json, never by editing those libraries. The runtime loader (dnfw csrc/runtime/loader.S) includes
dn2_111.h for the area's address: for 1.12 a copy of csrc/ with that one value changed is written into the build
directory (dnfw's code, so it stays out of the repository) and the loader is built from it.

What changes, and why it is safe (port/addrmap.py checks each):
  - the area: appended after MAIN OS, which ends 4096 bytes later on 1.12 (0x4030C980);
  - the loader's cave: the same 138 zero bytes, 0x540 later (nothing in 1.12 references them);
  - the startup calls at 0x4000053E, data_init 0x4000045C and bss_clear 0x400004B2: unchanged addresses;
  - the parameter table (0x401F7FC8 -> 0x401F83D8) and its 68-byte companion (0x4243325C -> 0x4243425C); the site
    scanners count their literals (56 bases, 55 bounds) and fail on any other count, so a wrong address cannot pass;
  - free RAM for our code (0x46800000) and the area's runtime (0x46710000): unchanged."""
import os, pathlib, re, shutil
import osver
from osver import A


def apply(build_dir):
    import cfmod
    from dnfw.patch import area, loader, paramtable as PT
    if osver.OS == '1.11':
        return
    area.AREA_VA = A(0x4030B980)
    loader.CAVE_VA, loader.LINK_VA = A(0x4028DA6E), A(0x4028DA70)
    assert loader.CALLS_VA == A(0x4000053E)
    PT.STOCK_END = A(0x4030B980)
    PT.TABLE = A(0x401F7FC8)
    PT.RUNTIME = A(0x4243325C)
    PT.NOT_THE_BOUND = tuple(A(x) for x in (0x40031FEE, 0x40032422, 0x400325E2))
    PT.SWITCH_CASES = (A(0x4006EF14),)
    PT.NOT_THIS_TIME = {A(k): v for k, v in {0x400DC7F0: 'param_set_tables_build (see dnfw paramtable.py)',
                                            0x400C241C: 'the 68-byte companion table (see dnfw paramtable.py)',
                                            0x40044828: 'a cmpa.l bound in 0x400446c2 (see dnfw paramtable.py)'}.items()}
    # the runtime loader, from a copy of dnfw's csrc with the 1.12 area address
    src = pathlib.Path(loader.SOURCE)
    dst = pathlib.Path(build_dir) / 'dnfw_csrc_112'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    h = dst / 'include' / 'dn2_111.h'
    t = h.read_text()
    t2, n = re.subn(r'#define DNFW_AREA\s+0x4030B980', f'#define DNFW_AREA      0x{A(0x4030B980):08X}', t)
    assert n == 1, 'dn2_111.h: DNFW_AREA not found'
    for name, old in (('DN2_DATA_INIT', 0x4000045C), ('DN2_BSS_CLEAR', 0x400004B2)):
        assert re.search(rf'#define {name}\s+0x{old:08X}', t2), name
    h.write_text(t2)
    loader.SOURCE = dst

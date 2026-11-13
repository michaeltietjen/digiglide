"""Which Digitone II OS DigiGlide is built and tested against: DG_OS=1.12 (default: what the owner runs) or 1.11.

All addresses in the sources are written as their OS 1.11 value (the notes and the reverse engineering are 1.11's);
A(x) gives the address in the selected OS from port/addr_1.12.json (port/addrmap.py made and checked it). An address
missing from the table is an error, never passed through: a 1.11 address in a 1.12 image is a silent crash.

Only section 3 (the ColdFire MAIN OS) differs between 1.11 and 1.12; the SHARC code (section 7) is byte-identical,
so DSP renders and their snapshots are shared."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.expanduser(os.environ.get('DN2_WORKSPACE', '~/dn2-workspace'))
OS = os.environ.get('DG_OS', '1.12')
assert OS in ('1.11', '1.12'), OS

_MAP = {}
if OS == '1.12':
    j = json.load(open(os.path.join(HERE, '..', 'port', 'addr_1.12.json')))
    _MAP = {int(k, 16): int(v['to'], 16) for k, v in j['map'].items()}

if OS == '1.11':
    STOCK_SYX = os.path.join(WS, 'Digitone_II_OS1.11.syx')
    SEC3_STOCK = os.path.join(WS, 'extracted', 'section_3.bin')
    STOCK_SHA256 = '2af43e65e3d8390b41c9f66222620f8cce027d73ed87db00c80b440f628472e0'
else:
    STOCK_SYX = os.path.join(WS, 'v112', 'Digitone_II_OS1.12.syx')
    SEC3_STOCK = os.path.join(WS, 'v112', 'extracted', 'section_3.bin')
    STOCK_SHA256 = '7e5b8a733d4ab1fdf7e5d22757f7d8eddaa3cbf71d0858874a791844c02ceb35'
    os.environ.setdefault('DT2_MAIN_IMG', SEC3_STOCK)       # digikit's emulator: the MAIN OS it resolves symbols in
PREFIX = f'DN2_{OS}_DIGIGLIDE_'
STOCK_EMU = os.path.join(WS, 'build', 'stock_emu' if OS == '1.11' else 'stock112_emu')


def A(x):
    """the selected OS's address for a 1.11 address."""
    if OS == '1.11':
        return x
    try:
        return _MAP[x]
    except KeyError:
        raise KeyError(f'{x:#010x} has no 1.12 address in port/addr_1.12.json (run port/addrmap.py and add it)') from None


def defines():
    """C / asm: -DOSA_<1.11 hex>=<address> for every mapped address (sources write OSA_4004F8FE etc.)."""
    keys = _MAP if OS == '1.12' else json.load(open(os.path.join(HERE, '..', 'port', 'addr_1.12.json')))['map']
    out = []
    for k in keys:
        k = k if isinstance(k, int) else int(k, 16)
        out.append(f'-DOSA_{k:08X}=0x{A(k):08X}')
    return out

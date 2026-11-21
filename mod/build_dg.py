"""Build DigiGlide: python3 build_dg.py [-o OUT.syx] [-D NAME=VALUE ...] [--no-ui]
Default output: $DN2_WORKSPACE/build/DN2_<OS>_DIGIGLIDE_<N>.syx (next free N: never overwrites an older build).
OS: DG_OS=1.12 (default, what the owner runs) or 1.11 (osver.py; addresses ported by port/addrmap.py).

Parts:
  - the frame hook (digiglide.c, hooks_dg.S) and the core (core/dg_core.c);
  - the UI (ui/dg_ui.c, ui/hooks_ui.S): DigiGlide's 18 parameters as records 321..338 of the parameter table, which
    is relocated so it can grow (dnfw.patch.paramtable: 56 bases repointed, 55 bounds raised by 18, as dnfw's LFO4),
    and three more SYN pages (CHORD, MOTION, SETUP) on every synth track.
The relocated table is generated from YOUR stock image into the build directory (ptable.S): it holds Elektron's
records, so it is never written into the repository.
Fails if any `__` runtime helper is linked: this toolchain's libgcc is 68020 code (notes/build_log.md, M2)."""
import argparse, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser('~/glide/.claude/skills/digitone-2-modding-skill/scripts'))
import cfmod, dn2paths as P
from dnfw.patch import paramtable as PT
import osver, port_os, preflight
from osver import A

OURS = {'__bss_start', '__bss_end', '__image_end'}
BASE = 0x40000400
GROUP_FX = 0x12                              # the kit's FX set (the delay's group): see BUF_K0
BUF_K0 = 70                                  # FX words k 70..87: no stock parameter, sent nowhere; the pages' edit buffer
PAGE_NAME_SYN = A(0x40210800)                # "SYN", WAVETONE's records' page name
UNIT_NONE = A(0x40218572)                    # "", their unit
ROW_TEXT, ROW_DIAL = 248, 240              # stock entries whose knob rows DigiGlide's records borrow (MOD, PD1)
ENTRY0 = 321

# rev 6: 18 parameters in page order (digiglide.c K_ order): CHORD, MOTION, SETUP. A record's value is the kit's FX
# word BUF_K0 + k, a buffer for the selected track; the settings themselves are in the kit's record (digiglide.c, the
# store). The rows these borrow are copied and made unlockable in ui/dg_ui.c (dg_row).
# short, long, min, max, default (indices), formatter, row
RECORDS = [
    ('TYPE', 'Chord Type', 0, 4, 0, 'dg_fmt_type', ROW_TEXT),     # build 23: 5TH
    ('EXT', 'Extension', 0, 7, 0, 'dg_fmt_ext', ROW_TEXT),
    ('KEY', 'Key', 0, 24, 0, 'dg_fmt_key', ROW_TEXT),
    ('VOIC', 'Voicing', 0, 127, 127, 'dg_fmt_voic', ROW_DIAL),
    ('POS', 'Position', 0, 127, 64, 'dg_fmt_pos', ROW_DIAL),
    ('GLID', 'Glide Time', 0, 12, 2, 'dg_fmt_glid', ROW_TEXT),
    ('PLAY', 'Play Mode', 0, 3, 0, 'dg_fmt_play', ROW_TEXT),       # CHRD STRM STRU HARP (build 19)
    ('HOLD', 'Hold', 2, 3, 2, 'dg_fmt_hold', ROW_TEXT),               # stored 2 = OFF, 3 = ON (digiglide.c HOLD_OFF)
    ('PATH', 'Glide Path', 0, 9, 0, 'dg_fmt_path', ROW_TEXT),
    ('TIME', 'Glide Timing', 0, 5, 0, 'dg_fmt_time', ROW_TEXT),   # build 23: DRON
    ('ORDR', 'Glide Order', 0, 4, 0, 'dg_fmt_ordr', ROW_TEXT),
    ('STAG', 'Stagger', 0, 6, 0, 'dg_fmt_stag', ROW_TEXT),
    ('MOVE', 'Move', 0, 9, 0, 'dg_fmt_move', ROW_TEXT),
    ('DRFT', 'Drift', 0, 50, 8, 'dg_fmt_drft', ROW_DIAL),
    ('VIB', 'Vibrato', 0, 50, 4, 'dg_fmt_vib', ROW_DIAL),
    ('SCRB', 'Scrub', 0, 127, 127, 'dg_fmt_scrb', ROW_DIAL),
    ('VCNT', 'Voice Count', 0, 4, 0, 'dg_fmt_vcnt', ROW_TEXT),   # codes: 0 OFF, 1..4 = 3..6 voices
    ('BASS', 'Bass Voice', 0, 6, 2, 'dg_fmt_bass', ROW_TEXT),
    ('SPD', 'Strum Speed', 0, 127, 64, 'dg_fmt_spd', ROW_DIAL),    # build 21: strum / harp gap, FX k 88
    ('BPAT', 'Bass Pattern', 0, 7, 0, 'dg_fmt_bpat', ROW_TEXT),     # build 23: FX k 89..92
    ('BRAT', 'Bass Rate', 0, 2, 1, 'dg_fmt_brate', ROW_TEXT),
    ('BLOM', 'Bloom', 0, 127, 64, 'dg_fmt_bloom', ROW_DIAL),
    ('STRK', 'Restrike', 0, 3, 0, 'dg_fmt_strk', ROW_TEXT),
    ('BAL', 'Bass Balance', 0, 127, 64, 'dg_fmt_bal', ROW_DIAL),   # build 24: FX k 93
    ('TUNE', 'Tuning', 0, 1, 0, 'dg_fmt_tune', ROW_TEXT),           # build 29: EQL / PURE, FX k 94
    ('FAN', 'Fan', 0, 127, 0, 'dg_fmt_fan', ROW_DIAL),              # build 29: FX k 95
]
PAGES = [('CHORD', 'DigiGlide', list(range(ENTRY0, ENTRY0 + 8))), ('MOTION', 'DigiGlide', list(range(ENTRY0 + 8, ENTRY0 + 16))),
         ('SETUP', 'DigiGlide', [ENTRY0 + 16, ENTRY0 + 17, ENTRY0 + 19, ENTRY0 + 20, ENTRY0 + 18, ENTRY0 + 21,
                                 ENTRY0 + 22, ENTRY0 + 23]),
         ('TUNE', 'DigiGlide', [ENTRY0 + 24, ENTRY0 + 25, 0, 0, 0, 0, 0, 0])]   # build 29: TUNE FAN   # build 24: VCNT BASS BPAT BRATE / SPD BLOOM STRK BAL   # entry 0 = an empty cell, as stock pages
HEAD = PT.RECORD - 8                       # entry 0 reads the 52 bytes before the table
TAIL = 8                                   # the last stock record's formatter and unit, past the table


def free_ids(stock, n):
    used = {struct.unpack_from('>I', stock, PT.TABLE - BASE + PT.RECORD * i + 40)[0] for i in range(PT.COUNT)}
    used.discard(0xFFFFFFFF)
    gaps = [v for v in range(min(used), max(used)) if v not in used]
    assert len(gaps) >= n
    return gaps[:n]


def gen_ptable(stock, path):
    """ptable.S: [head 52][320 stock records][tail 8] then DigiGlide's records, strings, page descriptors, rows."""
    blob = stock[PT.TABLE - BASE - HEAD:PT.TABLE - BASE + PT.RECORD * PT.COUNT + TAIL]
    assert len(blob) == HEAD + PT.RECORD * PT.COUNT + TAIL and len(blob) % 4 == 0
    ids = free_ids(stock, len(RECORDS))
    L = ['/* generated by build_dg.py from the stock image: Elektron data, not for the repository */',
         '    .section .rodata.dg_ptable,"a"', '    .balign 4',
         '    .globl dg_ptable, dg_pt_b16, dg_pt_b40, dg_records, dg_pages, dg_rows']

    def data(b):
        for i in range(0, len(b), 16):
            L.append('    .byte ' + ','.join(str(x) for x in b[i:i + 16]))
    L.append('dg_ptable:')                  # = the firmware's base for field +0 (table - 60 + 8)
    data(blob[:8])
    L.append('dg_pt_b16:')                  # base + 8
    data(blob[8:32])
    L.append('dg_pt_b40:')                  # base + 32
    data(blob[32:])
    L.append('dg_records:')                 # entry 321 = dg_ptable + 60 * 321
    for k, (short, long_, lo, hi, dflt, fmt, row) in enumerate(RECORDS):
        slot = BUF_K0 + k
        L.append(f'    /* entry {ENTRY0 + k}: slot {slot} {short} */')
        L.append(f'    .long {GROUP_FX}, {slot}, {lo << 8:#x}, {hi << 8:#x}, {dflt << 8:#x}, 0, 0xffffffff, '
                 f'0xffffffff, {ids[k]}, 0, dg_long_{k}, {PAGE_NAME_SYN:#x}, dg_short_{k}, {fmt}, {UNIT_NONE:#x}')
    L.append('dg_rows:')
    for short, *_, row in RECORDS:
        L.append(f'    .long {A(0x4243325C) + 68 * row:#x}   /* {short}: stock entry {row}\'s row */')
    L.append('dg_pages:')
    for p, (title, sub, ents) in enumerate(PAGES):
        L.append(f'    .long dg_title_{p}, dg_sub_{p}, ' + ', '.join(str(e) for e in ents) + ', 10')
    for k, (short, long_, *_) in enumerate(RECORDS):
        L += [f'dg_long_{k}: .asciz "{long_}"', f'dg_short_{k}: .asciz "{short}"']
    for p, (title, sub, _) in enumerate(PAGES):     # old-ABI std::string: {length, capacity, refcount -1} + chars
        for name, text in ((f'dg_title_{p}', title), (f'dg_sub_{p}', sub)):
            L += ['    .balign 4', f'    .long {len(text)}, {len(text)}, -1', f'{name}: .asciz "{text}"']
    open(path, 'w').write('\n'.join(L) + '\n')


ap = argparse.ArgumentParser()
ap.add_argument('-o')
ap.add_argument('-D', action='append', default=[])
ap.add_argument('--no-ui', action='store_true')
a = ap.parse_args()
out = a.o
if not out:
    n = 1
    while (P.BUILD / f'{osver.PREFIX}{n}.syx').exists():
        n += 1
    out = str(P.BUILD / f'{osver.PREFIX}{n}.syx')
defs = dict(d[2:].split('=', 1) for d in osver.defines())
defs.update(dict(d.split('=', 1) for d in a.D))
defs.setdefault('DG_BUILD', os.path.basename(out)[:-4].rsplit('_', 1)[-1])    # the status box and the probe's tag
gen = P.BUILD / 'digiglide_gen'
gen.mkdir(exist_ok=True)
port_os.apply(gen)
stock = cfmod.section(osver.STOCK_SYX, 3)
import hashlib
assert hashlib.sha256(open(osver.STOCK_SYX, 'rb').read()).hexdigest() == osver.STOCK_SHA256, 'not the stock OS file'
print('OS', osver.OS, osver.STOCK_SYX)
srcs = ['digiglide.c', 'core/dg_core.c', 'hooks_dg.S', 'probe.S']
entries = ['dg_stub', 'dg_tx', 'T', 'DG', 'dg_cur', 'dg_ui', 'dg_test_read', 'dg_tail_log', 'dg_chord_name', 'dg_name', 'dg_msg', 'dg_vchk', 'dg_probe_rx', 'dg_probe_tag', 'dg_probe_tx', 'dg_imported', 'dg_par', 'dg_par_set', 'dg_marked', 'dg_lock_get', 'dg_lock_put', 'dg_lock_any', 'dg_view_step', 'dg_view_locks', 'dg_lockset_stub', 'dg_lockget_stub', 'dg_lockclr_stub', 'dg_arp_in', 'dg_arp_out', 'dg_arp_single', 'dg_arp_ins', 'dg_arp_outs', 'dg_arp_last', 'dg_drone_sel', 'dg_drone_loads', 'dg_drone_req']
if not a.no_ui:
    gen_ptable(stock, gen / 'ptable.S')
    srcs += ['ui/dg_ui.c', 'ui/hooks_ui.S', str(gen / 'ptable.S')]
    entries += ['dg_count_stub', 'dg_page_stub', 'dg_row_stub', 'dg_syn_stub', 'dg_row', 'dg_on_mask', 'dg_pass_stub', 'dg_ui_page', 'dg_ui_first', 'dg_ui_locks', 'dg_ptable', 'dg_pt_b16', 'dg_pt_b40']
m = cfmod.Mod([s if os.path.isabs(s) else os.path.join(HERE, s) for s in srcs], entries=entries, init='dg_mod_init',
              include=[HERE, os.path.join(HERE, 'core')], defines=defs, stock=osver.STOCK_SYX)
ISR_MOVE = '2039' + f'{A(0x402876F8):08x}'          # move.l <ISR counter>,%d0
m.context(A(0x40025E88), '6620', 'bnes right after the hooked move: reads its flags (the stub replays the move last)')
m.context(A(0x40025E94), '4879' + f'{A(0x80005E60):08x}', 'the frame the driver sends right after: 0x80005e60')
m.jsr(A(0x40025E82), 'dg_stub', stock=ISR_MOVE, why='audio ISR: before the frame goes to the DSP -> dg_tx')
m.jsr(A(0x40026762), 'dg_arp_in', stock='4eb940029cd4', why='notes into the arp: a DigiGlide track gives its chord')
m.jsr(A(0x40026D3C), 'dg_arp_out', stock='4eb940029fa6', why='a key leaves the arp: its chord notes go')
m.jsr(A(0x4012169A), 'dg_probe_rx', stock='47f9' + f'{A(0x40207AE6):08x}',
      why='SysEx router, before the Elektron header compare: the read-only USB probe (HELLO, PEEK)')
if not a.no_ui:
    sym = {8: 'dg_ptable', 16: 'dg_pt_b16', 40: 'dg_pt_b40'}
    bases = PT.base_sites(stock, BASE)
    bounds = PT.bound_sites(stock, BASE)
    for s in bases:
        bias = s.was - (PT.TABLE - PT.RECORD)
        m.pointer(s.va, s.was, sym[bias], f'parameter table base (+{bias}) -> the relocated table')
    for s in bounds:
        m.patch(s.va, f'{s.was:08x}', f'{s.was + len(RECORDS):08x}', f'parameter entry bound {s.was} -> +{len(RECORDS)}')
    m.jsr(A(0x400C24D2), 'dg_count_stub', stock='7204202f0004', why='SYN page count: +4 on a synth track')
    m.jsr(A(0x400C24F2), 'dg_page_stub', stock='222f0008202f000c', why='SYN page descriptor: CHORD / MOTION / SETUP / TUNE')
    m.jsr(A(0x400C2418), 'dg_row_stub', stock='202f00040c8000000141', why='knob row for entries 321..346')
    m.jsr(A(0x40018118), 'dg_syn_stub', stock='4fefffe448d71c1c', why='SYN page draw (every machine): DigiGlide draws its pages')
    m.jsr(A(0x4004F8FE), 'dg_lockset_stub', stock='2f0a2f02246f000c', why='set lock: a DigiGlide row\'s lock goes to the packed lanes')
    m.jsr(A(0x4004EAA4), 'dg_lockget_stub', stock='206f00042028002c', why='get lock: a DigiGlide row\'s lock comes from the packed lanes')
    m.jsr(A(0x4004F944), 'dg_lockclr_stub', stock='2f0a2f02246f000c', why='remove lock: a DigiGlide row\'s lock leaves the packed lanes')
    m.jsr(A(0x4011D398), 'dg_pass_stub', stock='420015400020', why='end of the screen pass: the shortcut and its message')
    print(f'parameter table: {len(bases)} bases, {len(bounds)} bounds, {len(RECORDS)} records added')
m.write(out)
bad = [l.split()[-1] for l in open(out[:-4] + '/symbols.txt') if l.split()[-1].startswith('__') and l.split()[-1] not in OURS]
print(out)
print('runtime helpers linked:', bad or 'none')
if not preflight.check(out):                                # dnfw v0.50's safety rules against this OS's stock file
    os.replace(out, out + '.FAILED')
    print('PREFLIGHT FAILED: image renamed', out + '.FAILED', 'do not flash it')
    sys.exit(1)
sys.exit(1 if bad else 0)

/* DigiGlide's three SYN pages (CHORD, MOTION, SETUP) on every synth track: the value formatters of its 18 parameter records
 * and the test the page hooks ask ("is the active track a DigiGlide track?"). The records, the page descriptors and
 * the relocated parameter table are generated at build time (build_dg.py, ptable.S); the hooks are in hooks_ui.S.
 *
 * A formatter is the stock record's +52 word: void f(int32_t raw, char *buf), raw = knob << 8 (0x400c243c calls it
 * with the shared buffer 0x4243298c). Texts stay within 4 characters, so the right column clears the page dots. */
#include <stdint.h>

typedef uint32_t (*fn1)(uint32_t);
/* The app singleton. NOT its getter 0x4018a97a: that constructs the app (451,596 bytes) when this is still 0, and the
 * page readers run while the app is being built at boot, so calling it from a page hook started a second
 * construction and froze the UI, depending on boot timing (DIGIGLIDE_5/6/8 in the emulator). */
#define APP_SINGLETON (*(volatile uint32_t *)OSA_446478D0)
#define ACTIVE_TRACK ((fn1)OSA_40046BFE)                  /* (root + 48) -> active track */

int dg_synth(uint32_t t);
int32_t dg_mach(uint32_t t);
int32_t dg_par(uint32_t t, uint32_t k);
void dg_ui_sync(uint32_t t);
int dg_vcnt_on(int32_t raw);
uint8_t dg_knob(int32_t raw, uint32_t k);
const char *dg_ui_step(volatile uint8_t *screen, uint32_t track);

static int32_t active_track(void)
{
    uint32_t root = APP_SINGLETON;
    if (!root)
        return -1;                                      /* still booting */
    return (int32_t)ACTIVE_TRACK(root + 48);
}

/* the pages show on every synth track (VCNT, DigiGlide's switch, has to be reachable while it is OFF): the hooks ask
 * for SYN page type `type`, which is the machine */
int dg_ui_active(uint32_t type)
{
    int32_t t = active_track();
    return t >= 0 && type <= 3 && dg_mach((uint32_t)t) == (int32_t)type;
}

/* the knob row of DigiGlide's record k: the stock row dg_rows names (MOD's for a list, PD1's for a dial), copied, with
 * flag bit 3 set and its randomiser emptied. The records' values are FX words now, and stock files a p-lock or a
 * randomised value under (track, k) as if k were a sound slot: either would land in the sound's slots 70..87, the
 * filter envelope (naturarum/dn2-cfw docs/parameter-table-growth.md 5.1, rule 5). Row: +0 flags (a lock needs bits 0
 * and 3 clear), +0x24 the randomiser's std::function (16 bytes; 61 stock rows have none). Rebuilt on every call:
 * the stock rows are built at boot, after the first readers run. */
extern const uint32_t dg_rows[];
static uint32_t rowbuf[18][17];
uint32_t dg_row(uint32_t k)
{
    const uint32_t *s = (const uint32_t *)dg_rows[k];
    uint32_t *d = rowbuf[k], i;
    for (i = 0; i < 17; i++)
        d[i] = s[i];
#ifdef DG_LOCKABLE                                      /* experiment (build 17): leave six rows lockable */
    if (!((DG_LOCKABLE >> k) & 1))
#endif
    d[0] |= 8;
    d[9] = d[10] = d[11] = d[12] = 0;
    return (uint32_t)d;
}

static void put(char *buf, const char *s)
{
    while ((*buf++ = *s++))
        ;
}

static void num(char *buf, int32_t v)
{
    char t[8];
    int n = 0;
    if (v < 0) {
        *buf++ = '-';
        v = -v;
    }
    do {
        t[n++] = (char)('0' + v % 10);
        v /= 10;
    } while (v && n < 7);
    while (n)
        *buf++ = t[--n];
    *buf = 0;
}

static void pick(char *buf, int32_t i, const char *const *names, int32_t n)
{
    if (i < 0)
        i = 0;
    if (i >= n)
        i = n - 1;
    put(buf, names[i]);
}

static const char *const TYPE[] = {"MAJ", "MIN", "SUS", "DIM"};
static const char *const EXT[] = {"NONE", "6", "7", "MAJ7", "9", "6+9", "7+9", "M7+9"};
static const char *const NOTE[] = {"C", "C#", "D", "EB", "E", "F", "F#", "G", "AB", "A", "BB", "B"};
static const char *const BASS[] = {"OFF", "FL-2", "FL-1", "FOL", "SL-2", "SL-1", "SOLO"};
static const char *const MOVE[] = {"NONE", "BLOM", "CAS+", "CAS-", "SPRL", "SWOP", "SCAT", "CONV", "FALL",
                                   "EVOL"};
static const char *const GLID[] = {"0", "1/16", "1/8", "1/4", "1/2", "1", "2", "4", "8", "16", "15s", "30s", "60s"};
static const char *const PATH[] = {"SMTH", "LIN", "EASE", "SWEL", "BNCE", "LATE", "SNAP", "WOBL", "SEMI", "SCAL"};
static const char *const TIME[] = {"TOGR", "DIST", "BLAG", "BLED", "LOOS"};
static const char *const ORDR[] = {"TOGR", "LOW", "HIGH", "OUTI", "RAND"};
static const char *const STAG[] = {"0", "0.5", "1", "2", "3", "5", "8"};
static const char *const ONOFF[] = {"OFF", "ON"};

/* every value goes through dg_knob: a stored value outside the parameter's range shows (and plays) as its default.
 * Parameter numbers are digiglide.c's K_ order (the pages' order). */
void dg_fmt_type(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 0), TYPE, 4); }
void dg_fmt_ext(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 1), EXT, 8); }
void dg_fmt_key(int32_t raw, char *buf)                 /* OFF, C..B (major), Cm..Bm (minor) */
{
    uint8_t k = dg_knob(raw, 2);
    if (!k) {
        put(buf, "OFF");
        return;
    }
    put(buf, NOTE[(k - 1) % 12]);
    while (*buf)
        buf++;
    put(buf, k > 12 ? "m" : "");
}
void dg_fmt_voic(int32_t raw, char *buf) { num(buf, dg_knob(raw, 3)); }
void dg_fmt_pos(int32_t raw, char *buf) { num(buf, (int32_t)dg_knob(raw, 4) - 64); }
void dg_fmt_glid(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 5), GLID, 13); }
void dg_fmt_play(int32_t raw, char *buf) { (void)raw; put(buf, "CHRD"); }
void dg_fmt_hold(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 7), ONOFF, 2); }
void dg_fmt_path(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 8), PATH, 10); }
void dg_fmt_time(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 9), TIME, 5); }
void dg_fmt_ordr(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 10), ORDR, 5); }
void dg_fmt_stag(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 11), STAG, 7); }
void dg_fmt_move(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 12), MOVE, 10); }
void dg_fmt_drft(int32_t raw, char *buf) { num(buf, dg_knob(raw, 13)); }
void dg_fmt_vib(int32_t raw, char *buf) { num(buf, dg_knob(raw, 14)); }
void dg_fmt_scrb(int32_t raw, char *buf) { num(buf, dg_knob(raw, 15)); }
void dg_fmt_vcnt(int32_t raw, char *buf)
{
    uint8_t c = dg_knob(raw, 16);
    if (c)
        num(buf, c + 2);
    else
        put(buf, "OFF");
}
void dg_fmt_bass(int32_t raw, char *buf) { pick(buf, dg_knob(raw, 17), BASS, 7); }

/* ---------------------------------------------------------------- the page itself
 * The stock knob rows draw a value with their own pictures and texts (MOD's glyphs, MULT's "BPM n"), not with a
 * record's formatter, and every machine draws its SYN pages its own way, so DigiGlide's pages are drawn here, in
 * place of the whole stock page draw 0x40018118(view, canvas) (hooks_ui.S, dg_syn_stub): each cell is the parameter's
 * value text (from its formatter) over its label; then the level meter and the page dots, as the stock grid's tail.
 * The values are the track's (the store, digiglide.c); encoders and the header's value line go through the records.
 * Canvas: 128 x 64, y up from the bottom; the grid's cells are 26 wide from x 24. */
#define TEXT ((void (*)(void *, uint32_t, int, int, int, const char *, ...))OSA_4011545C)
#define FILL ((void (*)(void *, int, int, int, int, int))OSA_40114954)   /* mode -1: invert */
#define PAGE_COUNT ((int (*)(void *))OSA_400173CA)
#define PAGE_DOTS ((void (*)(void *, void *, int, int, int))OSA_4006598A)
#define PAGE_TABLE ((volatile int32_t *)OSA_42432AD4)     /* 4 longs a machine: its own page count first */
#define FONT OSA_44507ED8
#define CENTRED 2

static void *method(void *obj, int offset)
{
    return *(void **)(*(char **)obj + offset);
}

typedef void (*fmt_fn)(int32_t, char *);
#define NP 18                                           /* CHORD 0..7, MOTION 8..15, SETUP 16..17 */
static const fmt_fn FMT[NP] = {dg_fmt_type, dg_fmt_ext, dg_fmt_key, dg_fmt_voic, dg_fmt_pos, dg_fmt_glid,
                               dg_fmt_play, dg_fmt_hold, dg_fmt_path, dg_fmt_time, dg_fmt_ordr, dg_fmt_stag,
                               dg_fmt_move, dg_fmt_drft, dg_fmt_vib, dg_fmt_scrb, dg_fmt_vcnt, dg_fmt_bass};
static const char *const LABEL[NP] = {"TYPE", "EXT", "KEY", "VOIC", "POS", "GLID", "PLAY", "HOLD",
                                      "PATH", "TIME", "ORDR", "STAG", "MOVE", "DRFT", "VIB", "SCRB", "VCNT", "BASS"};
#define VALUE_Y_TOP 39
#define LABEL_Y_TOP 29
#define VALUE_Y_BOT 12
#define LABEL_Y_BOT 2

uint32_t dg_ui_locks;                                   /* always 0 since rev 6 (the pages show no locks); tests read it */

/* bit t: DigiGlide is on on track t + 1 (SETUP shows it; tests) */
uint32_t dg_on_mask(void)
{
    uint32_t t, m = 0;
    for (t = 0; t < 16; t++)
        if (dg_synth(t) && dg_vcnt_on(dg_par(t, 16)))
            m |= 1u << t;
    return m;
}

static void draw_page(void *view, void *canvas, uint32_t track, int dg_page, int page, int pages)
{
    int i;
    for (i = 0; i < 8; i++) {
        int k = dg_page * 8 + i, top = i < 4, cx = 24 + 26 * (i & 3) + 13;
        int vy = top ? VALUE_Y_TOP : VALUE_Y_BOT, ly = top ? LABEL_Y_TOP : LABEL_Y_BOT;
        char buf[12];
        if (k >= NP)
            continue;                                   /* SETUP's empty cells */
        FMT[k](dg_par(track, (uint32_t)k), buf);
        TEXT(canvas, FONT, cx, vy, CENTRED, "%.4s", buf);
        TEXT(canvas, FONT, cx, ly, CENTRED, "%s", LABEL[k]);
    }
    dg_ui_locks = 0;
    if (dg_page == 2) {                                 /* SETUP's lower row: which tracks have DigiGlide on, 1..16 */
        uint32_t m = dg_on_mask(), t;                   /* (a track's last digit where it is on, a dot where not) */
        char map[17];
        for (t = 0; t < 16; t++)
            map[t] = (m >> t) & 1 ? (char)('0' + (t + 1) % 10) : '.';
        map[16] = 0;
        TEXT(canvas, FONT, 76, VALUE_Y_BOT, CENTRED, "%s", map);
        TEXT(canvas, FONT, 76, LABEL_Y_BOT, CENTRED, "%s", "ON: TRACKS 1-16");
    }
    ((void (*)(void *, void *, int))method(view, 184))(view, canvas, 0);   /* the level meter */
    if (pages > 1)
        PAGE_DOTS(view, canvas, pages, page, 7);
}

int32_t dg_ui_page = -1;                                 /* the SYN page last drawn (tests navigate by it) */
int32_t dg_ui_first = -1;                                /* the first DigiGlide page of the track last drawn (tests) */
static int dg_page_shown;                               /* a DigiGlide page was drawn in this screen pass */

/* from dg_syn_stub: draw a DigiGlide page -> 1, or 0 for the stock draw */
int dg_syn_draw(void *view, void *canvas)
{
    int page = ((int (*)(void *))method(view, 132))(view), first;
    int32_t t = active_track();
    dg_ui_page = page;
    if (t < 0 || !dg_synth((uint32_t)t))
        return 0;
    first = PAGE_TABLE[4 * dg_mach((uint32_t)t)];
    dg_ui_first = first;
    if (page < first || page >= first + 3)
        return 0;
    dg_ui_sync((uint32_t)t);                            /* a knob turned since the last pass shows now */
    draw_page(view, canvas, (uint32_t)t, page - first, page, PAGE_COUNT(view));
    dg_page_shown = 1;
    return 1;
}

/* ---------------------------------------------------------------- the shortcut's message
 * From dg_pass_stub at the end of every screen pass (0x4011d398, after every layer has drawn on `canvas`, before the
 * pass clears the screen's "redraw due" flag and the panel is sent the frame): the shortcut acts here, in the UI task,
 * and its message is drawn over everything, a framed box across the middle of the screen. */
const char *dg_dbg_line(uint32_t which, uint32_t track);
const char *dg_chord_name(uint32_t track);
void dg_overlay(volatile uint8_t *screen, void *canvas)
{
    int32_t t = active_track();
    const char *text = dg_ui_step(screen, t < 0 ? 0xFF : (uint32_t)t);
    const char *d1 = dg_dbg_line(0, t < 0 ? 0 : (uint32_t)t);
    if (d1) {                                           /* the status box, at the bottom of the screen */
        FILL(canvas, 0, 44, 127, 63, 0);
        TEXT(canvas, FONT, 64, 46, CENTRED, "%s", d1);
        TEXT(canvas, FONT, 64, 55, CENTRED, "%s", dg_dbg_line(1, 0));
    }
    if (dg_page_shown && !d1) {                         /* on a DigiGlide page: the sounding chord, over the title */
        const char *nm = dg_chord_name(t < 0 ? 0xFF : (uint32_t)t);
        if (nm) {
            FILL(canvas, 19, 53, 127, 63, 0);
            TEXT(canvas, FONT, 73, 55, CENTRED, "%s", nm);
        }
    }
    dg_page_shown = 0;
    if (!text)
        return;
    FILL(canvas, 4, 21, 123, 43, 1);
    FILL(canvas, 6, 23, 121, 41, 0);
    TEXT(canvas, FONT, 64, 29, CENTRED, "%s", text);
}

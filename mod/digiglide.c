/* DigiGlide: Brickglide's chord brain on a Digitone II track (ColdFire side, spec rev 3).
 *
 * Hook: dg_stub (hooks_dg.S) runs in the audio ISR right before the driver sends the 2688-byte frame at 0x80005e60 to
 * the DSP; dg_tx() rewrites that frame for a DigiGlide chord:
 *   - the track reserves 6 voices through the stock VOICE menu (VOICES = 6), so stock plays it only on DSP voices 0..5
 *     and gives them to no other track (notes/open_questions.md, Q1);
 *   - when stock starts a note there (the "source" voice) on a synth track whose VCNT is on, the core
 *     (core/dg_core.c, the M1 model in fixed point) plans the chord: dg_trig on the trig, dg_gate_off when the source
 *     is released, dg_block every block;
 *   - every started DigiGlide voice gets the source's sound record, velocity, curve, level, machine and track (copied
 *     every block, so modulation and envelopes follow the source), its own pitch in the note word, and its pan;
 *   - a voice attacks only when its gate opens (fresh chord); a chord change while sounding only moves note words.
 *
 * Frame layout (ColdFire view, big-endian halfwords): +0x02+2v note << 8, +0x22/+0x26 note-on mask, +0x24/+0x28
 * note-off mask, +0x34+2v velocity, +0x54+2v velocity curve, +0x74+2v level, +0x94+2v machine, +0xda+146v sound
 * record (slot 89, amp pan, at +128), +0xa5a+2v voice -> track.
 *
 * Parameters (rev 6): 18 per track, kept in the kit (the store, below), read at every event. A value outside the
 * parameter's range reads as its default. SCRB is read every block while a chord sounds, so turning it scrubs the
 * glide live. The pattern seed is 0. Until image 14 they were sound slots of a WAVETONE sound, with p-locks.
 *
 * The switch is VCNT, stored as a code: 0 = OFF, 1..4 = 3..6 voices. Only those exact values turn DigiGlide on;
 * anything else is OFF, and OFF is exactly stock:
 *   - a trig whose VCNT is OFF plays as a stock note; a DigiGlide chord still sounding
 *     releases (note-offs), and each of its voices is given back to stock the moment stock starts a note on it;
 *   - switching OFF while a chord sounds (knob or shortcut) releases it the same way, at the next block;
 *   - switching on takes effect at the next trig.
 * Released DigiGlide voices keep the pitch DigiGlide gave them while they ring out (no jump in the release tail).
 * With no DigiGlide voice left the frame is untouched.
 *
 * Shortcut: [FUNC] + push encoder E (VCNT's own knob on HARMONY; unused in stock 1.11 on every page,
 * experiments/m4_funcany_mem.py) flips the active track's VCNT between OFF and the last voice count it had (5 if
 * none), and shows "DIGIGLIDE ON (n VOICES)" / "DIGIGLIDE OFF". The ISR only spots the press (the key-held bitmap
 * 0x445a1e30) and asks the screen for a redraw; the change and the message are made in the UI task, at the end of the
 * screen pass (ui/dg_ui.c, dg_overlay).
 */
#include "core/dg_core.h"

#define FRAME ((volatile uint8_t *)OSA_80005E60)
#define TEMPO_WORD (*(volatile uint32_t *)OSA_402A0DEC)    /* BPM * 120 */
#define PLAYHEAD ((volatile uint8_t *)OSA_446483D0)        /* + track: current step */
#define SOUNDS (*(uint8_t *volatile *)OSA_800052A0)       /* live sounds: + 52 + 1163 t */
#define PLAYING (*(uint8_t *volatile *)OSA_42C5A9A0)      /* playing pattern; its lock table at +97872 */
#define KEYS_HELD ((volatile uint8_t *)OSA_445A1E30)       /* bit (code - 1) */
#define PLAY_FLAG (*(volatile uint32_t *)OSA_42C5A994)     /* 1 while the sequencer plays */
#define MUTE_MASK (*(volatile uint16_t *)OSA_8000521A)     /* bit t: track t + 1 is muted (1.12, by experiment) */
#define CODE_STOP 21
#define CODE_ENC_H 48
#define CODE_ENC_G 47
#define WIN_BLOCKS 60                                   /* notes within 40 ms are one chord event */
#define EV_MAX 8
#define CODE_FUNC 17
#define CODE_ENC_E 45
/* rev 5 parameters, in page order: CHORD (TYPE EXT KEY VOIC / POS GLID PLAY HOLD), MOTION (PATH TIME ORDR STAG /
 * MOVE DRFT VIB SCRB), SETUP (VCNT BASS). */
enum { K_TYPE, K_EXT, K_KEY, K_VOIC, K_POS, K_GLID, K_PLAY, K_HOLD, K_PATH, K_TIME, K_ORDR, K_STAG, K_MOVE, K_DRFT,
       K_VIB, K_SCRB, K_VCNT, K_BASS, K_SPD, K_BPAT, K_BRATE, K_BLOOM, K_STRK, K_BAL, K_TUNE, K_FAN, DG_NP };
#define ST_NP 18                                        /* the 18 a track images <= 20 kept (K_TYPE..K_BASS) */
#define HOLD_OFF 0x0200                                 /* HOLD's two values double as "this track was set up for
                                                         * DigiGlide": a store that was never written holds 0 */
#define HOLD_ON 0x0300
/* rev 6: where the settings live (the store, below) */
#define LIVE_KITS OSA_4210C08C                          /* the 129 live kits, 0x5d71 bytes each; SOUNDS = the current */
#define KIT_STRIDE 0x5d71
#define IMAGE_KITS (OSA_405CD96C + 0xae0200)            /* the working project image's kit records, 0x2a00 each */
#define REC_STRIDE 0x2a00
#define REC_USED 0x28af                                 /* stock's kit record ends here (0xbacef00c at +0x28ab) */
#define FXBUF 0x48e4                                    /* the live kit's FX words (2 B, by k), after its 16 sounds */
#define BUF_K0 70                                       /* FX k 70..87: unused by stock, the pages' edit buffer */
#define CODE_ENC_F 46
#define MINE ((1u << DG_NV) - 1)                        /* DSP voices 0..5 */
#define RSET_OFF (0xda + 134)                           /* record slot 92 (amp envelope reset), 256 = on */
#define PAN_OFF (0xda + 128)                            /* record slot 89 (amp pan), raw knob << 8 */
#ifndef DG_BUILD
#define DG_BUILD 0
#endif
#define DG_STR(x) #x
#define DG_XSTR(x) DG_STR(x)
extern char dg_msg[28];
static char *dg_put(char *d, const char *s)
{
    while (*s)
        *d++ = *s++;
    *d = 0;
    return d;
}
#define MSG_BLOCKS 2000                                 /* the shortcut's message: 1.3 s */

static inline uint16_t rd16(volatile uint8_t *f, uint32_t o) { return *(volatile uint16_t *)(f + o); }
static inline void wr16(volatile uint8_t *f, uint32_t o, uint16_t v) { *(volatile uint16_t *)(f + o) = v; }

/* build 32: two chord slots. Each DigiGlide track that sounds has its own engine and its own state, so two tracks
 * can play chords at once (owner, image 31: a drone on one track, glides on another). A third track that plays while
 * both slots sound gets stock's single notes, as a second one did through image 31. Everything a chord owns is kept
 * NE times; the names below mean "the slot the hook is working on" (sel). Only the hook (dg_tx) changes the slot and
 * it puts slot 0 back before it returns, so code outside the hook reads slot 0 by these names (the tests, and the
 * symbols DG, dg_ui, dg_name, dg_tail_log, which are slot 0's) and names another slot explicitly. */
#define NE 2
#ifdef DG_PROF                                          /* a profiling build: the hook's parts stay apart */
#define NI __attribute__((noinline))
#else
#define NI
#endif
static uint32_t cx;                                     /* the slot in work */
static void sel(uint32_t s);
dg_track TS[NE];                                        /* the core's state (BSS, zeroed by the loader) */
static dg_track *tp = TS;
#define T (*tp)

struct dg_state {
    uint32_t blocks;                                    /* hook calls (proves the hook is live) */
    uint32_t trigs;                                     /* DigiGlide trigs seen */
    int32_t src;                                        /* DSP voice stock started for the current chord */
    uint32_t active;                                    /* 1 while a DigiGlide chord is engaged (gates may be on) */
    uint32_t was_on;                                    /* gates sent last block */
    uint32_t last_step, last_tempo, last_note;          /* what the last trig used (tests) */
    uint8_t step_log[16];                               /* step of trig k at [k & 15] (tests) */
    int32_t track;                                      /* the DigiGlide track of the current chord */
    uint32_t locks;                                     /* last trig: bit k = parameter k came from a p-lock */
    uint32_t ctl;                                       /* DSP voices DigiGlide drives (releasing ones included) */
    uint32_t stock_trigs;                               /* trigs on a WAVETONE track played as stock (VCNT OFF) */
    uint32_t combo_was, combo_req;                      /* the shortcut: keys last block, a press to handle */
    uint32_t msg_until;                                 /* the message shows until this block */
    volatile uint8_t *screen;                           /* the UI's screen object (set by dg_overlay) */
    /* rev 4: DigiGlide owns the track's notes */
    volatile uint8_t *vdata;                            /* the kit's voice config (5 B a track, +1 = VOICES), from the UI */
    uint32_t base, nres;                                /* the track's reserved DSP voices: base .. base + nres - 1 */
    uint32_t held;                                      /* DSP voices whose stock note DigiGlide swallowed, still held */
    uint32_t swallowed;                                 /* stock note-ons swallowed so far (tests) */
    uint32_t ev_start, ev_open, ev_n, ev_chordy, ev_fired, ev_ident, ev_latched;
    uint8_t ev_notes[EV_MAX];
    uint32_t gate_open;                                 /* the chord's gate is open (not yet released) */
    uint32_t latched, l_ident, l_ident2;                /* a latched chord sounds; what it is */
    uint32_t play_was, stop_was, latch_was, latch_req;
    uint32_t ev_seq;                                    /* the event is a sequenced trig, not a key played by hand */
    uint32_t ev_legato, snd_sig;                        /* a key was still down when the event began; the sound's name hash */
    uint32_t def_was, def_req, sig;                     /* the defaults shortcut; the chord settings last played */
    uint32_t dbg_base, dbg_nres, dbg_v;
    uint32_t dbg, dbg_was, dbg_req;                     /* the status box ([FUNC] + push encoder G) */
    uint32_t seen_on, seen_other;                       /* note-ons seen on the DigiGlide track / refused (no voices) */
    uint32_t off_block, tail;                           /* the last release, how long it rings (blocks) */
    uint32_t last_cw, rev_block, reattack;              /* the last chord word; the last re-voicing; GLID 0 retrigger */
    uint32_t events, releases;                          /* chord events fired / "same chord again" releases (tests) */
    uint32_t owed, lmask;                               /* build 33: blocks the engine is behind; its last mask */
    uint32_t hurry;
    uint32_t pend_on, pend_off;                         /* build 34: edges worked out, sent on the next (light) frame */                                     /* build 33: a strike or a release waits: no light block */
} DGS[NE];
static struct dg_state *dgp = DGS;
#define DG (*dgp)                                        /* the slot's */
#define GL (DGS[0])                                     /* the fields there is one of (blocks, the UI's, counters) */

uint32_t dg_tail_log_s[NE];
#define dg_tail_log (dg_tail_log_s[cx])
//                                 /* bit 0 = the last trig glided from a ringing chord, ... (tests) */
dg_params dg_cur_s[NE];
#define dg_cur (dg_cur_s[cx])
//                                     /* the parameters of the last trig */
char dg_name_s[NE][16];
#define dg_name (dg_name_s[cx])
//                                     /* the chord that sounds, by name (the pages show it) */
uint8_t dg_ui_s[NE][DG_NP];
#define dg_ui (dg_ui_s[cx])
//                                 /* the 18 parameters as last read for an event (tests, UI) */
/* ---------------------------------------------------------------- rev 6: the settings belong to the track
 * Until image 14 the 18 parameters were sound slots 50..64, 93, 94 and 65 of a WAVETONE sound (the only machine that
 * leaves 50..64 alone), so DigiGlide was WAVETONE's and a sound load took it away. Now they are 18 bytes a track in
 * the kit: any FM TONE, WAVETONE, FM DRUM or SWARMER sound can be loaded on the track and the chords stay.
 *
 * The store is in the kit's record of the working project image (the copy the box keeps across power-off and writes
 * with a project SAVE): the record is 0x28af bytes in a 0x2a00-byte slot, and stock neither writes nor reads the 337
 * bytes after it (naturarum/dn2-cfw notes/T6.0, read from the 1.12 serializer and loader; in the emulator a pattern
 * written there survives a sound edit, a pattern save, a reload and playing; on the owner's unit all 129 records had
 * them at zero). Layout at record + 0x28af: "DGK1", then 16 tracks x 18 bytes in K_ order, each the knob value;
 * VCNT 0 = OFF, 1..4 = 3..6 voices; HOLD 2 = off, 3 = on, and anything else there means the track was never set up
 * (it reads as the defaults, OFF). Nothing is written to a kit until a DigiGlide setting on it is changed.
 * What this does not do yet: SAVE KIT, kit copy / paste, the +Drive kit library and exports go through stock's kit
 * serializer, which does not carry these bytes. The settings stay with the pattern's kit inside the project.
 * P-locks: see par_at. */
static const uint8_t UISLOT[DG_NP] = {50, 51, 52, 53, 55, 93, 65, 94, 59, 60, 61, 62, 57, 63, 64, 58, 54, 56};   /* images <= 14 */
static const uint8_t PMAX[DG_NP] = {4, 7, 24, 127, 127, 12, 3, 1, 9, 5, 4, 6, 9, 50, 50, 127, 4, 6, 127, 7, 2, 127, 3, 127, 1, 127};
static const uint8_t PDEF[DG_NP] = {0, 0, 0, 127, 64, 2, 0, 0, 0, 0, 0, 0, 0, 8, 4, 127, 0, 2, 64, 0, 1, 64, 0, 64, 0, 0};   /* owner: VOIC 127, GLID 1/8 */

static volatile uint8_t *sound_of(uint32_t t)
{
    return SOUNDS + 52 + 1163 * t;
}

static int32_t sound_slot(uint32_t t, uint32_t slot)    /* sounds sit at odd addresses: bytewise */
{
    volatile uint8_t *snd = sound_of(t);
    return (snd[0x14 + 2 * slot] << 8) | snd[0x15 + 2 * slot];
}

int32_t dg_mach(uint32_t t)                             /* the track's machine: 0 FM TONE, 1 WAVETONE, 2 FM DRUM, */
{                                                       /* 3 SWARMER, 4 MIDI; -1 = no such track */
    if (t >= 16 || !SOUNDS)
        return -1;
    return sound_of(t)[0xDE];
}

int dg_synth(uint32_t t)                                /* DigiGlide plays every synth machine (and shows its pages) */
{
    int32_t m = dg_mach(t);
    return m >= 0 && m <= 3;
}

int dg_vcnt_on(int32_t raw)                             /* VCNT's exact on-codes: 3..6 voices */
{
    return raw == 0x100 || raw == 0x200 || raw == 0x300 || raw == 0x400;
}

static uint8_t *volatile st_sounds;
static volatile uint8_t *volatile st_cand;

/* the current kit's store (its record's spare bytes), or 0 while there is no valid record */
static volatile uint8_t *store(void)
{
    uint8_t *snd = SOUNDS;
    volatile uint8_t *r;
    if (snd != st_sounds) {
        uint32_t d = (uint32_t)snd - LIVE_KITS, i = d / KIT_STRIDE;
        st_cand = snd && d == i * KIT_STRIDE && i < 129 ? (volatile uint8_t *)(IMAGE_KITS + REC_STRIDE * i) : 0;
        st_sounds = snd;
    }
    r = st_cand;
    if (!r || r[0] != 0xbe || r[1] != 0xef || r[2] != 0xba || r[3] != 0xce)
        return 0;
    if (r[REC_USED - 4] != 0xba || r[REC_USED - 3] != 0xce || r[REC_USED - 2] != 0xf0 || r[REC_USED - 1] != 0x0c)
        return 0;
    return r + REC_USED;
}

/* build 23: the store is "DGK2" + 16 bytes a track: 8 settings that need a byte (KEY VOIC POS DRFT VIB SCRB SPD
 * BLOOM), then 16 nibbles for the small ones (HOLD's nibble, 2 or 3, still marks a track that has settings; 0 = none).
 * 4 + 256 bytes of the 337 spare. Kits saved by images <= 22 hold "DGK1" (16 x 18 bytes, then SPD's 16 bytes as value
 * + 1): they are read as they are, and rewritten as DGK2 at the kit's first DigiGlide edit (st_convert). */
#define ST_TRK 16
#define ST_V2 (4 + 16 * ST_TRK)
#define ST_V1 (4 + 16 * ST_NP + 16)
/* where each parameter lives in a track's 16 bytes: 0..7 a byte, 16 + n nibble n of bytes 8..15 (high nibble first) */
static const uint8_t ST_LOC[DG_NP] = {16, 17, 0, 1, 2, 18, 19, 20, 21, 22, 23, 24, 25, 3, 4, 5, 26, 27, 6, 28, 29, 7, 30, 32, 33, 34};
/* 32: build 24's BAL, a byte a track after the 16 tracks' bytes (+260 + t), as value + 1 (0: the default, so a kit
 * saved by image 23 reads 64). 33, 34: build 29's TUNE (+276 + t) and FAN (+292 + t), the same way: 308 bytes of
 * the 337 spare */
#define ST_END (ST_V2 + 48)
static uint8_t st_old[ST_V1];                           /* a DGK1 kit while it is rewritten (the ISR reads it here) */
static volatile uint8_t *volatile st_conv;

static int st_ver(volatile uint8_t *p)
{
    if (p == st_conv)
        return 1;
    if (p[0] != 'D' || p[1] != 'G' || p[2] != 'K')
        return 0;
    return p[3] == '1' ? 1 : p[3] == '2' ? 2 : 0;
}

static int st_ok(volatile uint8_t *p) { return st_ver(p) != 0; }

static uint32_t st_get2(volatile uint8_t *p, uint32_t t, uint32_t k)
{
    volatile uint8_t *q = p + 4 + ST_TRK * t;
    uint32_t c = ST_LOC[k], n, b;
    if (c >= 32) {
        b = p[ST_V2 + 16 * (c - 32) + t];
        return b ? b - 1u : PDEF[k];
    }
    if (c < 16)
        return q[c];
    n = c - 16;
    b = q[8 + n / 2];
    return n & 1 ? b & 15 : b >> 4;
}

static void st_put2(volatile uint8_t *p, uint32_t t, uint32_t k, uint32_t v)
{
    volatile uint8_t *q = p + 4 + ST_TRK * t;
    uint32_t c = ST_LOC[k], n;
    if (c >= 32) {
        p[ST_V2 + 16 * (c - 32) + t] = (uint8_t)(v > 254 ? PDEF[k] + 1u : v + 1u);
        return;
    }
    if (c < 16) {
        q[c] = (uint8_t)v;
        return;
    }
    if (v > 15)
        v = k == K_HOLD ? 2 : PDEF[k];
    n = c - 16;
    q += 8 + n / 2;
    *q = (uint8_t)(n & 1 ? (*q & 0xF0) | v : (*q & 0x0F) | v << 4);
}

static uint32_t st_get1(volatile uint8_t *p, uint32_t t, uint32_t k)   /* a DGK1 kit (or its copy) */
{
    uint8_t b;
    if (p == st_conv)
        p = st_old;
    if (k < ST_NP)
        return p[4 + ST_NP * t + k];
    if (k == K_SPD) {
        b = p[4 + 16 * ST_NP + t];
        return b ? b - 1u : PDEF[k];
    }
    return PDEF[k];
}

static uint32_t st_get(volatile uint8_t *p, uint32_t t, uint32_t k)
{
    return st_ver(p) == 2 ? st_get2(p, t, k) : st_get1(p, t, k);
}

static void st_convert(volatile uint8_t *p)             /* DGK1 -> DGK2, every track's settings kept */
{
    uint32_t i, t, k;
    for (i = 0; i < ST_V1; i++)
        st_old[i] = p[i];
    st_conv = p;                                        /* from here readers use the copy */
    for (i = 4; i < ST_V1; i++)
        p[i] = 0;
    for (t = 0; t < 16; t++) {
        uint8_t h = st_old[4 + ST_NP * t + K_HOLD];
        if (h != 2 && h != 3)
            continue;
        for (k = 0; k < DG_NP; k++)
            st_put2(p, t, k, st_get1(p, t, k));
    }
    p[3] = '2';
    st_conv = 0;
}

int dg_marked(uint32_t t)                               /* the track has DigiGlide settings of its own in this kit */
{
    volatile uint8_t *p = store();
    uint32_t h;
    if (!p || t >= 16 || !st_ok(p))
        return 0;
    h = st_get(p, t, K_HOLD);
    return h == 2 || h == 3;
}

/* parameter k of track t as its raw code (the knob value << 8, as a sound slot held it): the store's, else the default */
int32_t dg_par(uint32_t t, uint32_t k)
{
    if (k >= DG_NP)
        return 0;
    if (dg_marked(t))
        return (int32_t)(st_get(store(), t, k) << 8);
    return k == K_VCNT ? 0 : k == K_HOLD ? HOLD_OFF : PDEF[k] << 8;
}

void dg_par_set(uint32_t t, uint32_t k, uint32_t raw)
{
    volatile uint8_t *p = store();
    uint32_t i, h;
    if (!p || t >= 16 || k >= DG_NP)
        return;
    if (st_ver(p) == 1)
        st_convert(p);
    if (st_ver(p) != 2) {                               /* this kit's first DigiGlide setting */
        for (i = 4; i < ST_END; i++)
            p[i] = 0;
        p[0] = 'D'; p[1] = 'G'; p[2] = 'K'; p[3] = '2';
    }
    h = st_get2(p, t, K_HOLD);
    if (h != 2 && h != 3)                               /* the track's first: every parameter's default, OFF */
        for (i = 0; i < DG_NP; i++)
            st_put2(p, t, i, i == K_HOLD ? 2 : PDEF[i]);
    st_put2(p, t, k, raw >> 8);
}

uint8_t dg_knob(int32_t raw, uint32_t k)                /* knob << 8 -> the parameter's index; outside: default */
{
    int32_t v = raw >> 8;
    if (k == K_VCNT)
        return dg_vcnt_on(raw) ? (uint8_t)v : 0;
    if (k == K_HOLD)
        return raw == HOLD_ON;
    if (raw < 0 || (raw & 0xFF) || v > PMAX[k])
        return PDEF[k];
    return (uint8_t)v;
}

/* ---------------------------------------------------------------- p-locks made on the pages (build 17)
 * Six parameters can be locked per step: POS, TYPE, EXT, VOIC, GLID, MOVE. The sequencer keeps one lane (129 words,
 * -1 = no lock) per (track, sound slot), from a pool of 80 a pattern. Sound slots 0 and 100 have no parameter on
 * any machine and a lock there changes no word of the frame the DSP is sent (experiments/b17_lanes_frame.py), so
 * DigiGlide packs its six into those two lanes: each field is 0 = not locked, else value + 1.
 *   slot 0:   POS + 129 * (TYPE + 5 * EXT)        (at most 5,804)
 *   slot 100: VOIC + 129 * (GLID + 14 * MOVE)     (at most 19,865)
 * Stock does not lock a row whose record is in the FX group (experiments/b17_lockable_row.py), so the lock is
 * written here, through the stock setter, when a knob of a page turns while a step is held. */
#define APP_ROOT (*(volatile uint32_t *)OSA_446478D0)
#define ACTIVE_CTX ((uint32_t (*)(uint32_t))OSA_4003EFDE)            /* (app) -> the active track's sequencer context */
#define LOCK_SET ((uint32_t (*)(uint32_t, uint32_t, uint32_t, uint32_t))OSA_4004F8FE)  /* ctx, step, slot, value */
#define HELD_OBJ (*(volatile uint8_t *volatile *)OSA_446478C8)      /* +600: 128 bits, the steps held in GRID REC */
#define MARK_EDITED ((void (*)(volatile uint8_t *, uint32_t))OSA_40055BC4)   /* as stock's lock path does */
/* build 23: three lanes. TYPE has 5 values now (5TH), so lane 0 has a second code above 8192 with TYPE's field 6 wide;
 * words up to 5,804 keep the old code (TYPE 5 wide) and are read as they are, and a lock edited on such a step is
 * written back in the new code. Lane 65 (sound slot 65: no machine has a record for it, and a lock there lands in a
 * voice record word the DSP does not read, experiments/b23_slot65.py) holds BPAT and BLOOM.
 *   slot 0:   8192 + POS + 129 * (TYPE + 6 * EXT)   (old: POS + 129 * (TYPE + 5 * EXT), at most 5,804)
 *   slot 100: VOIC + 129 * (GLID + 14 * MOVE)
 *   slot 65:  BPAT + 9 * BLOOM */
#define NLANE 3
static const struct { uint8_t slot, n; uint16_t base; uint8_t k[4], mod[4]; } LANE[NLANE] = {
    {0, 3, 8192, {K_POS, K_TYPE, K_EXT}, {129, 6, 9}},
    {100, 3, 0, {K_VOIC, K_GLID, K_MOVE}, {129, 14, 11}},
    {65, 4, 0, {K_BPAT, K_BLOOM, K_TUNE, K_FAN}, {9, 129, 3, 9}},   /* build 29: + 1161 * (TUNE + 3 * FAN) */
};
/* build 29: lane 65 has 31,347 codes of the 32,767 a lock word holds, so a FAN lock is one of 8 levels (0, 18, 36,
 * 54, 73, 91, 109, 127); a word images <= 28 wrote (under 1,161) reads as it was, TUNE and FAN not locked */
#define FAN_LEVELS 8
static uint32_t fan_level(uint32_t v) { return (v * (FAN_LEVELS - 1) + 63) / 127; }
static uint32_t fan_value(uint32_t l) { return (l * 127 + 3) / (FAN_LEVELS - 1); }
static const uint8_t LK_LANE[DG_NP] = {[K_POS] = 1, [K_TYPE] = 1, [K_EXT] = 1, [K_VOIC] = 2, [K_GLID] = 2,
                                       [K_MOVE] = 2, [K_BPAT] = 3, [K_BLOOM] = 3, [K_TUNE] = 3,
                                       [K_FAN] = 3};   /* lane + 1, 0 = not lockable */
static const uint8_t LK_FIELD[DG_NP] = {[K_POS] = 0, [K_TYPE] = 1, [K_EXT] = 2, [K_VOIC] = 0, [K_GLID] = 1,
                                        [K_MOVE] = 2, [K_BPAT] = 0, [K_BLOOM] = 1, [K_TUNE] = 2,
                                        [K_FAN] = 3};

static int32_t lane_raw(uint32_t t, uint32_t step, uint32_t slot)   /* the lane's word, or -1 */
{
    volatile uint8_t *pat = PLAYING, *lt;
    int8_t idx;
    if (!pat || t >= 16 || step >= 128)
        return -1;
    lt = pat + 97872;
    idx = (int8_t)lt[20640 + 101 * t + slot];
    if (idx < 0)
        return -1;
    return *(volatile int16_t *)(lt + 2 + 2 * (step + 129 * (uint32_t)idx));
}

/* a lane's word -> its fields (0 = not locked, else value + 1); 0 if the word is no DigiGlide lock */
static int lane_fields(uint32_t l, int32_t v, uint32_t *f)
{
    static const uint8_t OLD0[3] = {129, 5, 9};
    const uint8_t *mod = LANE[l].mod;
    uint32_t i, top = 1;
    if (v < 0)
        return 0;
    if (l == 0 && v <= 5804)
        mod = OLD0;
    else
        v -= LANE[l].base;
    for (i = 0; i < LANE[l].n; i++)
        top *= mod[i];
    if (v < 0 || (uint32_t)v >= top)
        return 0;
    for (i = 0; i < LANE[l].n; i++) {
        f[i] = (uint32_t)v % mod[i];
        v /= mod[i];
    }
    return 1;
}

int32_t dg_lock_get(uint32_t t, uint32_t step, uint32_t k)   /* the locked index of parameter k, or -1 */
{
    uint32_t f[4], l;
    if (k >= DG_NP || !LK_LANE[k])
        return -1;
    l = LK_LANE[k] - 1u;
    if (!lane_fields(l, lane_raw(t, step, LANE[l].slot), f))
        return -1;
    if (k == K_FAN && f[LK_FIELD[k]])
        return (int32_t)fan_value(f[LK_FIELD[k]] - 1);
    return (int32_t)f[LK_FIELD[k]] - 1;
}

int dg_lock_any(uint32_t t, uint32_t step)              /* the step holds a DigiGlide lock */
{
    uint32_t l, i, f[4];
    for (l = 0; l < NLANE; l++)
        if (lane_fields(l, lane_raw(t, step, LANE[l].slot), f))
            for (i = 0; i < LANE[l].n; i++)
                if (f[i])
                    return 1;
    return 0;
}

/* lock parameter k of the ACTIVE track on a step to index val, or unlock it (val < 0). -> 0 if stock refused (the
 * pattern's 80 lanes are all in use) */
int dg_lock_put(uint32_t t, uint32_t step, uint32_t k, int32_t val)
{
    uint32_t app = APP_ROOT, f[4], l, i, any = 0;
    int32_t v = 0, m = 1;
    f[0] = f[1] = 0;                                    /* (not an initialiser: four words become a memset call) */
    f[2] = f[3] = 0;
    if (!app || k >= DG_NP || !LK_LANE[k] || step >= 128)
        return 0;
    l = LK_LANE[k] - 1u;
    if (!lane_fields(l, lane_raw(t, step, LANE[l].slot), f) && val < 0)
        return 1;
    f[LK_FIELD[k]] = val < 0 ? 0 : (k == K_FAN ? fan_level((uint32_t)val) : (uint32_t)val) + 1;
    for (i = 0; i < LANE[l].n; i++) {
        v += (int32_t)f[i] * m;
        m *= LANE[l].mod[i];
        any |= f[i];
    }
    return LOCK_SET(ACTIVE_CTX(app), step, LANE[l].slot, any ? (uint32_t)(v + LANE[l].base) : 0xFFFFu) & 0xFF;
}

/* The stock lock path, hooked (ui/hooks_ui.S). With a step held in GRID RECORDING, a knob of a lockable row makes
 * stock call the track context's "get lock" (0x4004eaa4: ctx, step, slot), "set lock" (0x4004f8fe: ctx, step, slot,
 * value) and, for a knob push on a locked step, "remove lock" (0x4004f944: ctx, step, slot), with the record's k as
 * the slot: for DigiGlide's records that is 70..87, the sound's filter envelope. All three are taken here when the
 * slot is one of the six rows', a DigiGlide page is on screen and the context is the active track's: the lock goes
 * to the packed lanes and nothing is filed under 70..87. Everything else is stock's (notes/build_log.md, Build 17). */
int dg_ui_on_page(void);
#define NOT_OURS 0x7FFFFFFF
static int lock_ours(uint32_t ctx, uint32_t slot, uint32_t *t)
{
    uint32_t app = APP_ROOT, k = slot - BUF_K0;
    if (!app || slot < BUF_K0 || k >= DG_NP || !LK_LANE[k] || !dg_ui_on_page() || ctx != ACTIVE_CTX(app))
        return 0;
    *t = *(volatile uint32_t *)(ctx + 60);
    return *t < 16 && dg_synth(*t);
}

/* Stock's knob path with a step held (0x40067856 -> 0x40064d08): no lock yet = "set lock" at the row's value, else
 * "get lock", add the knob's delta in 1/256 steps, "set lock". A lock holds whole steps, so the part of a step the
 * knob has moved is kept here for the lock last written, and given back by the next "get". */
static struct { uint32_t key; uint8_t frac, full; } lk_part;   /* full: FAN's own value (its lock has 8 levels) */

int32_t dg_lock_set_hook(uint32_t ctx, uint32_t step, uint32_t slot, uint32_t value)
{
    uint32_t t, k = slot - BUF_K0;
    int32_t v = (int32_t)(value & 0xFFFF) >> 8;
    if (!lock_ours(ctx, slot, &t))
        return NOT_OURS;
    if ((value & 0xFFFF) == 0xFFFF) {
        lk_part.key = 0;
        return dg_lock_put(t, step, k, -1);
    }
    lk_part.key = 1u << 31 | t << 16 | step << 8 | k;
    lk_part.frac = (uint8_t)value;
    if (v > PMAX[k]) {
        v = PMAX[k];
        lk_part.frac = 0;
    }
    lk_part.full = (uint8_t)v;
    return dg_lock_put(t, step, k, v);
}

int32_t dg_lock_clr_hook(uint32_t ctx, uint32_t step, uint32_t slot)
{
    uint32_t t;
    if (!lock_ours(ctx, slot, &t))
        return NOT_OURS;
    lk_part.key = 0;
    return dg_lock_put(t, step, slot - BUF_K0, -1);
}

int32_t dg_lock_get_hook(uint32_t ctx, uint32_t step, uint32_t slot)
{
    uint32_t t;
    int32_t lk;
    if (!lock_ours(ctx, slot, &t))
        return NOT_OURS;
    lk = dg_lock_get(t, step, slot - BUF_K0);
    if (lk < 0)
        return -1;
    if (lk_part.key != (1u << 31 | t << 16 | step << 8 | (slot - BUF_K0)))
        return lk << 8;
    if (slot - BUF_K0 == K_FAN)                         /* the knob goes on from where it is, not from the level */
        lk = lk_part.full;
    return lk << 8 | lk_part.frac;
}

/* Parameter k for a trig on (track, step): a p-lock, else the track's value.
 * P-locks are the sequencer's: it keeps one lane per (track, sound slot). Up to image 14 the parameters were sound
 * slots of a WAVETONE sound, so the locks made then sit in the lanes of slots 50..64, 93, 94, and WAVETONE's DSP
 * ignores those slots. They are still honoured, on a WAVETONE track that has DigiGlide settings: patterns made with
 * images <= 14 play their locked chord changes as before. A lock value that is not a value of the parameter is not a
 * DigiGlide lock (FM TONE's own locks stay in those lanes when a track's machine is changed) and is skipped.
 * Since image 17 six parameters are locked in the packed lanes of slots 0 and 100 (dg_lock_get); those come first. */
static int32_t par_at(uint32_t t, uint32_t step, uint32_t k, int *locked)
{
    volatile uint8_t *pat = PLAYING;
    *locked = 0;
    {
        int32_t lk = dg_lock_get(t, step, k);          /* build 17: a lock made on the pages */
        if (lk >= 0 && lk <= PMAX[k]) {
            *locked = 1;
            return lk << 8;
        }
    }
    if (pat && step < 128 && k != K_PLAY && k < ST_NP && dg_mach(t) == 1 && dg_marked(t)) {
        volatile uint8_t *lt = pat + 97872;
        int8_t idx = (int8_t)lt[20640 + 101 * t + UISLOT[k]];
        if (idx >= 0) {
            int32_t v = *(volatile int16_t *)(lt + 2 + 2 * (step + 129 * (uint32_t)idx));
            int ok = k == K_VCNT ? v == 0 || dg_vcnt_on(v) : k == K_HOLD ? v == HOLD_OFF || v == HOLD_ON
                     : v >= 0 && !(v & 0xFF) && (v >> 8) <= PMAX[k];
            if (ok) {
                *locked = 1;
                return v;
            }
        }
    }
    return dg_par(t, k);
}

/* the 18 parameters for an event on (track, step) into dg_ui, lock bits into DG.locks; -> 1 if VCNT is on */
static int read_ui(uint32_t t, uint32_t step)
{
    uint32_t k;
    int locked;
    DG.locks = 0;
    for (k = 0; k < DG_NP; k++) {
        dg_ui[k] = dg_knob(par_at(t, step, k, &locked), k);
        DG.locks |= (uint32_t)locked << k;
    }
    return dg_ui[K_VCNT] != 0;
}

/* dg_ui -> the engine's parameters (the scale comes with the chord: fire_event) */
static void engine_params(dg_params *p)
{
    p->key = 0; p->scl = 0;
    p->voic = dg_ui[K_VOIC]; p->pos = dg_ui[K_POS];
    p->vcnt = (uint8_t)(dg_ui[K_VCNT] + 2); p->bass = dg_ui[K_BASS]; p->sprd = 77; p->move = dg_ui[K_MOVE];
    p->glid = dg_ui[K_GLID]; p->path = dg_ui[K_PATH]; p->time = dg_ui[K_TIME]; p->ordr = dg_ui[K_ORDR];
    p->stag = dg_ui[K_STAG]; p->drft = dg_ui[K_DRFT]; p->vib = dg_ui[K_VIB]; p->scrb = dg_ui[K_SCRB];
    p->tune = dg_ui[K_TUNE]; p->fan = dg_ui[K_FAN];
}

/* tests: what an event on (track, step) would read, into dg_ui; -> the lock mask | 0x80000000 if VCNT is on */
uint32_t dg_test_read(uint32_t t, uint32_t step)
{
    int on = read_ui(t, step);
    return DG.locks | (on ? 0x80000000u : 0);
}

static void pm_clear(void);
static void bp_trig(void);

void dg_mod_init(void)
{
    uint32_t e, k;
    GL.blocks = GL.stock_trigs = GL.combo_was = GL.combo_req = GL.msg_until = 0;
    GL.screen = 0;
    GL.vdata = 0;
    GL.swallowed = GL.latch_was = GL.latch_req = 0;
    GL.dbg = GL.dbg_was = GL.dbg_req = GL.seen_on = GL.seen_other = GL.def_was = GL.def_req = 0;
    for (e = NE; e-- > 0; ) {                           /* (slot 0 last: it stays the slot in work) */
        sel(e);
        DG.trigs = DG.active = DG.was_on = DG.locks = DG.ctl = 0;
        DG.src = DG.track = -1;
        DG.pend_on = DG.pend_off = 0;
        DG.base = DG.nres = DG.held = DG.ev_open = DG.ev_n = DG.gate_open = DG.latched = 0;
        DG.play_was = DG.stop_was = DG.events = DG.releases = 0;
        DG.off_block = DG.tail = DG.sig = DG.ev_legato = DG.snd_sig = DG.ev_seq = 0;
        dg_tail_log = 0;
        dg_init(&T, 120u * 120u, 0);
        for (k = 0; k < DG_NP; k++)
            dg_ui[k] = PDEF[k];
        dg_ui[K_VCNT] = 3;
        engine_params(&dg_cur);
        dg_name[0] = 0;
        DG.last_cw = DG.rev_block = DG.reattack = DG.owed = DG.lmask = DG.hurry = 0;
        pm_clear();
    }
}

/* the per-voice words and sound record of voice s copied to voice d */
NI static void clone_voice(volatile uint8_t *f, uint32_t s, uint32_t d)
{
    volatile uint16_t *a = (volatile uint16_t *)(f + 0xda + 146 * s);
    volatile uint16_t *b = (volatile uint16_t *)(f + 0xda + 146 * d);
    uint32_t i;
    if (s == d)
        return;
    {   /* 146 B = 36 longs + a halfword. Records are only halfword aligned: the ColdFire reads and writes a
         * misaligned long (build 28; the frame is on-chip SRAM). Build 33: plain pointers and four longs a turn. The
         * volatile loop was 24 bytes of code a long, 870 a voice: 37 % of the hook's work with six voices sounding
         * (the owner's unit: 332 microseconds on a note frame, where about 240 is free). */
        typedef uint32_t __attribute__((may_alias)) u32a;
        const u32a *al = (const u32a *)(const void *)a;
        u32a *bl = (u32a *)(void *)b;
        for (i = 0; i < 9; i++) {
            uint32_t w0 = al[0], w1 = al[1], w2 = al[2], w3 = al[3];
            bl[0] = w0; bl[1] = w1; bl[2] = w2; bl[3] = w3;
            al += 4; bl += 4;
        }
        b[72] = a[72];
    }
    wr16(f, 0x34 + 2 * d, rd16(f, 0x34 + 2 * s));
    wr16(f, 0x54 + 2 * d, rd16(f, 0x54 + 2 * s));
    wr16(f, 0x74 + 2 * d, rd16(f, 0x74 + 2 * s));
    wr16(f, 0x94 + 2 * d, rd16(f, 0x94 + 2 * s));
    wr16(f, 0xa5a + 2 * d, rd16(f, 0xa5a + 2 * s));
}

NI static uint16_t note_word(int32_t c16)                  /* Q16 cents -> note << 8 (1/256 semitone), rounded */
{
    int32_t w = (c16 + 12800) / 25600;
    if (w < 0)
        w = 0;
    if (w > (127 << 8))
        w = 127 << 8;
    return (uint16_t)w;
}

static int key_held(uint32_t code)
{
    return (KEYS_HELD[(code - 1) >> 3] >> ((code - 1) & 7)) & 1;
}

static void redraw(void)
{
    if (GL.screen)
        GL.screen[32] = 1;                              /* the UI loop's "redraw due" (0x4011d2f4) */
}

#define CODE_ENC_A 41
#define CODE_ENC_B 42
volatile uint8_t dg_drone_req;                          /* bit 0: pick the next, bit 1: load (set in the ISR) */
int32_t dg_drone_sel = -1;                              /* the drone picked, 0..9 (tests) */
uint32_t dg_drone_loads;                                /* sounds loaded so far (tests) */

NI static void shortcut_tick(void)
{
    uint32_t combo = key_held(CODE_FUNC) && key_held(CODE_ENC_E);
    if (combo && !GL.combo_was) {
        GL.combo_req = 1;                               /* handled by dg_overlay in the UI task */
        redraw();
    }
    GL.combo_was = combo;
    combo = key_held(CODE_FUNC) && key_held(CODE_ENC_H);
    if (combo && !GL.latch_was) {
        GL.latch_req = 1;
        redraw();
    }
    GL.latch_was = combo;
    combo = key_held(CODE_FUNC) && key_held(CODE_ENC_F);
    if (combo && !GL.def_was) {
        GL.def_req = 1;
        redraw();
    }
    GL.def_was = combo;
    combo = key_held(CODE_FUNC) && key_held(CODE_ENC_G);
    if (combo && !GL.dbg_was) {
        GL.dbg ^= 1;
        if (GL.dbg) {                                   /* which build is on the unit (the OS screen says 1.12) */
            dg_put(dg_msg, "DIGIGLIDE BUILD " DG_XSTR(DG_BUILD));
            GL.msg_until = GL.blocks + MSG_BLOCKS;
        }
        redraw();
    }
    GL.dbg_was = combo;
    {   /* build 31, DigiDrone: [FUNC] + push encoder A picks a drone sound, + push encoder B loads it */
        static uint8_t pick_was, load_was;
        combo = key_held(CODE_FUNC) && key_held(CODE_ENC_A);
        if (combo && !pick_was) {
            dg_drone_req |= 1;
            redraw();
        }
        pick_was = (uint8_t)combo;
        combo = key_held(CODE_FUNC) && key_held(CODE_ENC_B);
        if (combo && !load_was) {
            dg_drone_req |= 2;
            redraw();
        }
        load_was = (uint8_t)combo;
    }
    if (GL.dbg && !(GL.blocks & 127))
        redraw();
    if (GL.msg_until) {                                 /* keep the message drawn, then erase it once */
        if (GL.blocks >= GL.msg_until) {
            GL.msg_until = 0;
            redraw();
        } else if (!(GL.blocks & 63)) {
            redraw();
        }
    }
}

/* ---------------------------------------------------------------- the shortcut, from the UI task (dg_overlay) */
static uint8_t last_code[16];                           /* the voice count each track had when switched OFF */
char dg_msg[28];
#define msg dg_msg

static char *put(char *d, const char *s)
{
    while ((*d = *s++))
        d++;
    return d;
}

static void toggle(uint32_t t)
{
    if (!dg_synth(t)) {
        put(msg, "DIGIGLIDE: NOT ON MIDI");
        return;
    }
    if (dg_vcnt_on(dg_par(t, K_VCNT))) {
        last_code[t] = (uint8_t)(dg_par(t, K_VCNT) >> 8);
        dg_par_set(t, K_VCNT, 0);
        put(msg, "DIGIGLIDE OFF");
    } else {
        uint32_t c = last_code[t] >= 1 && last_code[t] <= 4 ? last_code[t] : 3;   /* 3 = 5 voices */
        char *e;
        dg_par_set(t, K_VCNT, c << 8);
        if (!dg_vcnt_on(dg_par(t, K_VCNT))) {           /* no kit record to keep it in */
            put(msg, "DIGIGLIDE: NO KIT");
            return;
        }
        e = put(msg, "DIGIGLIDE ON (");
        *e++ = (char)('0' + c + 2);
        put(e, " VOICES)");
    }
}

/* every DigiGlide parameter of track t to its default (VCNT is left as it is) */
static void set_defaults(uint32_t t)
{
    uint32_t k;
    for (k = 0; k < DG_NP; k++)
        if (k != K_VCNT)
            dg_par_set(t, k, k == K_HOLD ? HOLD_OFF : (uint32_t)PDEF[k] << 8);
}

static void toggle_latch(uint32_t t)
{
    if (!dg_synth(t)) {
        put(msg, "DIGIGLIDE: NOT ON MIDI");
        return;
    }
    if (dg_par(t, K_HOLD) == HOLD_ON) {
        dg_par_set(t, K_HOLD, HOLD_OFF);
        put(msg, "HOLD OFF");
    } else {
        dg_par_set(t, K_HOLD, HOLD_ON);
        put(msg, "HOLD ON");
    }
}

/* ---------------------------------------------------------------- build 31: DigiDrone
 * Ten FM TONE drone sounds are in the image as stock stored sounds (dg_drones.h, written by the OS's own converter in
 * the emulator: tests/make_drones.py). [FUNC] + push encoder A steps through their names; [FUNC] + push encoder B
 * loads the one shown into the active track's sound with stock's loader (as a sound loaded from the +Drive: the
 * machine, the name and every parameter), and sets the DigiGlide settings that go with it. Runs in the UI task. */
#include "dg_drones.h"
#define SOUND_LOAD ((uint32_t (*)(volatile uint8_t *, uint8_t *))OSA_400DD1EA)
static void drone_pick(void)
{
    char *e;
    /* Two no-ops, kept on purpose: without these 4 bytes the code after here sits where the emulated panel drops
     * [RECORD] and a trig key's release in test_b17_locks (the same code 4 bytes on passes: build log, image 31). */
    __asm__ volatile("nop\nnop");
    dg_drone_sel = dg_drone_sel + 1 >= DRONE_N ? 0 : dg_drone_sel + 1;
    e = put(msg, "DRONE ");
    if (dg_drone_sel >= 9)
        *e++ = '1';
    *e++ = (char)('0' + (dg_drone_sel + 1) % 10);
    *e++ = ' ';
    put(e, DRONE_NAME[dg_drone_sel]);
}

static void drone_load(uint32_t t)
{
    static uint8_t buf[DRONE_LEN];
    volatile uint8_t *d = buf;
    const uint8_t *s, *g;
    uint32_t i;
    if (!dg_synth(t)) {
        put(msg, "DIGIGLIDE: NOT ON MIDI");
        return;
    }
    if (dg_drone_sel < 0) {
        put(msg, "FUNC+A PICKS A DRONE");
        return;
    }
    s = DRONE_SND[dg_drone_sel];
    for (i = 0; i < DRONE_LEN; i++)
        d[i] = s[i];
    if (!(SOUND_LOAD(sound_of(t), buf) & 0xFF)) {
        put(msg, "DRONE: LOAD FAILED");
        return;
    }
    {   /* Stock keeps, per DSP voice, the sound its parameter mirror was filled from (0x800052a8 + 4 v; the voice's
         * track at +96) and fills the mirror again at a note-on only when that is not the track's sound. The loader
         * wrote new values into the same sound, so the mirror would stay the old sound's (machine included): forget
         * it for the track's voices, as stock's own setter does (0x400258be), and the next note-on fills it. */
        volatile uint32_t *vp = (volatile uint32_t *)(OSA_800052A0 + 8);
        for (i = 0; i < 16; i++)
            if (vp[i] == (uint32_t)sound_of(t) || vp[24 + i] == t)
                vp[i] = 0;
    }
    for (g = DRONE_DG[dg_drone_sel]; g[0] != 255; g += 2)
        dg_par_set(t, g[0], (uint32_t)g[1] << 8);
    if (!dg_vcnt_on(dg_par(t, K_VCNT))) {
        put(msg, "DRONE: NO KIT");
        return;
    }
    dg_drone_loads++;
    put(put(msg, "LOADED "), DRONE_NAME[dg_drone_sel]);
}

/* VOICES: a track whose VCNT is on needs that many reserved DSP voices (the VOICE menu's VOICES), or stock
 * plays its notes anywhere in the 16-voice pool. Called from the UI task: raise it through stock's own setter (which
 * limits it to the voices still free) and say so; when VCNT goes OFF, put back what was there if nobody changed it. */
typedef uint32_t (*vget_fn)(void *);              /* (a pointer, but the firmware returns it in d0) */
typedef void (*vset_fn)(void *, uint32_t, int32_t);
static uint8_t v_prev[16], v_set[16], v_tried[16], v_was_on[16];
uint8_t dg_vchk[16];                                    /* the track's voices were looked at once (tests clear it) */
uint16_t dg_cmwarn;                                     /* build 26: "CHORD MODE ON?" was shown on the track (bit t) */

/* Sounds made with images <= 14 carry DigiGlide in their own slots (WAVETONE, VCNT's on-code in slot 54, HOLD's mark in
 * slot 94). On a track that has no settings of its own yet, such a sound's values are taken over once, so the owner's
 * patterns and saved sounds keep playing chords. The sound itself is left as it is. */
uint32_t dg_imported;                                   /* tracks taken over so far (tests) */

/* build 34: a pattern change keeps a track's DigiGlide. The settings live in the pattern's kit, so a pattern whose
 * kit never had them (a new one, or a copy: stock's kit copy does not carry the bytes) played single notes on the
 * track that played chords a moment ago (owner, image 33, playing by hand: "switching between patterns ... single
 * notes after"). When the kit changes, a synth track that was on in the kit before, has no settings of its own in
 * the new kit and holds the same sound (machine and name) takes the old kit's settings over, once: after that they
 * are the new kit's own. A track that was set up there (VCNT OFF too) or holds another sound is left alone. */
uint32_t dg_inherited;                                  /* tracks carried over so far (tests) */
static uint32_t inh_sig_of(uint32_t t)
{
    volatile uint8_t *snd = sound_of(t);
    uint32_t h = snd[0xDE] + 1u, i;
    for (i = 4; i < 20; i++)
        h = h * 31 + snd[i];
    return h;
}

static void inherit_tick(void)
{
    static uint8_t *kit_was;
    static uint8_t on[16], rr;
    static uint16_t val[16][DG_NP];
    static uint32_t sig[16];
    uint8_t *kit = SOUNDS;
    uint32_t t, k;
    if (!kit || GL.blocks <= 3000 || !store())
        return;
    if (kit != kit_was) {
        if (kit_was)
            for (t = 0; t < 16; t++) {
                if (!on[t] || !dg_synth(t) || dg_marked(t) || inh_sig_of(t) != sig[t])
                    continue;
                for (k = 0; k < DG_NP; k++)
                    if (k != K_VCNT)
                        dg_par_set(t, k, val[t][k]);
                dg_par_set(t, K_VCNT, val[t][K_VCNT]);  /* (the switch last: every value is there when it goes on) */
                dg_inherited++;
                {
                    char *e = put(msg, "DIGIGLIDE KEPT: TRACK ");
                    if (t >= 9)
                        *e++ = '1';
                    *e++ = (char)('0' + (t + 1) % 10);
                    *e = 0;
                    GL.msg_until = GL.blocks + MSG_BLOCKS;
                }
            }
        kit_was = kit;
        for (t = 0; t < 16; t++)
            on[t] = 0;
        rr = 0;
    }
    t = rr++ & 15;                                      /* one track a pass: what the kit holds now */
    on[t] = dg_synth(t) && dg_marked(t) && dg_vcnt_on(dg_par(t, K_VCNT));
    if (on[t]) {
        for (k = 0; k < DG_NP; k++)
            val[t][k] = (uint16_t)dg_par(t, k);
        sig[t] = inh_sig_of(t);
    }
}

static void import_tick(void)
{
    uint32_t t, k;
    if (!SOUNDS || GL.blocks <= 3000 || !store())
        return;
    for (t = 0; t < 16; t++) {
        int32_t h;
        if (dg_mach(t) != 1 || !dg_vcnt_on(sound_slot(t, 54)) || dg_marked(t))
            continue;
        h = sound_slot(t, 94);
        if (h != HOLD_OFF && h != HOLD_ON)
            continue;
        for (k = 0; k < ST_NP; k++) {                   /* (SPD: its default) */
            int32_t raw = sound_slot(t, UISLOT[k]);
            dg_par_set(t, k, k == K_VCNT || k == K_HOLD ? (uint32_t)raw : (uint32_t)dg_knob(raw, k) << 8);
        }
        dg_imported++;
    }
}

/* The pages' knobs. A stock knob writes its record's value into a parameter set; DigiGlide's 18 records name the
 * kit's FX set, words k 70..87, which stock has no parameter for and sends nowhere (a knob turned in the emulator
 * changed that word and nothing else in the kit). That is one buffer for the kit, so it follows the selected track:
 * when the track or the kit changes, or the store was changed from elsewhere (a shortcut, the defaults), the store is
 * copied into the buffer; when a knob changed the buffer, the value goes to the store. A buffer value that is not a
 * value of the parameter is put back. Called from the UI task before a DigiGlide page is drawn and after every pass. */
static uint8_t *b_kit;
static uint32_t b_trk = 0xFF;
static uint16_t b_shadow[DG_NP];
static const uint8_t PMIN[DG_NP] = {0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
static const uint8_t PTOP[DG_NP] = {4, 7, 24, 127, 127, 12, 3, 3, 9, 5, 4, 6, 9, 50, 50, 127, 4, 6, 127, 7, 2, 127, 3, 127, 1, 127};

/* the step the pages show and edit: the first step held in GRID RECORDING, or -1 (the track's own values) */
int32_t dg_view_step = -1;
uint32_t dg_view_locks;                                 /* bit k: parameter k is locked on that step (drawn inverted) */
int dg_ui_shown_page(void);

static int32_t held_step(volatile uint32_t **bits)
{
    volatile uint8_t *o = HELD_OBJ;
    uint32_t i;
    *bits = 0;
    if (!o)
        return -1;
    *bits = (volatile uint32_t *)(o + 600);
    for (i = 0; i < 128; i++)
        if (((*bits)[i >> 5] >> (i & 31)) & 1)
            return (int32_t)i;
    return -1;
}

int32_t dg_view(uint32_t t, uint32_t k)                 /* what the page shows for parameter k: the held step's lock, */
{                                                       /* else the track's value */
    int32_t lk = dg_view_step >= 0 ? dg_lock_get(t, (uint32_t)dg_view_step, k) : -1;
    return lk >= 0 ? lk << 8 : dg_par(t, k);
}

void dg_ui_sync(uint32_t t)
{
    uint8_t *kit = SOUNDS;
    volatile uint32_t *bits = 0;
    uint32_t k, fresh, locks = 0;
    int32_t hs;
    if (!kit || t >= 16)
        return;
    hs = dg_synth(t) ? held_step(&bits) : -1;
    fresh = kit != b_kit || t != b_trk || hs != dg_view_step;
    b_kit = kit;
    b_trk = t;
    dg_view_step = hs;
    for (k = 0; k < DG_NP; k++) {
        volatile uint8_t *w = kit + FXBUF + 2 * (BUF_K0 + k);
        uint16_t buf = (uint16_t)(w[0] << 8 | w[1]), st;
        if (!fresh && buf != b_shadow[k] && !(buf & 0xFF) && (buf >> 8) >= PMIN[k] && (buf >> 8) <= PTOP[k]
            && dg_synth(t)) {
            if (hs < 0)                                 /* (with a step held stock sends the knob to its lock */
                dg_par_set(t, k, buf);                  /* path: dg_lock_set_hook) */
        }
        st = (uint16_t)dg_view(t, k);
        if (hs >= 0 && dg_lock_get(t, (uint32_t)hs, k) >= 0)
            locks |= 1u << k;
        if (buf != st) {
            w[0] = (uint8_t)(st >> 8);
            w[1] = (uint8_t)st;
        }
        b_shadow[k] = st;
    }
    dg_view_locks = locks;
}

static void voices_tick(void)
{
    uint8_t *app = (uint8_t *)(*(volatile uint32_t *)OSA_446478D0);
    void *cfg;
    uint8_t *d;
    uint32_t t, settled;
    if (!app || !SOUNDS)
        return;
    cfg = app + 244 + 17092;                            /* 0x4003e41a, 0x40030af8 */
    d = (uint8_t *)((vget_fn)(*(uint32_t **)cfg)[10])(cfg);
    GL.vdata = d;
    if (!d)
        return;
    /* the first look waits until audio has run for 2 s: during start-up, before the kit is loaded, this data is
     * not the kit's yet (build 8's first try changed the start-up state: test_m55_regression) */
    settled = GL.blocks > 3000;
    for (t = 0; t < 16; t++) {
        int32_t raw = dg_par(t, K_VCNT);
        uint32_t have = d[5 * t + 1];
        if (dg_synth(t) && dg_vcnt_on(raw)) {
            uint32_t want = (uint32_t)(raw >> 8) + 2, k;
            if (have < want && v_tried[t] != (uint8_t)(want << 4 | have)) {
                if (!v_set[t])
                    v_prev[t] = (uint8_t)have;
                ((vset_fn)OSA_40029094)(cfg, t, (int32_t)want);
                v_tried[t] = (uint8_t)(want << 4 | d[5 * t + 1]);     /* not again until something changes */
                v_set[t] = d[5 * t + 1];
                if (d[5 * t + 1] >= want) {
                    char *e = put(msg, "VOICES SET TO ");
                    *e++ = (char)('0' + d[5 * t + 1]);
                    *e = 0;
                } else {                                /* other tracks hold the rest (the VOICE menu) */
                    char *e = put(msg, "VOICES ");
                    *e++ = (char)('0' + d[5 * t + 1]);
                    e = put(e, " OF ");
                    *e++ = (char)('0' + want);
                    *e = 0;
                }
                for (k = 0, have = 0; k < 16; k++)
                    have += d[5 * k + 1];
                if (have >= 16)                         /* every voice is reserved: tracks with none are silent */
                    put(msg, "OTHER TRACKS: NO VOICES");
                GL.msg_until = GL.blocks + MSG_BLOCKS;
            }
            v_was_on[t] = 1;
            if (settled)
                dg_vchk[t] = 1;
        } else {
            /* VCNT is off. Hand back the voices DigiGlide reserved: what was there before when this session set
             * them; otherwise (set in an earlier session and saved with the kit: the first look at the track, or
             * VCNT just went off) a WAVETONE sound that was a DigiGlide sound and holds 3..6 goes back to the
             * default, or the reservations pile up until the other tracks have no voices (the unit, build 7). */
            if (v_set[t]) {
                if (have == v_set[t])
                    ((vset_fn)OSA_40029094)(cfg, t, v_prev[t]);
            } else if ((v_was_on[t] || (settled && !dg_vchk[t])) && have >= 3 && have <= 6) {
                if (dg_marked(t)) {
                    char *e;
                    ((vset_fn)OSA_40029094)(cfg, t, 0);
                    e = put(msg, "VOICES FREED: TRACK ");
                    if (t >= 9)
                        *e++ = '1';
                    *e++ = (char)('0' + (t + 1) % 10);
                    *e = 0;
                    GL.msg_until = GL.blocks + MSG_BLOCKS;
                }
            }
            v_set[t] = v_tried[t] = v_was_on[t] = 0;
            if (settled)
                dg_vchk[t] = 1;
        }
    }
}

static uint32_t voice_range(uint32_t t, uint32_t *base);

/* the status box: two lines of counters (decimal, 3 digits, wrapping) read over USB with the Screenshot RPC */
static char dbg1[30], dbg2[30];
uint32_t dg_forced, dg_defer_max;                       /* build 28 (dg_tx) */
static uint32_t hk_show, hk_show_note, hk_show_min;
#define DTRR3 (*(volatile uint32_t *)0xFC07C004)
#define DTCN3 (*(volatile uint32_t *)0xFC07C00C)
/* build 33: is the mod's own code slow on the unit, or the frame's memory? A loop of known length (200 turns, about
 * 1,400 instructions) and 256 reads of the frame, timed with DTIM3 while the status box is on. */
static uint32_t cal_i = 0xFFFFFFFFu, cal_u = 0xFFFFFFFFu, cal_f = 0xFFFFFFFFu;
static volatile uint32_t cal_sink;
static uint32_t __attribute__((noinline)) cal_loop(uint32_t n)
{
    uint32_t x = 1, i;
    for (i = 0; i < n; i++) {
        x = x * 5 + i;
        x ^= x >> 7;
    }
    return x;
}
static uint32_t __attribute__((noinline)) cal_frame(void)
{
    volatile uint8_t *f = FRAME;
    uint32_t x = 0, i;
    for (i = 0; i < 256; i++)
        x += rd16(f, 0xda + 2 * (i & 63));
    return x;
}
static uint32_t cal2(uint32_t t)
{
    t = t == 0xFFFFFFFFu ? 0 : t * 4 / 33;
    return t > 99 ? 99 : t;
}

static char *num(char *d, const char *label, uint32_t v, int digits)
{
    d = put(d, label);
    if (digits >= 3)
        *d++ = (char)('0' + v / 100 % 10);
    if (digits >= 2)
        *d++ = (char)('0' + v / 10 % 10);
    *d++ = (char)('0' + v % 10);
    *d++ = ' ';
    *d = 0;
    return d;
}

/* line 0: B base voice, N voices held, O note-ons seen with VCNT on, T taken by DigiGlide, S played as stock
 * line 1: K the note stock sent for the last key, R the root DigiGlide played, E chord events, L held-chord |
 *         gate open | HOLD, P the sequencer plays. Counters wrap at 100. At most 21 characters a line. */
const char *dg_dbg_line(uint32_t which, uint32_t track)
{
    char *e;
    if (!GL.dbg)
        return 0;
    if (!which) {
        uint32_t b = 0, n = voice_range(track < 16 ? track : 0, &b);
        e = num(dbg1, "B", b, 2);
        e = num(e, "N", n, 1);
        e = num(e, "O", GL.seen_on, 2);
        e = num(e, "T", GL.swallowed, 2);
        num(e, "S", GL.stock_trigs, 2);
        return dbg1;
    }
    if (which == 2) {                                   /* build 28: H the hook's longest time in the last 1.4 s, N the
                                                         * longest on a frame with notes (microseconds; a block is
                                                         * 667). Build 33: L the shortest with a chord sounding; and,
                                                         * in turn with those every 1.4 s, the same small loop timed
                                                         * in the hook (I) and here in the UI task (U), and 256 reads
                                                         * of the frame (F): microseconds, shortest seen, 99 = more */
        static char dbg3[30];
        uint32_t k, t0, dt;
        for (k = 0; k < 4; k++) {
            t0 = DTCN3;
            cal_sink += cal_loop(200);
            dt = DTCN3;
            dt = dt >= t0 ? dt - t0 : dt + DTRR3 + 1 - t0;
            if (dt < cal_u)
                cal_u = dt;
        }
        if ((GL.blocks >> 11) & 1) {
            e = num(dbg3, "I", cal2(cal_i), 2);
            e = num(e, "U", cal2(cal_u), 2);
            num(e, "F", cal2(cal_f), 2);
        } else {
            e = num(dbg3, "H", hk_show * 4 / 33, 3);
            e = num(e, "N", hk_show_note * 4 / 33, 3);
            num(e, "L", hk_show_min == 0xFFFFFFFFu ? 0 : hk_show_min * 4 / 33, 3);
        }
        return dbg3;
    }
    {   /* (build 32: the slot playing this track, else slot 0) */
        uint32_t q = track < 16 && DGS[1].track == (int32_t)track && DGS[0].track != (int32_t)track;
        e = num(dbg2, "K", DGS[q].last_note, 3);
        e = num(e, "R", (uint32_t)TS[q].aroot, 3);
        e = num(e, "E", DGS[q].events, 2);
        e = num(e, "L", DGS[q].latched * 100 + DGS[q].gate_open * 10 + dg_ui_s[q][K_HOLD], 3);
    }
    num(e, "P", PLAY_FLAG == 1, 1);
    return dbg2;
}

/* the name of the chord sounding on `track` (the pages show it), or 0 */
const char *dg_chord_name(uint32_t track)
{
    uint32_t q;
    for (q = 0; q < NE; q++)
        if (DGS[q].active && (int32_t)track == DGS[q].track && (DGS[q].gate_open || DGS[q].latched) && dg_name_s[q][0])
            return dg_name_s[q];
    return 0;
}

/* the end of each screen pass: remember the screen, act on a shortcut press, -> the message to draw (or 0) */
const char *dg_ui_step(volatile uint8_t *screen, uint32_t track)
{
    GL.screen = screen;
    if (GL.combo_req) {
        GL.combo_req = 0;
        toggle(track);
        GL.msg_until = GL.blocks + MSG_BLOCKS;
    }
    if (GL.latch_req) {
        GL.latch_req = 0;
        toggle_latch(track);
        GL.msg_until = GL.blocks + MSG_BLOCKS;
    }
    if (GL.def_req) {                                   /* [FUNC] + push encoder F: this sound back to the defaults */
        GL.def_req = 0;
        if (dg_synth(track)) {
            set_defaults(track);
            put(msg, "DEFAULTS SET");
        } else {
            put(msg, "DIGIGLIDE: NOT ON MIDI");
        }
        GL.msg_until = GL.blocks + MSG_BLOCKS;
    }
    if (dg_drone_req) {                                 /* build 31 */
        uint32_t r = dg_drone_req;
        dg_drone_req = 0;
        if (r & 1)
            drone_pick();
        else
            drone_load(track);
        GL.msg_until = GL.blocks + MSG_BLOCKS;
    }
    inherit_tick();
    import_tick();
    dg_ui_sync(track);
    voices_tick();
    return GL.msg_until && GL.blocks < GL.msg_until ? msg : 0;
}

/* the track's reserved DSP voices: stock packs the reserved blocks from voice 0 in track order
 * (experiments/m6_reserve_other.py) */
static uint32_t voice_range(uint32_t t, uint32_t *base)
{
    volatile uint8_t *d = GL.vdata;
    uint32_t b = 0, k;
    if (!d)
        return 0;
    for (k = 0; k < t; k++)
        b += d[5 * k + 1];
    *base = b;
    return b + d[5 * t + 1] <= 16 ? d[5 * t + 1] : 0;
}

/* how long a released chord still rings: the sound's amp release (slot 85) as blocks to -40 dB, measured in the
 * SHARC emulator (pack/calibration.json) at knob 0, 16, .. 112, and 60 s at 127 (INF) */
static uint32_t tail_blocks(uint32_t t)
{
    static const uint32_t TB[9] = {75, 195, 1012, 2722, 5505, 9547, 14985, 21922, 90000};
    int32_t raw = sound_slot(t, 85);
    uint32_t k = raw < 0 ? 0 : raw > 0x7F00 ? 0x7F00 : (uint32_t)raw, i = k >> 12, fr = k & 0xFFF;
    if (i >= 8)
        return TB[8];
    return TB[i] + (((TB[i + 1] - TB[i]) >> 4) * fr >> 8);
}

/* ------------------------------------------------------------------ build 19: PLAY modes (owner, 2026-11-14)
 * PLAY on the CHORD page, on DigiGlide's own voices (not the stock arp):
 *   CHRD  the chord's voices start together, as before;
 *   STRM  a struck chord is strummed low to high: its voices start one after the other, STRUM_GAP blocks apart;
 *   STRU  the same, high to low. Only strikes are strummed; a chord that glides to the next is not;
 *   HARP  every new chord, and every change of a sounding one (POS, TYPE, ... turned), runs up through the chord's
 *         notes from its lowest voice for three octaves, HARP_GAP blocks a note, round the chord's voices: the run's
 *         last notes ring. A voice keeps the run's note (with DRFT and VIB) until the next run.
 * The frame hook delays a voice's note-on until its turn; the engine, the glides and the gates are unchanged. */
enum { PM_CHRD, PM_STRM, PM_STRU, PM_HARP };
#define STRUM_GAP 20                                    /* blocks (1.5 kHz): 13 ms a string (Brickchord's strum) */
#define DAMP_BLOCKS 6                                   /* build 27: 4 ms, a strum damps a sounding string */
#define HARP_GAP 51                                     /* 34 ms a note (Brickchord's harp) */
#define HARP_SPAN 36                                    /* semitones above the chord's lowest voice */
#define RUN_MAX 24
static struct {
    uint32_t t0, n, i;                                  /* the schedule: start block, events, next event */
    uint8_t v[RUN_MAX];                                 /* engine voice index */
    int8_t note[RUN_MAX];                               /* HARP: the note; strum: -1 (the engine's pitch) */
    uint16_t at[RUN_MAX];                               /* blocks after t0 */
    int32_t hn[DG_NV];                                  /* HARP: the note a voice plays, Q16 cents (0: the engine's) */
    uint32_t wait;                                      /* engine voices whose start waits for its turn */
    uint32_t want;                                      /* HARP: a new chord or a change, the run is due */
} PMS[NE], *pmp = PMS;
#define PM (*pmp)
uint32_t dg_pm_runs, dg_pm_strums;                      /* runs and strums started (tests) */

/* build 21: SPD scales both gaps, 2^((SPD - 64) / 24): 64 = the gaps above, 0 = x0.16 (strum 2 ms, harp 5 ms a note),
 * 127 = x6.2 (strum 82 ms, harp 210 ms). Every 24 is twice as slow. */
static const uint32_t SPD_TB[24] = {65536, 67456, 69433, 71468, 73562, 75717, 77936, 80220, 82570, 84990, 87480, 90043, 92682, 95398, 98193, 101070, 104032, 107080, 110218, 113448, 116772, 120194, 123715, 127341};
uint32_t dg_pm_gap(uint32_t base, uint32_t spd)
{
    int32_t e = (int32_t)spd - 64, q = e >= 0 ? e / 24 : -((23 - e) / 24);
    uint32_t g = base * SPD_TB[e - 24 * q] >> 16;
    g = q >= 0 ? g << q : g >> -q;
    return g ? g : 1;
}

static void pm_clear(void)
{
    uint32_t i;
    PM.n = PM.i = PM.wait = PM.want = 0;
    for (i = 0; i < DG_NV; i++)
        PM.hn[i] = 0;
}

static uint32_t pm_semi(int32_t c16)                    /* Q16 cents -> the nearest note, 0..127 */
{
    int32_t n = (c16 + 3276800) / 6553600;          /* a semitone is 100 << 16 */
    return (uint32_t)(n < 0 ? 0 : n > 127 ? 127 : n);
}

/* the voices of `set` (engine indices) in order of pitch, up (dir 0) or down (dir 1) */
static uint32_t pm_order(uint32_t set, const int32_t *out, int dir, uint8_t *ord)
{
    uint32_t i, j, n = 0;
    for (i = 0; i < DG_NV; i++) {
        if (!((set >> i) & 1))
            continue;
        for (j = n; j > 0 && (dir ? out[ord[j - 1]] < out[i] : out[ord[j - 1]] > out[i]); j--)
            ord[j] = ord[j - 1];
        ord[j] = (uint8_t)i;
        n++;
    }
    return n;
}

/* one block: start a schedule if one is due, then the voices whose turn it is. att: the voices the engine strikes
 * this block, gat: the voices it gates. Returns the voices to start now. */
NI static uint32_t pm_block(uint32_t mode, uint32_t att, uint32_t gat, const int32_t *out)
{
    uint8_t ord[DG_NV];
    int32_t tg[DG_NV];
    uint32_t n, k, fire = 0;
    (void)out;
    if (mode == PM_CHRD || mode > PM_HARP) {
        if (PM.n || PM.wait || PM.hn[0] | PM.hn[1] | PM.hn[2] | PM.hn[3] | PM.hn[4] | PM.hn[5])
            pm_clear();
        return 0;
    }
    for (k = 0; k < DG_NV; k++)                         /* voices are ordered by where they go, not where they are */
        tg[k] = T.v[k].tgt;
    if (mode == PM_HARP && PM.want && gat) {
        /* BASS on: the lowest voice is the bass. It keeps its note (struck with the chord, not run again on a
         * change) and the run goes round the chord voices from their lowest, so POS moves the run. */
        uint32_t lo, m, j = 0, pcs = DG.last_cw & 0xFFF, bass = 0;
        n = pm_order(gat, tg, 0, ord);
        PM.n = 0;
        if (dg_ui[K_BASS] && n >= 2) {
            bass = 1u << ord[0];
            if (att & bass) {
                PM.v[0] = ord[0];
                PM.note[0] = -1;
                PM.at[0] = 0;
                PM.n = 1;
            }
            PM.hn[ord[0]] = 0;
            j = 1;
        }
        lo = pm_semi(tg[ord[j]]);
        for (m = lo; m <= lo + HARP_SPAN && m <= 127 && PM.n < RUN_MAX; m++)
            if ((pcs >> (m % 12)) & 1) {
                k = PM.n - (bass && (att & bass));     /* the run's own count */
                PM.v[PM.n] = ord[j + k % (n - j)];
                PM.note[PM.n] = (int8_t)m;
                PM.at[PM.n] = (uint16_t)(k * dg_pm_gap(HARP_GAP, dg_ui[K_SPD]));
                PM.n++;
            }
        PM.i = 0;
        PM.t0 = GL.blocks;
        PM.wait = gat & ~bass;
        PM.want = 0;
        dg_pm_runs++;
    } else if ((mode == PM_STRM || mode == PM_STRU) && (att & (att - 1))) {    /* two voices or more struck */
        n = pm_order(att, tg, mode == PM_STRU, ord);
        for (k = 0; k < n; k++) {
            PM.v[k] = ord[k];
            PM.note[k] = -1;
            PM.at[k] = (uint16_t)(k * dg_pm_gap(STRUM_GAP, dg_ui[K_SPD]));
        }
        PM.n = n;
        PM.i = 0;
        PM.t0 = GL.blocks;
        PM.wait = att;
        dg_pm_strums++;
    }
    for (; PM.i < PM.n && GL.blocks - PM.t0 >= PM.at[PM.i]; PM.i++) {
        k = PM.v[PM.i];
        if (PM.note[PM.i] >= 0)
            PM.hn[k] = PM.note[PM.i] * 6553600 + dg_tune_off(&T, (int)k, PM.note[PM.i]);
        fire |= 1u << k;
    }
    PM.wait &= ~fire & gat;                             /* (a voice whose gate closed waits for nothing) */
    return fire & gat;
}

static void chord_off(void)                             /* the gate closes: the amp envelopes release */
{
    PM.want = 0;
    if (DG.gate_open && DG.track >= 0) {
        DG.off_block = GL.blocks;
        DG.tail = tail_blocks((uint32_t)DG.track);
    }
    dg_gate_off(&T);
    DG.hurry = 1;
    DG.gate_open = DG.latched = 0;
    redraw();                                           /* the pages stop showing the chord's name */
}

/* the chord's name for the pages: root, quality, extension ("C MAJ7", "D MIN7", "G 7", "B DIM", "F SUS ADD9") */
static void name_chord(uint32_t root, uint32_t pcs)
{
    static const char *const NOTE[12] = {"C", "C#", "D", "EB", "E", "F", "F#", "G", "AB", "A", "BB", "B"};
    uint32_t r = root % 12;
    char *e = put(dg_name, NOTE[r]);
#define HAS(x) ((pcs >> ((r + (x)) % 12)) & 1)
    int maj = HAS(4), min = HAS(3) && !maj, dim = min && HAS(6) && !HAS(7), sus = !maj && !min && HAS(5);
    int six = HAS(9), sev = HAS(10), ma7 = HAS(11), nin = HAS(2);
    if (dim && (sev || six)) {                          /* half-diminished, diminished seventh */
        put(e, sev ? " MIN7B5" : " DIM7");
        return;
    }
    e = put(e, dim ? " DIM" : min ? " MIN" : sus ? " SUS" : (six || sev || ma7 || nin) ? " " : " MAJ");
    if ((dim || min || sus) && (ma7 || (nin && !sev && !six)))
        e = put(e, " ");                                /* "B MIN MAJ7", "F SUS ADD9" */
    if (ma7)
        e = put(e, nin ? "MAJ9" : "MAJ7");
    else if (sev)
        e = put(e, nin ? "9" : "7");
    else if (six)
        e = put(e, nin ? "6/9" : "6");
    else if (nin)
        e = put(e, "ADD9");
#undef HAS
    (void)e;
}

/* the settings a sounding chord is built from, packed: a change re-voices it at once */
static uint32_t chord_sig(void)
{
    return dg_ui[K_TYPE] | (uint32_t)dg_ui[K_EXT] << 2 | (uint32_t)dg_ui[K_KEY] << 5 | (uint32_t)dg_ui[K_BASS] << 10 |
           (uint32_t)dg_ui[K_VCNT] << 13 | (uint32_t)dg_ui[K_VOIC] << 16 | (uint32_t)dg_ui[K_POS] << 23;
}

/* a chord event (the notes collected so far in DG.ev_notes) -> the core. One key = one chord: the lowest note is
 * the root; TYPE / EXT / KEY give its tones (dg_chord_for); a p-locked TYPE or EXT on the step beats KEY. */
static void fire_event(void)
{
    uint32_t i, j, lo, cw, w, sounding = 0;
    uint8_t nt[EV_MAX];
    for (i = 0; i < DG.ev_n; i++) {                     /* the event's notes, ascending */
        uint8_t x = DG.ev_notes[i];
        for (j = i; j > 0 && nt[j - 1] > x; j--)
            nt[j] = nt[j - 1];
        nt[j] = x;
    }
    /* the root is the lowest note, but not a detached bass: stock chord mode can add a note one or two octaves under
     * the chord (KEYBOARD SETUP, BASS OCT), and the chord is not built on that */
    for (i = 0; i + 1 < DG.ev_n && nt[i + 1] - nt[i] > 12; i++)
        ;
    lo = DG.ev_n ? nt[i] : 60;
    if (lo < DG_ROOT_LO)
        lo = DG_ROOT_LO;
    if (lo > DG_ROOT_HI)
        lo = DG_ROOT_HI;
    w = dg_chord_for((int32_t)lo, dg_ui[K_TYPE], dg_ui[K_EXT], dg_ui[K_KEY],
                     ((DG.locks >> K_TYPE) & 1) | ((DG.locks >> K_EXT) & 1) << 1);
    cw = DG_CW(lo, w & 0xFFF);
    if (DG.ev_fired && cw == DG.ev_ident)
        return;                                         /* a later note of the same event that changes nothing */
    for (i = 0; i < DG_NV; i++)
        sounding |= T.v[i].on;
    /* (not while another note of the track is still down: that is the same key's own trig or repeat, not a
     * second press) */
    if (!DG.ev_fired && DG.ev_latched && !DG.ev_seq && !DG.ev_legato && DG.latched && sounding && cw == DG.l_ident) {
        chord_off();                                    /* the same chord again: let it fade */
        DG.releases++;
    } else {
        uint32_t tw = TEMPO_WORD, tail, flags = 0;
        engine_params(&dg_cur);
        dg_cur.key = (uint8_t)((w >> 12) & 0xF);
        dg_cur.scl = (uint8_t)((w >> 16) & 0xF);
        if (dg_cur.vcnt > DG.nres)
            dg_cur.vcnt = (uint8_t)DG.nres;
        if (tw >= 30u * 120u && tw <= 300u * 120u)
            T.tempo = tw;
        /* build 21: STRM and STRU strike every trig, legato or held, at the new chord's own notes. Through image 20
         * a trig that overlapped the last glided into it unstruck (only a pattern's first chord was strummed), and
         * a held chord was strummed at the old chord's notes and then glided (experiments/b21_strum_real.py). A
         * strum does not glide; a chord setting turned while it sounds still does (the re-voicing reads GLID). */
        if (dg_ui[K_PLAY] == PM_STRM || dg_ui[K_PLAY] == PM_STRU)
            dg_cur.glid = 0;
        if (dg_cur.glid == 0 && sounding) {             /* GLID 0: no glide, the chord retriggers */
            dg_gate_off(&T);
            DG.reattack = 1;
            sounding = 0;
        }
        /* a separate key press or trig strikes the held chord again, and it still glides. The strike does not cut
         * the chord: every voice DigiGlide plays has AMP RSET off in its frame record (dg_tx), so the amp envelope
         * goes on from its level instead of restarting from silence. (Builds 7 and 8 struck with the sound's own
         * RSET: a slow pad fell silent at every trig. Build 9 struck no sustaining sound: "no attack per trig".
         * Builds 10 and 11 chose by AMP ATK.) Overlapping keys never attack. */
        if (sounding && !DG.ev_legato && !DG.ev_fired)
            DG.reattack = 1;
        tail = dg_cur.glid != 0 && !sounding && DG.tail && GL.blocks - DG.off_block < DG.tail;
        if (tail)                                       /* the last chord still rings: attack and glide from it */
            flags |= DG_CW_TAIL;
        dg_tail_log = dg_tail_log << 1 | tail;
        DG.last_tempo = T.tempo;
        DG.last_note = lo;
        DG.step_log[DG.trigs & 15] = (uint8_t)DG.last_step;
        dg_trig(&T, (int32_t)DG.last_step, &dg_cur, cw | flags);
        bp_trig();                                      /* build 23: bass pattern, restrike */
        name_chord(lo, w & 0xFFF);
        redraw();
        DG.last_cw = cw;
        PM.want = 1;                                    /* HARP: a new chord runs */
        DG.hurry = 1;
        DG.sig = chord_sig();
        DG.trigs++;
        DG.active = 1;
        DG.gate_open = 1;
        DG.latched = DG.ev_latched;
        DG.l_ident = cw;
        DG.ctl = ((1u << DG.nres) - 1) << DG.base;
    }
    DG.ev_fired = 1;
    DG.ev_ident = cw;
    DG.events++;
}

int dg_arp_single(uint32_t t);

/* ------------------------------------------------------------------ build 23: bass patterns, BLOOM, restrike
 * BPAT (BASS on: Follow or Solo): the bass voice plays a pattern on a grid of BRATE (1/4, 1/8, 1/16) from the tempo
 * instead of holding its note (Brickchord's _bass_start / _bass_step, the owner's spec). Step i since the pattern's
 * start: even steps at full level, odd at 80 % (Offbeat's notes, all on odd steps, at full level); each note 80 % of
 * the step; a new note is plucked (AMP RSET on, as a strum's string). The pattern starts at step 0 on a trig whose
 * root differs from the last; a trig on the same root goes on with the pattern. The fifth is the chord's own (6 on a
 * DIM chord, 8 on an augmented one), the third the chord's (4 or 3, else 2 or 5 on a SUS chord, else the octave).
 *   1 PULS root every step     2 OCT root, +12        3 WALK root root fifth +12    4 R-5 root fifth
 *   5 ARP root third fifth third   6 OFFB rest, root    7 3+3+2 root on steps 1, 4, 7 of eight
 * The pattern's note is the bass voice's target (the root in BASS's octave, with its drift and vibrato but not its
 * glide: a walking bass lands on each note) plus the step's interval.
 * BLOOM (centre 64 = off): below, the upper voices fade out one by one from the top, toward the bass alone; above,
 * each upper voice's level breathes at its own rate (the voices' VIB rates, 0.15 to 0.40 Hz), deeper as BLOOM rises
 * (at most 12 dB). "Upper" is every voice but the lowest (the bass voice when BASS is on). Each voice's level word
 * follows its target with a 20 ms smoothing. Read every 20 ms like the chord settings, so it can be turned live.
 * STRK (HOLD on, the chord held): the held chord is struck again every 1, 2 or 4 beats from the trig, rising from its
 * level (the voices are DigiGlide's reserved ones, so the last strike cannot ring on under the new). */
#define Q8_16TH (2700000u * 256u)                       /* a sixteenth, blocks Q8, times the tempo word */
static struct {
    uint32_t pos8, k;                                   /* place in the step, step since the start */
    int32_t root, off;                                  /* the root the pattern started on; the step's interval */
    uint8_t run, gate, strike, pend, full, slow;          /* slow: the sound's AMP ATK >= 32 (build 24) */
} BPS[NE], *bpp = BPS;
#define BP (*bpp)
static uint32_t rs_pos4_s[NE];
#define rs_pos4 (rs_pos4_s[cx])
//                              /* restrike: blocks Q4 since the last strike */
static int32_t lv_cur_s[NE][DG_NV], lv_gain_s[NE][DG_NV];
#define lv_cur (lv_cur_s[cx])
#define lv_gain (lv_gain_s[cx])
//         /* level: attenuation now (0 = none), gain wanted, Q15 */
uint32_t dg_bp_strikes, dg_restrikes;                   /* tests */
static uint8_t lv_busy_s[NE];
#define lv_busy (lv_busy_s[cx])
//                               /* a level is not at rest (build 28) */

static void bp_trig(void)
{
    if (!BP.run || T.aroot != BP.root)
        BP.pend = 1;
    rs_pos4 = 0;
}

static int32_t pc_has(uint32_t pcs, int32_t root, int32_t iv) { return (int32_t)((pcs >> ((root + iv) % 12)) & 1); }

/* the step's interval in semitones, or -1 for a rest */
static int32_t bp_interval(uint32_t pat, uint32_t k, uint32_t pcs, int32_t root)
{
    int32_t fifth = pc_has(pcs, root, 7) ? 7 : pc_has(pcs, root, 6) ? 6 : pc_has(pcs, root, 8) ? 8 : 7;
    int32_t third = pc_has(pcs, root, 4) ? 4 : pc_has(pcs, root, 3) ? 3 : pc_has(pcs, root, 2) ? 2
                  : pc_has(pcs, root, 5) ? 5 : 12;
    switch (pat) {
    case 1: return 0;
    case 2: return k & 1 ? 12 : 0;
    case 3: { static const int8_t W[4] = {0, 0, 0, 12}; return (k & 3) == 2 ? fifth : W[k & 3]; }
    case 4: return k & 1 ? fifth : 0;
    case 5: return (k & 1) ? third : (k & 2) ? fifth : 0;
    case 6: return k & 1 ? 0 : -1;
    case 7: return (k & 7) == 0 || (k & 7) == 3 || (k & 7) == 6 ? 0 : -1;
    default: return 0;
    }
}

/* one block: the bass pattern (-> 1 if it plays the bass voice), the restrike, the level gains */
int32_t dg_sin29(uint32_t ph);
NI static int bp_block(int32_t bs, uint32_t mask, const int32_t *out, int n)
{
    uint32_t tw = T.tempo ? T.tempo : 14400, pat = dg_ui[K_BPAT], i;
    int on = bs >= 0 && pat && pat <= 7 && DG.active && ((mask >> (8 + bs)) & 1);
    BP.strike = 0;
    if (!on) {
        BP.run = BP.pend = BP.gate = 0;
    } else {
        uint32_t l8 = Q8_16TH * (4u >> (dg_ui[K_BRATE] > 2 ? 1 : dg_ui[K_BRATE])) / tw;
        if (!BP.run || BP.pend) {
            BP.run = 1;
            BP.pend = 0;
            BP.root = T.aroot;
            BP.pos8 = 0;
            BP.k = 0;
            BP.strike = 1;
        } else {
            BP.pos8 += 256;
            if (BP.pos8 >= l8) {
                BP.pos8 = BP.pos8 - l8 < l8 ? BP.pos8 - l8 : 0;
                BP.k++;
                BP.strike = 1;
            }
        }
        if (BP.strike) {
            BP.off = bp_interval(pat, BP.k, DG.last_cw & 0xFFF, BP.root % 12);
            BP.gate = BP.off >= 0;
            BP.full = !(BP.k & 1) || pat == 6;
            BP.slow = DG.track >= 0 && sound_slot((uint32_t)DG.track, 81) >= (32 << 8);   /* AMP ATK */
            BP.strike = BP.gate;
            dg_bp_strikes += BP.strike;
        } else if (BP.gate && BP.pos8 >= l8 / 5 * 4)
            BP.gate = 0;
    }
    /* restrike */
    if (dg_ui[K_STRK] && dg_ui[K_HOLD] && DG.latched && DG.active) {
        uint32_t l4 = (2700000u * 16u * 4u / tw) * (dg_ui[K_STRK] == 3 ? 4u : dg_ui[K_STRK]);
        rs_pos4 += 16;
        if (rs_pos4 >= l4) {
            rs_pos4 -= l4;
            DG.reattack = 1;
            PM.want = 1;                                /* HARP: the run again */
            dg_restrikes++;
        }
    } else
        rs_pos4 = 0;
    /* level gains: BLOOM on the upper voices, the bass pattern's accent on the bass voice */
    /* build 28: BLOOM at its centre, no bass voice or BAL at its centre, every level at rest: nothing to work out */
    if (dg_ui[K_BLOOM] == 64 && (bs < 0 || bs >= DG_NV || dg_ui[K_BAL] == 64) && !lv_busy)
        return on;
    {
        int32_t b = (int32_t)dg_ui[K_BLOOM] - 64, lo = -1;
        uint8_t ord[DG_NV];
        uint32_t m = 0, u, j;
        for (i = 0; i < DG_NV; i++)
            lv_gain[i] = 32767;
        for (i = 0; i < (uint32_t)n && i < DG_NV; i++) {     /* the chord voices by pitch, high first */
            if (!((mask >> i) & 1))
                continue;
            for (j = m; j > 0 && out[ord[j - 1]] < out[i]; j--)
                ord[j] = ord[j - 1];
            ord[j] = (uint8_t)i;
            m++;
        }
        if (bs < 0 || dg_cur.bass >= 4)                 /* no bass voice under them: the lowest is the bass */
            lo = m ? ord[--m] : -1;
        (void)lo;
        u = m;                                          /* the upper voices: ord[0..u-1], top first */
        for (j = 0; j < u; j++) {
            int32_t g = 32767;
            if (b < 0) {
                int32_t f = (-b) * (int32_t)u * 4 - (int32_t)j * 256;      /* Q8 voices faded from the top */
                f = f < 0 ? 0 : f > 256 ? 256 : f;
                g = 32767 * (256 - f) / 256;
            } else if (b > 0) {
                int32_t sn = dg_sin29(T.v[ord[j]].ph) >> 14;               /* Q15, -1..1 */
                g = 32767 - b * (32767 / 4 * 3 / 63) * (32768 + sn) / 65536;
            }
            lv_gain[ord[j]] = g;
        }
        /* (the pattern's 80 % accent is applied in the frame, under the level word's cap: build 24) */
        /* build 24: BAL, the bass voice against the chord (owner: "bass is quiet": one voice under 3..5, about 6 dB
         * under a 4-voice chord, experiments/b23_bass_level.py). Centre 0: as image 23. Up: the bass to x 2 (its
         * level word stops at 127), the chord down to 25 % (-12 dB) at +63. Down: the bass fades out at -64. */
        if (bs >= 0 && bs < DG_NV) {
            int32_t bal = (int32_t)dg_ui[K_BAL] - 64, gb = 32767, gc = 32767;
            if (bal > 0) {
                gb = 32767 + bal * 32767 / 63;
                gc = 32767 - bal * (32767 / 4 * 3) / 63;
            } else if (bal < 0)
                gb = 32767 * (64 + bal) / 64;
            for (i = 0; i < DG_NV; i++)
                lv_gain[i] = (int32_t)((uint32_t)lv_gain[i] * (uint32_t)((int32_t)i == bs ? gb : gc) / 32767u);
        }
        for (i = 0; i < DG_NV; i++) {
            int32_t a = 32767 - lv_gain[i], d = a - lv_cur[i];
            lv_cur[i] = d < 30 && d > -30 ? a : lv_cur[i] + d / 30;
            if (on && (int32_t)i == bs)
                lv_cur[i] = a;                          /* (the bass note's accent is set at its pluck) */
        }
        for (i = 0, lv_busy = 0; i < DG_NV; i++)
            lv_busy |= lv_cur[i] != 0;
    }
    return on;
}

/* ------------------------------------------------------------------ build 28: nothing heavy on a note frame
 * The hook runs before the driver sends the frame, so its time delays that very frame, and a frame later than its
 * render is dropped with its note-ons: every track's notes of the step (owner, image 25, video: the pattern loses bass
 * and rhythm with DigiGlide on; measured, notes/build_log.md). Through image 27 the chord's own work (24 parameters
 * read, voice leading, the name) ran on the frame that carried the step's note-ons, and all 24 parameters were read
 * again every 30 blocks on whatever frame came up.
 *   - A chord event is only noted on its note frame (PD) and worked out at the end of the first frame that sends no
 *     note-on (after DEFER_MAX frames at the latest), so its own note-ons go out on a frame after that, alone.
 *   - A sounding chord's parameters are read one a block (a round in DG_NP blocks, 16 ms), never on a frame that
 *     carries stock note-ons; all of them again only when one has changed.
 * dg_forced: events worked out on a note frame after all (the wait ran out). dg_defer_max: the longest wait. */
#define DEFER_MAX 6
static struct {
    uint8_t n, wait, legato, chordy;
    uint8_t notes[EV_MAX];
    uint32_t stock, t, step;
} PDS[NE], *pdp = PDS;
#define PD (*pdp)
uint32_t dg_events_deferred;
static uint8_t lv_dirty_s[NE], lv_force_s[NE], lv_rot_s[NE];
static uint32_t lv_seen_step_s[NE] = {0xFFFF, 0xFFFF};
#define lv_dirty (lv_dirty_s[cx])
#define lv_force (lv_force_s[cx])
#define lv_rot (lv_rot_s[cx])
#define lv_seen_step (lv_seen_step_s[cx])

static void sel(uint32_t s)
{
    cx = s;
    tp = &TS[s]; dgp = &DGS[s]; pmp = &PMS[s]; bpp = &BPS[s]; pdp = &PDS[s];
}

NI static void run_event(void)
{
    uint32_t i;
    read_ui(PD.t, PD.step);
    if (!DG.ev_open || GL.blocks - DG.ev_start > WIN_BLOCKS) {
        DG.ev_open = 1;
        DG.ev_start = GL.blocks;
        DG.ev_n = DG.ev_chordy = DG.ev_fired = 0;
        DG.ev_legato = PD.legato;                       /* another key (or trig) of the track was still down */
        /* HOLD: the chord stays after the key or the trig ends, so a recording plays back as it sounded while
         * it was played. Only a key played by hand releases it by playing the same chord again: a sequenced
         * trig (the sequencer plays and the step has a trig) repeating a chord just plays it again. */
        DG.ev_latched = dg_ui[K_HOLD];
        /* sequenced or played by hand: the unit's own keys are the trig keys, and a hand-played note arrives
         * while one is down. (The first rule, "the playing step has a trig", failed on the unit: live-recorded
         * trigs are micro-timed and fire while the playhead still shows the step before.) */
        DG.ev_seq = PLAY_FLAG == 1 && !(KEYS_HELD[3] | KEYS_HELD[4]);       /* TRIG 1..16 = codes 25..40 */
    }
    for (i = 0; i < PD.n && DG.ev_n < EV_MAX; i++)
        DG.ev_notes[DG.ev_n++] = PD.notes[i];
    /* three notes in one block: stock chord mode is on, and its voicing hides which key was pressed (the root
     * may be wrong): say so. Build 26: once a track until power off, it repeated on every chord trig. */
    if (PD.chordy && !GL.msg_until && DG.track >= 0 && !(dg_cmwarn >> DG.track & 1)) {
        dg_cmwarn |= (uint16_t)(1u << DG.track);
        put(msg, "CHORD MODE ON?");
        GL.msg_until = GL.blocks + MSG_BLOCKS;
        redraw();
    }
    fire_event();
    DG.ctl &= ~PD.stock;
    PD.n = PD.wait = PD.chordy = 0;
    PD.stock = 0;
    lv_dirty = lv_force = 0;
    dg_events_deferred++;
}

/* build 28: the hook's own time on the unit, for the status box ([FUNC] + push G), read from DTIM3's counter (stock
 * runs it for the main loop's 30 Hz tick: bus clock / 16 = 8.25 counts a microsecond, wrapping at DTRR3). Read only
 * while the box is on. */
static uint32_t hk_max, hk_note, hk_min = 0xFFFFFFFFu;
static void dg_tx_body(void);

void dg_tx(void)
{
    uint32_t t0, dt, noted;
    if (!GL.dbg) {
        dg_tx_body();
        return;
    }
    noted = (rd16(FRAME, 0x22) | rd16(FRAME, 0x24)) != 0;
    t0 = DTCN3;
    dg_tx_body();
    dt = DTCN3;
    dt = dt >= t0 ? dt - t0 : dt + DTRR3 + 1 - t0;
    if (dt > hk_max)
        hk_max = dt;
    if ((noted || rd16(FRAME, 0x22) || rd16(FRAME, 0x24)) && dt > hk_note)
        hk_note = dt;
    if ((DGS[0].ctl || DGS[1].ctl) && dt < hk_min)
        hk_min = dt;
    if (!(GL.blocks & 2047)) {                          /* the worst of the last 1.4 s */
        hk_show = hk_max; hk_show_note = hk_note; hk_show_min = hk_min;
        hk_max = hk_note = 0;
        hk_min = 0xFFFFFFFFu;
    }
    if ((GL.blocks & 255) == 128 && !noted && !rd16(FRAME, 0x22) && !rd16(FRAME, 0x24)) {   /* (outside the time above) */
        t0 = DTCN3;
        cal_sink += cal_loop(200);
        dt = DTCN3;
        dt = dt >= t0 ? dt - t0 : dt + DTRR3 + 1 - t0;
        if (dt < cal_i)
            cal_i = dt;
        t0 = DTCN3;
        cal_sink += cal_frame();
        dt = DTCN3;
        dt = dt >= t0 ? dt - t0 : dt + DTRR3 + 1 - t0;
        if (dt < cal_f)
            cal_f = dt;
    }
}

/* build 32: the frame's note-ons, each given to the slot that plays its track (RT, filled once a frame by dg_tx_body):
 * own = the slot a DigiGlide note belongs to, 0xFF = stock's. */
static struct { uint8_t own, synth, t, step, base, nres; } RT[16];
static uint16_t tx_non, tx_noff;                        /* the note-on / note-off words going out (every slot's) */

/* the slot for a chord note of track t (claim: the tracks slots took earlier in this frame): the slot that plays
 * the track, else the one that last did, else a slot with nothing sounding and no event waiting; NE = none */
NI static uint32_t route(uint32_t t, const uint8_t *claim)
{
    uint32_t s;
    for (s = 0; s < NE; s++)
        if (claim[s] == t)
            return s;
    for (s = 0; s < NE; s++)
        if (claim[s] == 0xFF && DGS[s].track == (int32_t)t && (DGS[s].active || DGS[s].ctl || PDS[s].n))
            return s;
    for (s = 0; s < NE; s++)
        if (claim[s] == 0xFF && DGS[s].track == (int32_t)t)
            return s;
    for (s = 0; s < NE; s++)
        if (claim[s] == 0xFF && !(DGS[s].active || DGS[s].ctl) && !PDS[s].n)
            return s;
    return NE;
}

/* build 33: what a chord voice was last sent (note, pan and level words), for the frames that carry stock note-ons */
static uint16_t nw_last_s[NE][DG_NV], pan_last_s[NE][DG_NV], lw_last_s[NE][DG_NV], rs_last_s[NE][DG_NV];
uint32_t dg_edges_late;                                 /* build 34: frames that sent held-back edges (tests) */

/* one slot's part of a frame (sel(slot) first): on, off = the words stock sent */
uint32_t dg_light;                                      /* light blocks so far (tests) */
NI static void slot_block(volatile uint8_t *f, uint16_t on, uint16_t off)
{
    uint16_t non = tx_non, noff = tx_noff;
    int32_t out[DG_NV], v;
    uint32_t i, mask, gates, stock_on = 0, nnew = 0, playing, stop, newbits = 0, light, e_on = 0, e_off = 0, ran = 0;
    uint8_t newn[EV_MAX];

    /* a preset was loaded on the DigiGlide track (its name changed): the DSP voices were silenced, so the chord
     * DigiGlide holds is gone too. Forget it, or HOLD would keep gliding a silent chord. */
    if (DG.track >= 0 && !(GL.blocks & 31) && SOUNDS) {
        volatile uint8_t *snd = sound_of((uint32_t)DG.track);
        uint32_t h = snd[0xDE];
        for (i = 4; i < 20; i++)
            h = h * 31 + snd[i];
        if (h != DG.snd_sig) {
            if (DG.snd_sig && (DG.ctl || DG.active)) {
                noff |= (uint16_t)(DG.ctl & DG.was_on);
                DG.ctl = DG.was_on = DG.held = 0;
                DG.active = DG.gate_open = DG.latched = DG.ev_open = DG.tail = 0;
                dg_init(&T, T.tempo, 0);
                DG.hurry = 1;
                dg_name[0] = 0;
                redraw();
            }
            DG.snd_sig = h;
        }
    }

    /* every note-on of a synth track whose VCNT is on is DigiGlide's: it never reaches the DSP
     * (sequencer trigs, chord mode, held keys and MIDI in all arrive here as note-ons on the track's voices); its
     * note-off is swallowed with it. Every other note-on is stock's. */
    for (v = 0; (on | off) && v < 16; v++) {            /* (build 33: nothing to look at on a frame without notes) */
        uint32_t bit = 1u << v;
        if ((off & bit) && (DG.held & bit)) {
            DG.held &= ~bit;
            noff &= (uint16_t)~bit;
        } else if ((off & bit) && (DG.ctl & bit)) {
            /* a stock note-off on a voice DigiGlide plays, for a note that is already over: a retrigged step ends
             * its first note twice (at the retrig and again at the note's own length). Let through, it silenced
             * one voice of the chord, under HOLD too (experiments/trig_var.py, image 10). */
            noff &= (uint16_t)~bit;
        }
        if (!(on & bit))
            continue;
        if (RT[v].own == cx) {
            if (!nnew) {                                /* the event's parameters: the first note's */
                uint32_t base = RT[v].base, nres = RT[v].nres;
                if (DG.ctl && (base != DG.base || nres != DG.nres)) {      /* VOICES changed under a chord */
                    noff |= (uint16_t)(DG.ctl & DG.was_on);
                    DG.ctl = DG.was_on = 0;
                    dg_gate_off(&T);
                    DG.hurry = 1;
                }
                PD.t = RT[v].t;                         /* (build 28: its parameters are read with the event) */
                PD.step = RT[v].step;
                DG.track = (int32_t)RT[v].t;
                DG.last_step = RT[v].step;
                DG.base = base;
                DG.nres = nres;
            }
            if (nnew < EV_MAX)
                newn[nnew++] = (uint8_t)(rd16(f, 0x02 + 2 * v) >> 8);
            DG.src = v;
            DG.held |= bit;
            newbits |= bit;
            GL.swallowed++;
            non &= (uint16_t)~bit;
            continue;
        }
        if (RT[v].own != 0xFF)                          /* the other slot's */
            continue;
        if (RT[v].synth && DG.active && (int32_t)RT[v].t == DG.track) {    /* VCNT OFF on this trig: a stock note, */
            chord_off();                                                    /* the chord releases */
            DG.active = 0;
        }
        stock_on |= bit;
    }
    DG.ctl &= ~stock_on;                                /* stock starts a note on a voice: it is stock's again */

    playing = PLAY_FLAG == 1;
    stop = key_held(CODE_STOP);
    if (playing)                                        /* the sequencer stopped: only after 0.2 s of "not playing" */
        DG.play_was = 300;
    else if (DG.play_was && !--DG.play_was && DG.latched)
        chord_off();
    if (DG.latched && stop && !DG.stop_was)
        chord_off();                                    /* [STOP] lets a held chord go */
    DG.stop_was = stop;
    /* the track is muted: stock sends it no more notes, so nothing would ever end a chord HOLD keeps. Let it go
     * (stock's own notes on a muted track end with their lengths). */
    if (DG.latched && DG.track >= 0 && ((MUTE_MASK >> DG.track) & 1))
        chord_off();
    /* build 25: HOLD turned off (CHORD knob H or [FUNC] + push H) while a chord is held: the chord is no longer kept.
     * It lets go below, at once if no key or trig of it is down, else when the last one ends. */
    if (DG.latched && DG.track >= 0 && !(GL.blocks & 15) && dg_par((uint32_t)DG.track, K_HOLD) != HOLD_ON)
        DG.latched = 0;                                 /* (build 28: looked at every 16th block, 11 ms) */

    if (nnew) {                                         /* build 28: noted here, worked out on a quiet frame */
        if (!PD.n)
            PD.legato = (DG.held & ~newbits) != 0;
        for (i = 0; i < nnew && PD.n < EV_MAX; i++)
            PD.notes[PD.n++] = newn[i];
        if (nnew >= 3)
            PD.chordy = 1;
    }
    if (PD.n)
        PD.stock |= stock_on;
    /* a sounding chord's parameters, one a block (never on a frame with stock note-ons): VCNT switched OFF (knob or
     * shortcut) releases it now, SCRB follows the knob (or the trig's lock), any other change is taken below */
    if (DG.active && !PD.n && !on) {
        int locked;
        uint32_t k = lv_rot;
        int32_t raw = par_at((uint32_t)DG.track, DG.last_step, k, &locked);
        lv_rot = (uint8_t)(k + 1 >= DG_NP ? 0 : k + 1);
        if (k == K_VCNT && !dg_vcnt_on(raw)) {
            chord_off();
            DG.active = 0;
        } else {
            int32_t v = dg_knob(raw, k);
            if (v != (int32_t)dg_ui[k] || (uint32_t)locked != ((DG.locks >> k) & 1))
                lv_dirty = 1;
            if (k == K_SCRB && v != T.p.scrb) {
                T.p.scrb = (uint8_t)v;
                dg_set_scrb(&T, v);
            }
        }
    }
    if (DG.active && DG.gate_open && !DG.latched && !DG.held && !PD.n)
        chord_off();                                    /* every key / trig of the chord has ended: release */

    /* build 33: a frame that carries stock notes must not be late (a late frame is dropped with every track's
     * notes: the owner's unit, image 32, one HARP track: 332 microseconds on such a frame, kick and bass lost). Stock
     * writes every voice's record and words again each block (experiments, image 33), so the chord's voices still
     * get their sound and their last note, pan and level, but the engine and everything worked out from it wait
     * for the next frame: the chord holds its pitch for one block (0.67 ms) and the engine catches up there.
     * And a chord with nothing due (no strike, release, strum or harp run, bass pattern, restrike or level on the
     * move) is worked out every second block only: its glide, drift and vibrato move 750 times a second. */
    {
        int32_t rs_on = dg_ui[K_STRK] && dg_ui[K_HOLD] && DG.latched;
        light = DG.ctl && DG.lmask && DG.owed < 3 &&
                ((on | off) || DG.pend_on || DG.pend_off || ((GL.blocks & 1) && !DG.owed && !DG.hurry && !PD.n && PM.i >= PM.n && !PM.wait &&
                                !PM.want && !DG.reattack && !BP.run && !lv_busy && !rs_on && !lv_dirty && !lv_force));
    }
    if (light) {
        dg_light++;
        for (i = 0; i < DG_NV && i < DG.nres; i++) {
            uint32_t d = DG.base + i;
            if (!((DG.ctl >> d) & 1) || !((DG.lmask >> i) & 1))
                continue;
            if (DG.active) {
                clone_voice(f, (uint32_t)DG.src, d);
                wr16(f, PAN_OFF + 146 * d, pan_last_s[cx][i]);
                wr16(f, 0x74 + 2 * d, lw_last_s[cx][i]);
            }
            wr16(f, RSET_OFF + 146 * d, (DG.pend_on >> d) & 1 ? rs_last_s[cx][i] : 0);
            wr16(f, 0x02 + 2 * d, nw_last_s[cx][i]);
        }
        DG.owed++;
    }
    /* build 34: a chord's note-ons and note-offs never ride on the frame that worked them out. That frame is the
     * heaviest there is (the engine, every voice's words), and on the unit a late frame is dropped with its note-ons
     * (owner, image 33, played by hand with BPAT: "arp starts and then the chord hits after", "sometimes the arp or
     * the chord lags on press": the chord's frame lost, the bass pattern's next note sent). They are kept and go out
     * on the next frame, which is a light one: one block (0.67 ms) later. */
    if (DG.pend_on || DG.pend_off) {
        if (light || !DG.ctl) {
            non |= (uint16_t)(DG.pend_on & DG.ctl);
            noff |= (uint16_t)DG.pend_off;
            DG.pend_on = DG.pend_off = 0;
            dg_edges_late++;
        }
    }
    if (light) {
        ;
    } else if (DG.ctl) {
        if (DG.active && !PD.n) {
            uint32_t tr = (uint32_t)DG.track;
            /* the sequencer reaches a step that holds a lock and no trig of this track's fires on it (a lock
             * under a held chord): the chord takes the step's values now (looked at once a step: build 28) */
            if (playing && PLAYHEAD[tr] != lv_seen_step) {
                lv_seen_step = PLAYHEAD[tr];
                if (lv_seen_step != DG.last_step && dg_lock_any(tr, lv_seen_step)) {
                    DG.last_step = lv_seen_step;
                    lv_force = 1;
                }
            }
            if ((DG.gate_open || DG.latched) && !on && (lv_force || (lv_dirty && GL.blocks - DG.rev_block >= 30))) {
                lv_dirty = lv_force = 0;
                DG.rev_block = GL.blocks;               /* a chord setting was turned (TYPE EXT KEY VOIC POS BASS */
                if (read_ui(tr, DG.last_step) && chord_sig() != DG.sig) {      /* VCNT): glide to the new chord */
                    uint32_t w = dg_chord_for((int32_t)DG.last_note, dg_ui[K_TYPE], dg_ui[K_EXT], dg_ui[K_KEY],
                                              ((DG.locks >> K_TYPE) & 1) | ((DG.locks >> K_EXT) & 1) << 1);
                    engine_params(&dg_cur);
                    dg_cur.key = (uint8_t)((w >> 12) & 0xF);
                    dg_cur.scl = (uint8_t)((w >> 16) & 0xF);
                    if (dg_cur.vcnt > DG.nres)
                        dg_cur.vcnt = (uint8_t)DG.nres;
                    DG.last_cw = DG_CW(DG.last_note, w & 0xFFF);
                    DG.l_ident = DG.last_cw;
                    dg_trig(&T, (int32_t)DG.last_step, &dg_cur, DG.last_cw | DG_CW_REVOICE);
                    PM.want = 1;                        /* HARP: a change of a sounding chord runs again */
                    name_chord(DG.last_note, w & 0xFFF);
                    DG.sig = chord_sig();
                    redraw();
                }
            }
        }
        int32_t src_pan = (int32_t)rd16(f, 0xda + 146 * (uint32_t)DG.src + 128);   /* before any voice's own pan */
        uint32_t src_lv = rd16(f, 0x74 + 2 * (uint32_t)DG.src);   /* build 24: and before any voice's own level */
        uint32_t pm_fire;
        int32_t bs = dg_cur.bass && dg_cur.vcnt >= 1 ? (int32_t)dg_cur.vcnt - 1 : -1;   /* the bass voice */
        int bp;
        ran = DG.owed;
        for (; DG.owed; DG.owed--) {                    /* the blocks the engine waited (above): its time is whole */
            dg_block(&T, out);
            if (BP.run)
                BP.pos8 += 256;
            rs_pos4 += 16;
        }
        mask = dg_block(&T, out);
        DG.lmask = mask;
        DG.hurry = 0;
        gates = 0;
        bp = bp_block(bs, mask, out, bs >= 0 ? bs : (int)dg_cur.vcnt);
        {   /* build 19: the PLAY modes start some voices later than the engine does (pm_block) */
            uint32_t att = 0, gat = 0;
            for (i = 0; i < DG_NV && i < DG.nres; i++) {
                uint32_t bit = 1u << (DG.base + i);
                if (!(DG.ctl & bit) || !((mask >> i) & 1) || !((mask >> (8 + i)) & 1) || (bp && (int32_t)i == bs))
                    continue;
                gat |= 1u << i;
                if (!(DG.was_on & bit) || DG.reattack)
                    att |= 1u << i;
            }
            pm_fire = pm_block(dg_ui[K_PLAY], att, gat, out);
        }
        for (i = 0; i < DG_NV; i++) {
            uint32_t d = DG.base + i, bit = 1u << d;
            uint16_t nw_was = nw_last_s[cx][i], lw_was = lw_last_s[cx][i];
            if (i >= DG.nres || !(DG.ctl & bit))
                continue;
            if (!((mask >> i) & 1)) {                   /* never started: silent */
                DG.ctl &= ~bit;
                continue;
            }
            if (DG.active) {                            /* engaged: the latest note's sound, every block */
                uint32_t src = (uint32_t)DG.src;
                int32_t pan;
                clone_voice(f, src, d);
                pan = src_pan + T.v[i].pan / 2;                 /* +-1.0 = +-64 knob */
                if (pan < 0)
                    pan = 0;
                if (pan > 0x7F00)
                    pan = 0x7F00;
                wr16(f, PAN_OFF + 146 * d, (uint16_t)pan);
                pan_last_s[cx][i] = (uint16_t)pan;
            }
            /* the amp envelope never restarts from zero on a voice DigiGlide plays: an attack on a voice that
             * still sounds (a strike on a held chord, a new chord over the last one's release) rises from where
             * it is. On a silent voice it makes no difference. The sound's own AMP RSET is not used here.
             * build 22: except a string's turn in a strum or a harp run: it is plucked, its envelope restarts from
             * silence. Through image 21 a strum over a chord still sounding (HOLD on, legato trigs) changed each
             * string's pitch in turn with no attack: the old chord seemed to hold over the strum
             * (experiments/b22_hold_audio.py). */
            int bpv = bp && (int32_t)i == bs;          /* build 23: the bass voice plays its pattern */
            /* (build 24: a pattern note on a slow attack, AMP ATK >= 32, rises from where the bass is: plucked, a
             * 1/8 note ended before it was loud, about 5 dB down at ATK 60, experiments/b23_bass_level.py) */
            rs_last_s[cx][i] = ((pm_fire >> i) & 1) || (bpv && BP.strike && !BP.slow) ? 256 : 0;
            wr16(f, RSET_OFF + 146 * d, rs_last_s[cx][i]);
            if (DG.active) {                            /* build 23: BLOOM, the bass accent; build 24: BAL */
                /* (from the source's level: the source is often one of these voices, already scaled in this
                 * block; image 23 scaled the others twice) */
                uint32_t lw = lv_cur[i] ? src_lv * (uint32_t)(32767 - lv_cur[i]) >> 15 : src_lv;
                if (lw > 0x7F00)
                    lw = 0x7F00;
                if (bpv && !BP.full)
                    lw = lw * 26214u >> 15;             /* the pattern's odd steps: 80 % */
                {   /* build 27: a strum over a chord that still sounds (HOLD on, legato trigs) damps the strings:
                     * one waiting for its turn fades out in DAMP_BLOCKS and comes back plucked. Through image 26 it
                     * rang on at the last chord's note until its turn, the low strings longest on a strum down
                     * (owner, image 25: "strum down still doesn't work with chord hold on", "a ring holding over") */
                    static uint8_t damp_s[NE][DG_NV];
                    uint8_t *damp = damp_s[cx];
                    if (!bpv && ((PM.wait >> i) & 1) && ((DG.was_on >> d) & 1) &&
                        (dg_ui[K_PLAY] == PM_STRM || dg_ui[K_PLAY] == PM_STRU)) {
                        damp[i] = (uint8_t)(damp[i] + 1 + ran);     /* (build 33: and the blocks caught up) */
                        if (damp[i] > DAMP_BLOCKS)
                            damp[i] = DAMP_BLOCKS;
                        lw = lw * (uint32_t)(DAMP_BLOCKS - damp[i]) / DAMP_BLOCKS;
                    } else {
                        damp[i] = 0;
                    }
                }
                wr16(f, 0x74 + 2 * d, (uint16_t)lw);
                lw_last_s[cx][i] = (uint16_t)lw;
            }
            {   /* build 21: a string waiting for its turn in a strum keeps ringing at its last note */
                uint16_t *nw_last = nw_last_s[cx];
                if (bpv) {
                    if (BP.strike || BP.gate)           /* (each note lands: the bass's target, not its glide) */
                        nw_last[i] = note_word(out[i] - T.v[i].cur + T.v[i].tgt + BP.off * 6553600);
                } else if (!((PM.wait >> i) & 1) || !((DG.was_on >> d) & 1))
                    nw_last[i] = note_word(PM.hn[i] ? PM.hn[i] + out[i] - T.v[i].cur : out[i]);
                wr16(f, 0x02 + 2 * d, nw_last[i]);
            }
            if (((mask >> (8 + i)) & 1) && (!bpv || BP.gate))
                gates |= bit;
            if (bpv) {
                if (BP.strike)
                    e_on |= bit;
            } else if ((gates & bit) && (!(DG.was_on & bit) || DG.reattack) && !((PM.wait >> i) & 1))
                e_on |= bit;
            if ((pm_fire >> i) & 1)                     /* its turn in a strum or a harp run */
                e_on |= bit;
            if (!(gates & bit) && (DG.was_on & bit))
                e_off |= bit;
            if (e_on & bit) {                           /* build 34: its note-on goes out a frame later: until */
                wr16(f, 0x02 + 2 * d, nw_was);          /* then the voice keeps the note and level it had */
                if (DG.active)
                    wr16(f, 0x74 + 2 * d, lw_was);
            }
        }
        if (DG.pend_on | DG.pend_off) {                 /* (edges still waiting, no light frame came: with these) */
            non |= (uint16_t)((DG.pend_on | e_on) & DG.ctl);
            noff |= (uint16_t)(DG.pend_off | e_off);
            DG.pend_on = DG.pend_off = 0;
        } else {
            DG.pend_on = e_on;                          /* build 34: sent on the next frame */
            DG.pend_off = e_off;
        }
        DG.was_on = gates;
        DG.reattack = 0;
        for (i = DG.nres; i < DG_NV; i++)               /* core voices past the reserved block: silent */
            T.v[i].on = 0;
    }
    tx_non = non;
    tx_noff = noff;
}

static void dg_tx_body(void)
{
    volatile uint8_t *f = FRAME;
    uint16_t on = rd16(f, 0x22), off = rd16(f, 0x24);
    uint32_t s, v, i;

    GL.blocks++;
    shortcut_tick();

    /* every note-on of a synth track whose VCNT is on is DigiGlide's, if a slot is free for its track */
    if (on) {
        uint8_t claim[NE];
        for (s = 0; s < NE; s++)
            claim[s] = 0xFF;
        for (v = 0; v < 16; v++) {
            uint32_t t, step, base = 0, nres;
            int locked, p_on;
            if (!((on >> v) & 1))
                continue;
            t = rd16(f, 0xa5a + 2 * v);
            RT[v].own = 0xFF;
            RT[v].synth = 0;
            if (!dg_synth(t))
                continue;
            RT[v].synth = 1;
            RT[v].t = (uint8_t)t;
            step = PLAYHEAD[t];
            p_on = dg_vcnt_on(par_at(t, step, K_VCNT, &locked));
            nres = voice_range(t, &base);
            if (p_on) {
                GL.seen_on++;
                GL.dbg_base = base;
                GL.dbg_nres = nres;
                GL.dbg_v = v;
            }
            if (p_on && nres >= 3 && !dg_arp_single(t)) {   /* (the arp's notes are single stock notes) */
                s = route(t, claim);
                if (s < NE) {
                    claim[s] = (uint8_t)t;
                    RT[v].own = (uint8_t)s;
                    RT[v].step = (uint8_t)step;
                    RT[v].base = (uint8_t)base;
                    RT[v].nres = (uint8_t)nres;
                }                                       /* else: both slots sound other tracks, a stock note */
            } else if (DGS[0].track < 0 || !(DGS[0].active || DGS[0].ctl) || (int32_t)t == DGS[0].track) {
                GL.stock_trigs++;
            }
        }
    }
    tx_non = on;
    tx_noff = off;
    for (s = 0; s < NE; s++) {
        sel(s);
        slot_block(f, on, off);
    }
    if (tx_non != on || tx_noff != off) {
        wr16(f, 0x22, tx_non); wr16(f, 0x26, tx_non);
        wr16(f, 0x24, tx_noff); wr16(f, 0x28, tx_noff);
    }
    {   /* build 28: an event is worked out on a frame that sends no note-on; build 30: and no note-off (a late frame
         * is dropped whole); build 32: one event a frame, the slots in turn */
        static uint8_t turn;
        uint32_t done = 0;
        for (i = 0; i < NE; i++) {
            s = (turn + i) % NE;
            sel(s);
            if (!PD.n)
                continue;
            if (!done && (!(tx_non | tx_noff) || PD.wait >= DEFER_MAX)) {
                if (tx_non | tx_noff)
                    dg_forced++;
                if (PD.wait > dg_defer_max)
                    dg_defer_max = PD.wait;
                run_event();
                done = 1;
                turn = (uint8_t)((s + 1) % NE);
            } else if (PD.wait < 255) {
                PD.wait++;
            }
        }
    }
    sel(0);
}

/* ------------------------------------------------------------------ build 18: the stock arpeggiator plays the chord
 * Stock (notes/build_log.md, "Build 18"): the sequencer's note handler gives a track's notes to the arp with "notes
 * in" (0x40029cd4, one call site) when the sound's arp MODE (+351) is not OFF; a key release takes its note out
 * with "note out" (0x40029fa6, one call site); the arp then sends one note per arp step down the ordinary note
 * path. Both call sites come here. On a DigiGlide track the arp gets the chord of the key (TYPE, EXT, KEY and the
 * step's locks; POS moves the figure through the chord's inversions) in place of the key, and dg_tx lets the arp's
 * notes through as single stock notes. MODE CHRD (all notes on every step) is left as it was: the whole DigiGlide
 * chord is struck on every step. */
#define ARP_MODE 351
#define ARP_CHRD 7
typedef int32_t (*arp_in_fn)(uint32_t, uint8_t *, uint8_t *, int32_t, uint32_t, uint32_t, uint32_t, uint8_t *,
                             uint32_t *, uint32_t *);
#define ARP_IN ((arp_in_fn)OSA_40029CD4)
#define ARP_OUT ((int32_t (*)(uint32_t, uint32_t))OSA_40029FA6)
#define ARP_KEYS 4
static struct { uint8_t root, n, note[7]; } arp_key[16][ARP_KEYS];   /* per track: the keys down and what they added */
uint32_t dg_arp_ins, dg_arp_outs;                       /* chords given to the arp, keys taken out (tests) */
uint8_t dg_arp_last[8];                                 /* the notes last given: count, then the notes (tests) */

int dg_arp_single(uint32_t t)                           /* the arp plays this DigiGlide track's chord note by note */
{
    uint32_t m;
    if (t >= 16 || !SOUNDS || !dg_synth(t))
        return 0;
    m = sound_of(t)[ARP_MODE];
    return m && m != ARP_CHRD && dg_vcnt_on(dg_par(t, K_VCNT));
}

static uint32_t arp_chord(uint32_t t, uint32_t root, uint8_t *out)
{
    uint32_t step = PLAYHEAD[t], w, i, n = 0;
    int l1, l2, l3;
    int32_t typ = par_at(t, step, K_TYPE, &l1) >> 8, ext = par_at(t, step, K_EXT, &l2) >> 8;
    int32_t key = par_at(t, step, K_KEY, &l3) >> 8, inv = ((par_at(t, step, K_POS, &l3) >> 8) - 64) / 8;
    int32_t nt[7];
    w = dg_chord_for((int32_t)root, typ & 3, ext & 7, key, (uint32_t)(l1 | l2 << 1));
    for (i = 0; i < 12 && n < 7; i++)                   /* close position on the key; a second is played as a ninth */
        if ((w >> ((root + i) % 12)) & 1)
            nt[n++] = (int32_t)(root + i) + (i == 1 || i == 2 ? 12 : 0);
    for (i = 1; i < n; i++) {                           /* ascending */
        int32_t x = nt[i];
        uint32_t j = i;
        for (; j > 0 && nt[j - 1] > x; j--)
            nt[j] = nt[j - 1];
        nt[j] = x;
    }
    for (; inv > 0 && n; inv--) {                       /* POS up: the lowest note goes up an octave */
        int32_t x = nt[0] + 12;
        for (i = 0; i + 1 < n; i++)
            nt[i] = nt[i + 1];
        while (n > 1 && x <= nt[n - 2])
            x += 12;
        nt[n - 1] = x;
    }
    for (; inv < 0 && n; inv++) {                       /* POS down: the highest note goes down an octave */
        int32_t x = nt[n - 1] - 12;
        for (i = n - 1; i > 0; i--)
            nt[i] = nt[i - 1];
        while (n > 1 && x >= nt[1])
            x -= 12;
        nt[0] = x;
    }
    for (i = 0; i < n; i++)
        out[i] = (uint8_t)(nt[i] < 0 ? nt[i] + 12 * ((11 - nt[i]) / 12) : nt[i] > 127 ? nt[i] - 12 * ((nt[i] - 116) / 12) : nt[i]);
    return n;
}

int32_t dg_arp_in(uint32_t t, uint8_t *rec, uint8_t *base, int32_t next, uint32_t deflen, uint32_t tbase,
                  uint32_t tick, uint8_t *snd, uint32_t *is_on, uint32_t *restarted)
{
    uint8_t one[8], nt[7];
    uint32_t i, n, k, slot = 0;
    int32_t r = 0;
    if (!rec || !snd || !snd[ARP_MODE] || !dg_arp_single(t))
        return ARP_IN(t, rec, base, next, deflen, tbase, tick, snd, is_on, restarted);
    n = arp_chord(t, rec[2], nt);
    for (k = 0; k < ARP_KEYS; k++)                      /* this key's entry, or a free one, or the first */
        if (arp_key[t][k].n && arp_key[t][k].root == rec[2])
            slot = k + 1;
    for (k = 0; !slot && k < ARP_KEYS; k++)
        if (!arp_key[t][k].n)
            slot = k + 1;
    slot = slot ? slot - 1 : 0;
    arp_key[t][slot].root = rec[2];
    arp_key[t][slot].n = (uint8_t)n;
    dg_arp_last[0] = (uint8_t)n;
    for (i = 0; i < n; i++) {
        for (k = 0; k < 6; k++)
            one[k] = rec[k];
        one[2] = nt[i];
        arp_key[t][slot].note[i] = nt[i];
        dg_arp_last[1 + i] = nt[i];
        {   /* (stock returns the arp's run id from the call that starts it, 0 from one that only adds a note) */
            int32_t x = ARP_IN(t, one, base, -1, deflen, tbase, tick, snd, is_on, restarted);
            if (x)
                r = x;
        }
    }
    dg_arp_ins++;
    return r;
}

int32_t dg_arp_out(uint32_t t, uint32_t note)
{
    uint32_t k, i, j, q;
    int32_t r = 0;
    if (t >= 16)
        return ARP_OUT(t, note);
    for (k = 0; k < ARP_KEYS; k++)
        if (arp_key[t][k].n && arp_key[t][k].root == note)
            break;
    if (k == ARP_KEYS)
        return ARP_OUT(t, note);
    for (i = 0; i < arp_key[t][k].n; i++) {             /* its notes, but not one another key still holds */
        int kept = 0;
        for (j = 0; j < ARP_KEYS; j++)
            for (q = 0; j != k && q < arp_key[t][j].n; q++)
                kept |= arp_key[t][j].note[q] == arp_key[t][k].note[i];
        if (!kept)
            r |= ARP_OUT(t, arp_key[t][k].note[i]);
    }
    arp_key[t][k].n = 0;
    dg_arp_outs++;
    return r;
}


/* the names the tests read are slot 0's */
__asm__(".globl DG\n.set DG, DGS\n.globl dg_ui\n.set dg_ui, dg_ui_s\n.globl dg_name\n.set dg_name, dg_name_s\n"
        ".globl dg_tail_log\n.set dg_tail_log, dg_tail_log_s\n.globl dg_cur\n.set dg_cur, dg_cur_s\n.globl T\n.set T, TS");

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
       K_VIB, K_SCRB, K_VCNT, K_BASS, DG_NP };
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

dg_track T;                                             /* the core's state (BSS, zeroed by the loader) */

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
} DG;

uint32_t dg_tail_log;                                   /* bit 0 = the last trig glided from a ringing chord, ... (tests) */
dg_params dg_cur;                                       /* the parameters of the last trig */
char dg_name[16];                                       /* the chord that sounds, by name (the pages show it) */
uint8_t dg_ui[DG_NP];                                   /* the 18 parameters as last read for an event (tests, UI) */
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
static const uint8_t PMAX[DG_NP] = {3, 7, 24, 127, 127, 12, 0, 1, 9, 4, 4, 6, 9, 50, 50, 127, 4, 6};
static const uint8_t PDEF[DG_NP] = {0, 0, 0, 127, 64, 2, 0, 0, 0, 0, 0, 0, 0, 8, 4, 127, 0, 2};   /* owner: VOIC 127, GLID 1/8 */

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

static int st_ok(volatile uint8_t *p)
{
    return p[0] == 'D' && p[1] == 'G' && p[2] == 'K' && p[3] == '1';
}

int dg_marked(uint32_t t)                               /* the track has DigiGlide settings of its own in this kit */
{
    volatile uint8_t *p = store();
    return p && t < 16 && st_ok(p) && (p[4 + DG_NP * t + K_HOLD] == 2 || p[4 + DG_NP * t + K_HOLD] == 3);
}

/* parameter k of track t as its raw code (the knob value << 8, as a sound slot held it): the store's, else the default */
int32_t dg_par(uint32_t t, uint32_t k)
{
    if (dg_marked(t))
        return store()[4 + DG_NP * t + k] << 8;
    return k == K_VCNT ? 0 : k == K_HOLD ? HOLD_OFF : PDEF[k] << 8;
}

void dg_par_set(uint32_t t, uint32_t k, uint32_t raw)
{
    volatile uint8_t *p = store(), *q;
    uint32_t i;
    if (!p || t >= 16 || k >= DG_NP)
        return;
    if (!st_ok(p)) {                                    /* this kit's first DigiGlide setting */
        for (i = 0; i < 16 * DG_NP; i++)
            p[4 + i] = 0;
        p[0] = 'D'; p[1] = 'G'; p[2] = 'K'; p[3] = '1';
    }
    q = p + 4 + DG_NP * t;
    if (q[K_HOLD] != 2 && q[K_HOLD] != 3) {             /* the track's first: every parameter's default, OFF */
        for (i = 0; i < DG_NP; i++)
            q[i] = PDEF[i];
        q[K_HOLD] = 2;
    }
    q[k] = (uint8_t)(raw >> 8);
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

/* Parameter k for a trig on (track, step): a p-lock, else the track's value.
 * P-locks are the sequencer's: it keeps one lane per (track, sound slot). Up to image 14 the parameters were sound
 * slots of a WAVETONE sound, so the locks made then sit in the lanes of slots 50..64, 93, 94, and WAVETONE's DSP
 * ignores those slots. They are still honoured, on a WAVETONE track that has DigiGlide settings: patterns made with
 * images <= 14 play their locked chord changes as before. A lock value that is not a value of the parameter is not a
 * DigiGlide lock (FM TONE's own locks stay in those lanes when a track's machine is changed) and is skipped.
 * This build cannot MAKE a lock: the pages' knobs are not sound slots any more (see dg_ui_sync). */
static int32_t par_at(uint32_t t, uint32_t step, uint32_t k, int *locked)
{
    volatile uint8_t *pat = PLAYING;
    *locked = 0;
    if (pat && step < 128 && k != K_PLAY && dg_mach(t) == 1 && dg_marked(t)) {
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
}

/* tests: what an event on (track, step) would read, into dg_ui; -> the lock mask | 0x80000000 if VCNT is on */
uint32_t dg_test_read(uint32_t t, uint32_t step)
{
    int on = read_ui(t, step);
    return DG.locks | (on ? 0x80000000u : 0);
}

void dg_mod_init(void)
{
    DG.blocks = DG.trigs = DG.active = DG.was_on = DG.locks = DG.ctl = DG.stock_trigs = 0;
    DG.combo_was = DG.combo_req = DG.msg_until = 0;
    DG.screen = 0;
    DG.src = DG.track = -1;
    DG.vdata = 0;
    DG.base = DG.nres = DG.held = DG.swallowed = DG.ev_open = DG.ev_n = DG.gate_open = DG.latched = 0;
    DG.play_was = DG.stop_was = DG.latch_was = DG.latch_req = DG.events = DG.releases = 0;
    DG.dbg = DG.dbg_was = DG.dbg_req = DG.seen_on = DG.seen_other = 0;
    DG.off_block = DG.tail = DG.def_was = DG.def_req = DG.sig = DG.ev_legato = DG.snd_sig = DG.ev_seq = 0;
    dg_tail_log = 0;
    dg_init(&T, 120u * 120u, 0);
    {
        uint32_t k;
        for (k = 0; k < DG_NP; k++)
            dg_ui[k] = PDEF[k];
        dg_ui[K_VCNT] = 3;
        engine_params(&dg_cur);
    }
    dg_name[0] = 0;
    DG.last_cw = DG.rev_block = DG.reattack = 0;
}

/* the per-voice words and sound record of voice s copied to voice d */
static void clone_voice(volatile uint8_t *f, uint32_t s, uint32_t d)
{
    volatile uint16_t *a = (volatile uint16_t *)(f + 0xda + 146 * s);
    volatile uint16_t *b = (volatile uint16_t *)(f + 0xda + 146 * d);
    uint32_t i;
    if (s == d)
        return;
    for (i = 0; i < 73; i++)                            /* 146 B; records are only halfword aligned */
        b[i] = a[i];
    wr16(f, 0x34 + 2 * d, rd16(f, 0x34 + 2 * s));
    wr16(f, 0x54 + 2 * d, rd16(f, 0x54 + 2 * s));
    wr16(f, 0x74 + 2 * d, rd16(f, 0x74 + 2 * s));
    wr16(f, 0x94 + 2 * d, rd16(f, 0x94 + 2 * s));
    wr16(f, 0xa5a + 2 * d, rd16(f, 0xa5a + 2 * s));
}

static uint16_t note_word(int32_t c16)                  /* Q16 cents -> note << 8 (1/256 semitone), rounded */
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
    if (DG.screen)
        DG.screen[32] = 1;                              /* the UI loop's "redraw due" (0x4011d2f4) */
}

static void shortcut_tick(void)
{
    uint32_t combo = key_held(CODE_FUNC) && key_held(CODE_ENC_E);
    if (combo && !DG.combo_was) {
        DG.combo_req = 1;                               /* handled by dg_overlay in the UI task */
        redraw();
    }
    DG.combo_was = combo;
    combo = key_held(CODE_FUNC) && key_held(CODE_ENC_H);
    if (combo && !DG.latch_was) {
        DG.latch_req = 1;
        redraw();
    }
    DG.latch_was = combo;
    combo = key_held(CODE_FUNC) && key_held(CODE_ENC_F);
    if (combo && !DG.def_was) {
        DG.def_req = 1;
        redraw();
    }
    DG.def_was = combo;
    combo = key_held(CODE_FUNC) && key_held(CODE_ENC_G);
    if (combo && !DG.dbg_was) {
        DG.dbg ^= 1;
        if (DG.dbg) {                                   /* which build is on the unit (the OS screen says 1.12) */
            dg_put(dg_msg, "DIGIGLIDE BUILD " DG_XSTR(DG_BUILD));
            DG.msg_until = DG.blocks + MSG_BLOCKS;
        }
        redraw();
    }
    DG.dbg_was = combo;
    if (DG.dbg && !(DG.blocks & 127))
        redraw();
    if (DG.msg_until) {                                 /* keep the message drawn, then erase it once */
        if (DG.blocks >= DG.msg_until) {
            DG.msg_until = 0;
            redraw();
        } else if (!(DG.blocks & 63)) {
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

/* VOICES: a track whose VCNT is on needs that many reserved DSP voices (the VOICE menu's VOICES), or stock
 * plays its notes anywhere in the 16-voice pool. Called from the UI task: raise it through stock's own setter (which
 * limits it to the voices still free) and say so; when VCNT goes OFF, put back what was there if nobody changed it. */
typedef uint32_t (*vget_fn)(void *);              /* (a pointer, but the firmware returns it in d0) */
typedef void (*vset_fn)(void *, uint32_t, int32_t);
static uint8_t v_prev[16], v_set[16], v_tried[16], v_was_on[16];
uint8_t dg_vchk[16];                                    /* the track's voices were looked at once (tests clear it) */

/* Sounds made with images <= 14 carry DigiGlide in their own slots (WAVETONE, VCNT's on-code in slot 54, HOLD's mark in
 * slot 94). On a track that has no settings of its own yet, such a sound's values are taken over once, so the owner's
 * patterns and saved sounds keep playing chords. The sound itself is left as it is. */
uint32_t dg_imported;                                   /* tracks taken over so far (tests) */

static void import_tick(void)
{
    uint32_t t, k;
    if (!SOUNDS || DG.blocks <= 3000 || !store())
        return;
    for (t = 0; t < 16; t++) {
        int32_t h;
        if (dg_mach(t) != 1 || !dg_vcnt_on(sound_slot(t, 54)) || dg_marked(t))
            continue;
        h = sound_slot(t, 94);
        if (h != HOLD_OFF && h != HOLD_ON)
            continue;
        for (k = 0; k < DG_NP; k++) {
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
static const uint8_t PMIN[DG_NP] = {0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
static const uint8_t PTOP[DG_NP] = {3, 7, 24, 127, 127, 12, 0, 3, 9, 4, 4, 6, 9, 50, 50, 127, 4, 6};

void dg_ui_sync(uint32_t t)
{
    uint8_t *kit = SOUNDS;
    uint32_t k, fresh;
    if (!kit || t >= 16)
        return;
    fresh = kit != b_kit || t != b_trk;
    b_kit = kit;
    b_trk = t;
    for (k = 0; k < DG_NP; k++) {
        volatile uint8_t *w = kit + FXBUF + 2 * (BUF_K0 + k);
        uint16_t buf = (uint16_t)(w[0] << 8 | w[1]), st = (uint16_t)dg_par(t, k);
        if (!fresh && buf != b_shadow[k] && !(buf & 0xFF) && (buf >> 8) >= PMIN[k] && (buf >> 8) <= PTOP[k]
            && dg_synth(t)) {
            dg_par_set(t, k, buf);                      /* a knob */
            st = (uint16_t)dg_par(t, k);
        }
        if (buf != st) {
            w[0] = (uint8_t)(st >> 8);
            w[1] = (uint8_t)st;
        }
        b_shadow[k] = st;
    }
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
    DG.vdata = d;
    if (!d)
        return;
    /* the first look waits until audio has run for 2 s: during start-up, before the kit is loaded, this data is
     * not the kit's yet (build 8's first try changed the start-up state: test_m55_regression) */
    settled = DG.blocks > 3000;
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
                DG.msg_until = DG.blocks + MSG_BLOCKS;
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
                    DG.msg_until = DG.blocks + MSG_BLOCKS;
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
    if (!DG.dbg)
        return 0;
    if (!which) {
        uint32_t b = 0, n = voice_range(track < 16 ? track : 0, &b);
        e = num(dbg1, "B", b, 2);
        e = num(e, "N", n, 1);
        e = num(e, "O", DG.seen_on, 2);
        e = num(e, "T", DG.swallowed, 2);
        num(e, "S", DG.stock_trigs, 2);
        return dbg1;
    }
    e = num(dbg2, "K", DG.last_note, 3);
    e = num(e, "R", (uint32_t)T.aroot, 3);
    e = num(e, "E", DG.events, 2);
    e = num(e, "L", DG.latched * 100 + DG.gate_open * 10 + dg_ui[K_HOLD], 3);
    num(e, "P", PLAY_FLAG == 1, 1);
    return dbg2;
}

/* the name of the chord sounding on `track` (the pages show it), or 0 */
const char *dg_chord_name(uint32_t track)
{
    return DG.active && (int32_t)track == DG.track && (DG.gate_open || DG.latched) && dg_name[0] ? dg_name : 0;
}

/* the end of each screen pass: remember the screen, act on a shortcut press, -> the message to draw (or 0) */
const char *dg_ui_step(volatile uint8_t *screen, uint32_t track)
{
    DG.screen = screen;
    if (DG.combo_req) {
        DG.combo_req = 0;
        toggle(track);
        DG.msg_until = DG.blocks + MSG_BLOCKS;
    }
    if (DG.latch_req) {
        DG.latch_req = 0;
        toggle_latch(track);
        DG.msg_until = DG.blocks + MSG_BLOCKS;
    }
    if (DG.def_req) {                                   /* [FUNC] + push encoder F: this sound back to the defaults */
        DG.def_req = 0;
        if (dg_synth(track)) {
            set_defaults(track);
            put(msg, "DEFAULTS SET");
        } else {
            put(msg, "DIGIGLIDE: NOT ON MIDI");
        }
        DG.msg_until = DG.blocks + MSG_BLOCKS;
    }
    import_tick();
    dg_ui_sync(track);
    voices_tick();
    return DG.msg_until && DG.blocks < DG.msg_until ? msg : 0;
}

/* the track's reserved DSP voices: stock packs the reserved blocks from voice 0 in track order
 * (experiments/m6_reserve_other.py) */
static uint32_t voice_range(uint32_t t, uint32_t *base)
{
    volatile uint8_t *d = DG.vdata;
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

static void chord_off(void)                             /* the gate closes: the amp envelopes release */
{
    if (DG.gate_open && DG.track >= 0) {
        DG.off_block = DG.blocks;
        DG.tail = tail_blocks((uint32_t)DG.track);
    }
    dg_gate_off(&T);
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
        tail = dg_cur.glid != 0 && !sounding && DG.tail && DG.blocks - DG.off_block < DG.tail;
        if (tail)                                       /* the last chord still rings: attack and glide from it */
            flags |= DG_CW_TAIL;
        dg_tail_log = dg_tail_log << 1 | tail;
        DG.last_tempo = T.tempo;
        DG.last_note = lo;
        DG.step_log[DG.trigs & 15] = (uint8_t)DG.last_step;
        dg_trig(&T, (int32_t)DG.last_step, &dg_cur, cw | flags);
        name_chord(lo, w & 0xFFF);
        redraw();
        DG.last_cw = cw;
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

void dg_tx(void)
{
    volatile uint8_t *f = FRAME;
    uint16_t on = rd16(f, 0x22), off = rd16(f, 0x24);
    uint16_t non = on, noff = off;
    int32_t out[DG_NV], v;
    uint32_t i, mask, gates, stock_on = 0, nnew = 0, playing, stop, newbits = 0;
    uint8_t newn[EV_MAX];

    DG.blocks++;
    shortcut_tick();

    /* a preset was loaded on the DigiGlide track (its name changed): the DSP voices were silenced, so the chord
     * DigiGlide holds is gone too. Forget it, or HOLD would keep gliding a silent chord. */
    if (DG.track >= 0 && !(DG.blocks & 31) && SOUNDS) {
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
                dg_name[0] = 0;
                redraw();
            }
            DG.snd_sig = h;
        }
    }

    /* every note-on of a synth track whose VCNT is on is DigiGlide's: it never reaches the DSP
     * (sequencer trigs, chord mode, held keys and MIDI in all arrive here as note-ons on the track's voices); its
     * note-off is swallowed with it. Every other note-on is stock's. */
    for (v = 0; v < 16; v++) {
        uint32_t bit = 1u << v, t;
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
        t = rd16(f, 0xa5a + 2 * v);
        if (dg_synth(t) && (DG.track < 0 || !(DG.active || DG.ctl) || (int32_t)t == DG.track)) {
            uint32_t step = PLAYHEAD[t], base = 0, nres;
            int locked, p_on = dg_vcnt_on(par_at(t, step, K_VCNT, &locked));
            nres = voice_range(t, &base);
            if (p_on) {
                DG.seen_on++;
                DG.dbg_base = base;
                DG.dbg_nres = nres;
                DG.dbg_v = (uint32_t)v;
            }
            if (p_on && nres >= 3) {
                if (!nnew) {                            /* the event's parameters: the first note's */
                    if (DG.ctl && (base != DG.base || nres != DG.nres)) {      /* VOICES changed under a chord */
                        noff |= (uint16_t)(DG.ctl & DG.was_on);
                        DG.ctl = DG.was_on = 0;
                        dg_gate_off(&T);
                    }
                    read_ui(t, step);
                    DG.track = (int32_t)t;
                    DG.last_step = step;
                    DG.base = base;
                    DG.nres = nres;
                }
                if (nnew < EV_MAX)
                    newn[nnew++] = (uint8_t)(rd16(f, 0x02 + 2 * v) >> 8);
                DG.src = v;
                DG.held |= bit;
                newbits |= bit;
                DG.swallowed++;
                non &= (uint16_t)~bit;
                continue;
            }
            DG.stock_trigs++;
            if (DG.active && (int32_t)t == DG.track) {  /* VCNT OFF on this trig: a stock note, the chord releases */
                chord_off();
                DG.active = 0;
            }
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

    if (nnew) {
        if (!DG.ev_open || DG.blocks - DG.ev_start > WIN_BLOCKS) {
            DG.ev_open = 1;
            DG.ev_start = DG.blocks;
            DG.ev_n = DG.ev_chordy = DG.ev_fired = 0;
            DG.ev_legato = (DG.held & ~newbits) != 0;   /* another key (or trig) of the track is still down */
            /* HOLD: the chord stays after the key or the trig ends, so a recording plays back as it sounded while
             * it was played. Only a key played by hand releases it by playing the same chord again: a sequenced
             * trig (the sequencer plays and the step has a trig) repeating a chord just plays it again. */
            DG.ev_latched = dg_ui[K_HOLD];
            /* sequenced or played by hand: the unit's own keys are the trig keys, and a hand-played note arrives
             * while one is down. (The first rule, "the playing step has a trig", failed on the unit: live-recorded
             * trigs are micro-timed and fire while the playhead still shows the step before.) */
            DG.ev_seq = playing && !(KEYS_HELD[3] | KEYS_HELD[4]);          /* TRIG 1..16 = codes 25..40 */
        }
        for (i = 0; i < nnew && DG.ev_n < EV_MAX; i++)
            DG.ev_notes[DG.ev_n++] = newn[i];
        /* three notes in one block: stock chord mode is on, and its voicing hides which key was pressed (the root
         * may be wrong): say so */
        if (nnew >= 3 && !DG.msg_until) {
            put(msg, "CHORD MODE ON?");
            DG.msg_until = DG.blocks + MSG_BLOCKS;
            redraw();
        }
        fire_event();
        DG.ctl &= ~stock_on;
    } else if (DG.active) {
        int locked;
        if (!dg_vcnt_on(par_at((uint32_t)DG.track, DG.last_step, K_VCNT, &locked))) {
            chord_off();                                /* switched OFF (knob or shortcut): release now */
            DG.active = 0;
        }
    }
    if (DG.active && DG.gate_open && !DG.latched && !DG.held && !nnew)
        chord_off();                                    /* every key / trig of the chord has ended: release */

    if (DG.ctl) {
        if (DG.active && !nnew) {
            int locked;
            uint32_t tr = (uint32_t)DG.track;
            int32_t sc = dg_knob(par_at(tr, DG.last_step, K_SCRB, &locked), K_SCRB);
            if (sc != T.p.scrb) {                       /* SCRB follows the knob (or this trig's lock) live */
                T.p.scrb = (uint8_t)sc;
                dg_set_scrb(&T, sc);
            }
            if ((DG.gate_open || DG.latched) && DG.blocks - DG.rev_block >= 30) {
                DG.rev_block = DG.blocks;               /* a chord setting was turned (TYPE EXT KEY VOIC POS BASS */
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
                    name_chord(DG.last_note, w & 0xFFF);
                    DG.sig = chord_sig();
                    redraw();
                }
            }
        }
        int32_t src_pan = (int32_t)rd16(f, 0xda + 146 * (uint32_t)DG.src + 128);   /* before any voice's own pan */
        mask = dg_block(&T, out);
        gates = 0;
        for (i = 0; i < DG_NV; i++) {
            uint32_t d = DG.base + i, bit = 1u << d;
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
            }
            /* the amp envelope never restarts from zero on a voice DigiGlide plays: an attack on a voice that
             * still sounds (a strike on a held chord, a new chord over the last one's release) rises from where
             * it is. On a silent voice it makes no difference. The sound's own AMP RSET is not used here. */
            wr16(f, RSET_OFF + 146 * d, 0);
            wr16(f, 0x02 + 2 * d, note_word(out[i]));
            if ((mask >> (8 + i)) & 1)
                gates |= bit;
            if ((gates & bit) && (!(DG.was_on & bit) || DG.reattack))
                non |= (uint16_t)bit;
            if (!(gates & bit) && (DG.was_on & bit))
                noff |= (uint16_t)bit;
        }
        DG.was_on = gates;
        DG.reattack = 0;
        for (i = DG.nres; i < DG_NV; i++)               /* core voices past the reserved block: silent */
            T.v[i].on = 0;
    }
    if (non != on || noff != off) {
        wr16(f, 0x22, non); wr16(f, 0x26, non);
        wr16(f, 0x24, noff); wr16(f, 0x28, noff);
    }
}

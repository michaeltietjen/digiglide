/* DigiGlide core: the M1 model (model/digiglide.py) in 32-bit fixed point, for the ColdFire (no FPU, and no libgcc
 * 64-bit helpers: the toolchain's libgcc is built for the 68020) and for the host test.
 *
 * Units: pitch in cents Q16 (MIDI note * 100 * 65536); time in audio blocks (1500 per second); a glide's duration
 * and delay are Q16 when the whole glide fits 65536 blocks (all fast glides) and Q12 otherwise (tsh); shapes and progress in Q29; random from the same xorshift32 streams as the model.
 * The tempo arrives as the Digitone's tempo word (BPM * 120).
 */
#ifndef DG_CORE_H
#define DG_CORE_H
#include <stdint.h>

#define DG_NV 6
#define DG_MAXPATH 12               /* start + up to 10 vias + target */

typedef struct {                    /* the 16 parameters, as stored knob indices (same order as Params.FIELDS) */
    uint8_t key, scl, voic, pos, vcnt, bass, sprd, move;   /* key / scl: the scale for Scale steps and EVOL */
    uint8_t glid, path, time, ordr, stag, drft, vib, scrb;
    uint8_t tune, fan;                  /* build 29: TUNE 0 Equal, 1 Pure; FAN 0..127 */
} dg_params;

typedef struct {
    uint8_t started, on, shape, npath;  /* npath = 0: no glide in progress */
    int32_t note;                       /* target MIDI note */
    int32_t tgt, cur;                   /* Q16 cents */
    int32_t path[DG_MAXPATH];
    uint32_t t0;                        /* block the glide was planned in */
    uint32_t delay, dur;                /* blocks << tsh */
    uint32_t tsh;                       /* 16 or 12 */
    uint32_t rcp;                       /* progress = (el * rcp) >> rsh, Q29 */
    uint32_t rsh;
    uint32_t glide;                     /* blocks << tsh, last glide time sent */
    int32_t dr, dr_t;                   /* drift, Q24 cents */
    int32_t dr_n;                       /* blocks to the next drift target */
    uint32_t ph, inc;                   /* vibrato phase and step, cycles Q32 */
    uint32_t rng;                       /* drift random stream (0 = not drawn yet) */
    int32_t vib, drift;                 /* cents */
    int32_t pan;                        /* Q15, -32768..32767 */
    int32_t level;                      /* Q15 */
} dg_voice;

typedef struct {
    dg_voice v[DG_NV];
    dg_params p;
    uint32_t tempo;                     /* BPM * 120 */
    uint32_t pattern;
    uint32_t b;                         /* current block */
    int32_t key;                        /* the scale's key (Scale steps, EVOL) */
    int32_t aroot, avoic, apos;         /* what the voices' places are built on: the root, VOIC and POS */
    int32_t step;
    int32_t scrb, scrb_t;               /* Q30 */
    int32_t nfan;                       /* build 29: the chord voices FAN spreads (the layout's n) */
} dg_track;

void dg_init(dg_track *t, uint32_t tempo_word, uint32_t pattern);
#define DG_CAND_LO 12                   /* the notes the voice leader may use */
#define DG_CAND_HI 108
#define DG_ROOT_LO 24                   /* the roots it accepts (clamped) */
#define DG_ROOT_HI 96
#define DG_LEASH16 (700 * 65536)        /* a voice's reference is at most a fifth from its VOIC place */
/* a chord event: cw = pitch classes (bits 0..11) | root MIDI note << 12 | flags */
#define DG_CW(root, pcs) ((uint32_t)(pcs) | (uint32_t)(root) << 12)
#define DG_CW_TAIL (1u << 24)           /* the released chord still rings: its voices count as sounding */
#define DG_CW_REVOICE (1u << 25)        /* VOIC was turned: lead every voice from its VOIC place */
void dg_trig(dg_track *t, int32_t step, const dg_params *p, uint32_t cw);
uint32_t dg_chord_for(int32_t root, int32_t typ, int32_t ext, int32_t key, uint32_t locks);
void dg_gate_off(dg_track *t);
/* build 29: voice i's offset from equal temperament when it plays `note`, Q16 cents (TUNE Pure and FAN) */
int32_t dg_tune_off(const dg_track *t, int i, int32_t note);
void dg_set_scrb(dg_track *t, int32_t value);
/* advance one block; out_c16[v] = pitch (Q16 cents) of every started voice; returns a mask: bit v = started,
 * bit 8 + v = gate on */
uint32_t dg_block(dg_track *t, int32_t out_c16[DG_NV]);

#endif

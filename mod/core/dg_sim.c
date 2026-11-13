/* Host harness for the M2 equivalence test (not in the firmware): run a whole progression through the core.
 * ev: n_ev records of 20 int32 {block, kind (0 trig, 1 off, 2 scrb), step, note or scrb value, 16 params}.
 * Outputs per block and voice: pitch (Q16 cents), mask (dg_block's), note; and, if gliding is not NULL, per block a
 * mask of the voices whose glide has not landed yet (test_glid_fit.py). */
#include "dg_core.h"

int dg_sim2(const int32_t *ev, int32_t n_ev, int32_t n_blocks, uint32_t tempo_word, uint32_t pattern,
            int32_t *pitch, uint32_t *mask, int32_t *notes, uint32_t *gliding);

int dg_sim(const int32_t *ev, int32_t n_ev, int32_t n_blocks, uint32_t tempo_word, uint32_t pattern,
           int32_t *pitch, uint32_t *mask, int32_t *notes)
{
    return dg_sim2(ev, n_ev, n_blocks, tempo_word, pattern, pitch, mask, notes, 0);
}

int dg_sim2(const int32_t *ev, int32_t n_ev, int32_t n_blocks, uint32_t tempo_word, uint32_t pattern,
            int32_t *pitch, uint32_t *mask, int32_t *notes, uint32_t *gliding)
{
    dg_track t;
    int32_t b, e = 0, i;
    dg_init(&t, tempo_word, pattern);
    for (b = 0; b < n_blocks; b++) {
        while (e < n_ev && ev[20 * e] == b) {
            const int32_t *r = ev + 20 * e;
            if (r[1] == 0) {
                dg_params p;
                p.key = r[4]; p.scl = r[5]; p.voic = r[6]; p.pos = r[7]; p.vcnt = r[8]; p.bass = r[9];
                p.sprd = r[10]; p.move = r[11]; p.glid = r[12]; p.path = r[13]; p.time = r[14]; p.ordr = r[15];
                p.stag = r[16]; p.drft = r[17]; p.vib = r[18]; p.scrb = r[19];
                dg_trig(&t, r[2], &p, (uint32_t)r[3]);
            } else if (r[1] == 1) {
                dg_gate_off(&t);
            } else {
                dg_set_scrb(&t, r[3]);
            }
            e++;
        }
        mask[b] = dg_block(&t, pitch + DG_NV * b);
        for (i = 0; i < DG_NV; i++)
            notes[DG_NV * b + i] = t.v[i].note;
        if (gliding) {
            gliding[b] = 0;
            for (i = 0; i < DG_NV; i++)
                if (t.v[i].npath)
                    gliding[b] |= 1u << i;
        }
    }
    return (int)sizeof(dg_track);
}

/* M2 self-test (test image only, not in the firmware mod): replays progressions from selftest_events.h through the
 * core and hashes every block's output, so the ColdFire build can be compared with the host build. */
#include "dg_core.h"
#include "selftest_events.h"

dg_track st_track;
int32_t st_b, st_e, st_c;
uint32_t st_hash;

void dg_selftest_init(void)
{
}

uint32_t dg_selftest_start(int32_t c)
{
    st_c = c;
    st_b = 0;
    st_e = ST_CASES[c][2];
    st_hash = 2166136261u;
    dg_init(&st_track, (uint32_t)ST_CASES[c][0], (uint32_t)ST_CASES[c][1]);
    return 0;
}

/* run up to n more blocks of case st_c; returns the running hash (FNV-1a over 32-bit words) */
uint32_t dg_selftest_run(int32_t n)
{
    int32_t out[DG_NV], i, end = ST_CASES[st_c][2] + ST_CASES[st_c][3], nb = ST_CASES[st_c][4];
    while (n-- > 0 && st_b < nb) {
        uint32_t m;
        while (st_e < end && ST_EV[st_e][0] == st_b) {
            const int32_t *r = ST_EV[st_e];
            if (r[1] == 0) {
                dg_params p;
                p.key = r[4]; p.scl = r[5]; p.voic = r[6]; p.pos = r[7]; p.vcnt = r[8]; p.bass = r[9];
                p.sprd = r[10]; p.move = r[11]; p.glid = r[12]; p.path = r[13]; p.time = r[14]; p.ordr = r[15];
                p.stag = r[16]; p.drft = r[17]; p.vib = r[18]; p.scrb = r[19];
                dg_trig(&st_track, r[2], &p, (uint32_t)r[3]);
            } else if (r[1] == 1) {
                dg_gate_off(&st_track);
            } else {
                dg_set_scrb(&st_track, r[3]);
            }
            st_e++;
        }
        m = dg_block(&st_track, out);
        for (i = 0; i < DG_NV; i++)
            st_hash = (st_hash ^ (uint32_t)out[i]) * 16777619u;
        st_hash = (st_hash ^ m) * 16777619u;
        st_b++;
    }
    return st_hash;
}

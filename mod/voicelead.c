/* GLIDE voice leading, slides, curves and drift. Pure C: no firmware addresses except the tempo word read in
 * glide_tempo() (host tests define GLIDE_HOST and supply their own). */
#include "glide.h"

const struct glide_params glide_defaults = {
    0,              /* track 1 */
    0,              /* not bypassed */
    48,             /* ROOT C3 */
    CHRD_MAJ,
    VOIC_CLOSE,
    GLID_4,         /* 1/4 note */
    CURV_EASE_OUT,
    20,             /* DRFT */
};

/* Chord tones in semitones above the root; 0xff ends. maj9 keeps 4 voices: root, 3rd, 7th, 9th (no 5th). */
static const u8 chord_tab[CHRD_N][GLIDE_NV] = {
    {0, 4, 7, 0xff},    /* maj */
    {0, 3, 7, 0xff},    /* min */
    {0, 2, 7, 0xff},    /* sus2 */
    {0, 5, 7, 0xff},    /* sus4 */
    {0, 4, 7, 10},      /* 7 */
    {0, 4, 7, 11},      /* maj7 */
    {0, 3, 7, 10},      /* m7 */
    {0, 4, 7, 14},      /* add9 */
    {0, 4, 11, 14},     /* maj9 */
    {0, 7, 12, 0xff},   /* 5th + oct */
    {0, 5, 10, 15},     /* quartal */
};

/* Sequencer units: a 96 ppqn subtick = 225,000, a quarter = 21,600,000 (references/coldfire.md "Clock"). */
#define QUARTER 21600000UL
static const u32 glid_units[GLID_N] = {
    0, QUARTER / 8, QUARTER / 4, QUARTER / 2, QUARTER, 2 * QUARTER,
    4 * QUARTER, 8 * QUARTER, 16 * QUARTER, 32 * QUARTER,
};

u32 glide_units(u32 glid)
{
    return glid < GLID_N ? glid_units[glid] : glid_units[GLID_4];
}

#ifndef GLIDE_HOST
u32 glide_tempo(void)
{
    return *(volatile u32 *)0x402a0dec * 2;     /* BPM x 120 = half-units per block; "now" advances 2x that */
}
#endif

static void sort(s32 *a, u32 n)
{
    u32 i, j;
    for (i = 1; i < n; i++)
        for (j = i; j > 0 && a[j - 1] > a[j]; j--) {
            s32 t = a[j]; a[j] = a[j - 1]; a[j - 1] = t;
        }
}

u32 glide_chord(const struct glide_params *p, s32 trig_note, s32 *out)
{
    u32 n = 0, i;
    s32 root = (s32)p->root + (trig_note - 60);
    const u8 *iv = chord_tab[p->chrd < CHRD_N ? p->chrd : 0];
    s32 t[GLIDE_NV];
    for (i = 0; i < GLIDE_NV && iv[i] != 0xff; i++)
        t[n++] = root + iv[i];
    switch (p->voic) {
    case VOIC_SPREAD:                       /* second tone up an octave: open triad (C G E') */
        if (n >= 2) t[1] += 12;
        break;
    case VOIC_DROP2:                        /* second-highest tone down an octave */
        if (n >= 3) t[n - 2] -= 12;
        break;
    case VOIC_OPEN:                         /* root down an octave under the rest */
        if (n >= 2) t[0] -= 12;
        break;
    default:
        break;
    }
    for (i = 0; i < n; i++) {               /* keep every tone playable */
        while (t[i] < 0) t[i] += 12;
        while (t[i] > 127) t[i] -= 12;
    }
    sort(t, n);
    for (i = 0; i < n; i++)
        out[i] = t[i] * SEMI;
    return n;
}

/* The tone's octave nearest to pitch `from` (spec: octave shifts within the current pitch +-12). */
static s32 nearest_octave(s32 tone, s32 from)
{
    while (tone - from > 6 * SEMI && tone - 12 * SEMI >= 0) tone -= 12 * SEMI;
    while (from - tone > 6 * SEMI && tone + 12 * SEMI <= 127 * SEMI) tone += 12 * SEMI;
    return tone;
}

static s32 iabs(s32 x) { return x < 0 ? -x : x; }

/* All permutations of 4 indices (24), generated once. */
static const u8 perms[24][4] = {
    {0,1,2,3},{0,1,3,2},{0,2,1,3},{0,2,3,1},{0,3,1,2},{0,3,2,1},
    {1,0,2,3},{1,0,3,2},{1,2,0,3},{1,2,3,0},{1,3,0,2},{1,3,2,0},
    {2,0,1,3},{2,0,3,1},{2,1,0,3},{2,1,3,0},{2,3,0,1},{2,3,1,0},
    {3,0,1,2},{3,0,2,1},{3,1,0,2},{3,1,2,0},{3,2,0,1},{3,2,1,0},
};

#define PEN_CROSS (3 * SEMI)        /* per pair of voices that swap order */
#define PEN_UNISON (4 * SEMI)       /* per pair of voices landing on the same pitch */

static u32 rnd(u32 *s)              /* xorshift32: repeatable per seed */
{
    u32 x = *s;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    *s = x;
    return x;
}

static void drift(struct glide_state *g, u32 i)
{
    u32 d = g->param.drft > 127 ? 127 : g->param.drft;
    u32 r1 = rnd(&g->seed), r2 = rnd(&g->seed);
    /* detune: 0..+-15 cents at DRFT 127 = +-38 units of 1/256 semitone */
    s32 span = (s32)(38 * d / 127);
    g->v[i].detune = span ? (s32)(r1 % (u32)(2 * span + 1)) - span : 0;
    /* start delay: 0..1/32 note at DRFT 127 */
    g->v[i].delay = d ? (u32)((r2 % 1024) * ((QUARTER / 8) / 1024) * d / 127) : 0;
}

void glide_assign(struct glide_state *g, s32 src)
{
    u32 n = g->n, i, k, best = 0, nold = 0, m;
    s32 best_cost = 0x7fffffff;
    s32 old[GLIDE_NV];
    u8 oldidx[GLIDE_NV];
    u32 glid = glide_units(g->param.glid);
    (void)src;

    g->trigs++;
    g->seed = 0x9e3779b9u;                          /* repeatable per musical event: seeded from the chord + voices */
    for (i = 0; i < n; i++)
        g->seed = (g->seed ^ (u32)g->target[i]) * 0x01000193u;

    for (i = 0; i < GLIDE_NV; i++)
        if (g->v[i].on && g->active == 1) {
            oldidx[nold] = (u8)i;
            old[nold++] = g->v[i].cur;
            g->seed = (g->seed ^ (u32)g->v[i].cur) * 0x01000193u;
        }

    g->elapsed = 0;
    g->total = glid;

    if (nold == 0 || glid == 0) {                   /* first trig, after release, or GLID 0: attack fresh */
        for (i = 0; i < GLIDE_NV; i++) {
            g->v[i].release_at_end = 0;
            if (i < n) {
                g->v[i].cur = g->v[i].from = g->v[i].to = g->target[i];
                g->v[i].on = 1;
                g->v[i].start = 1;
                g->v[i].detune = 0;
                g->v[i].delay = 0;
            } else {
                g->v[i].start = 0;                   /* glide_tx releases voices still on */
            }
        }
        g->last_cost = 0;
        return;
    }

    /* Slots 0..m-1: slot j < nold is an existing voice, j >= nold a new voice; tone j < n a chord tone, j >= n a surplus
     * slot (the voice glides to its nearest kept tone and releases). Brute force over every pairing: m <= 4, 24 perms. */
    m = n > nold ? n : nold;
    for (k = 0; k < 24; k++) {
        const u8 *p = perms[k];
        s32 cost = 0, pitch[GLIDE_NV];
        u32 a, b, ok = 1;
        for (a = 0; a < m; a++)
            if (p[a] >= m) { ok = 0; break; }
        if (!ok)
            continue;
        if (m < 4) {                                /* only count each permutation of m once */
            for (a = m; a < 4; a++)
                if (p[a] != a) { ok = 0; break; }
            if (!ok)
                continue;
        }
        for (a = 0; a < nold; a++) {                /* existing voices: movement */
            s32 to;
            if (p[a] < n) {
                to = nearest_octave(g->target[p[a]], old[a]);
            } else {                                /* surplus: nearest kept tone */
                u32 t; s32 bd = 0x7fffffff;
                to = old[a];
                for (t = 0; t < n; t++) {
                    s32 c = nearest_octave(g->target[t], old[a]);
                    if (iabs(c - old[a]) < bd) { bd = iabs(c - old[a]); to = c; }
                }
            }
            pitch[a] = to;
            cost += iabs(to - old[a]);
        }
        for (a = nold; a < m; a++)                  /* new voices attack on their tone in the chord's own voicing */
            pitch[a] = p[a] < n ? g->target[p[a]] : 0;
        for (a = 0; a < nold; a++)
            for (b = a + 1; b < nold; b++) {
                if ((old[a] < old[b]) != (pitch[a] < pitch[b]) && old[a] != old[b])
                    cost += PEN_CROSS;
                if (pitch[a] == pitch[b] && p[a] < n && p[b] < n)
                    cost += PEN_UNISON;
            }
        if (cost < best_cost) {
            best_cost = cost;
            best = k;
        }
    }
    g->last_cost = best_cost;

    {
        const u8 *p = perms[best];
        u32 a, used = 0;
        u8 newslot[GLIDE_NV];
        u32 nnew = 0;
        for (a = 0; a < GLIDE_NV; a++)
            g->v[a].start = 0;
        for (a = 0; a < nold; a++) {
            struct glide_voice *v = &g->v[oldidx[a]];
            used |= 1u << oldidx[a];
            v->from = v->cur;
            if (p[a] < n) {
                v->to = nearest_octave(g->target[p[a]], v->cur);
                v->release_at_end = 0;
            } else {
                u32 t; s32 bd = 0x7fffffff;
                v->to = v->cur;
                for (t = 0; t < n; t++) {
                    s32 c = nearest_octave(g->target[t], v->cur);
                    if (iabs(c - v->cur) < bd) { bd = iabs(c - v->cur); v->to = c; }
                }
                v->release_at_end = 1;
            }
            drift(g, oldidx[a]);
        }
        for (a = nold; a < m; a++)                  /* tones left over go to free voices, attacking fresh */
            if (p[a] < n)
                newslot[nnew++] = p[a];
        for (a = 0; a < GLIDE_NV && nnew; a++)
            if (!(used >> a & 1)) {
                struct glide_voice *v = &g->v[a];
                u8 t = newslot[--nnew];
                v->cur = v->from = v->to = g->target[t];
                v->on = 1;
                v->start = 1;
                v->release_at_end = 0;
                v->detune = 0;
                v->delay = 0;
                used |= 1u << a;
            }
    }
}

/* Curve shape on t in [0, 65536]. */
static u32 curve(u32 c, u32 t)
{
    u32 u;
    switch (c) {
    case CURV_LINEAR:
        return t;
    case CURV_EASE_IN_OUT:                  /* smoothstep 3t^2 - 2t^3 */
        u = (t * (t >> 4)) >> 12;           /* t^2 / 65536 */
        return (3 * u) - ((2 * ((u * (t >> 4)) >> 12)));
    default:                                /* ease-out: 1 - (1 - t)^2 */
        u = 65536 - t;
        return 65536 - ((u * (u >> 4)) >> 12);
    }
}

void glide_tick(struct glide_state *g)
{
    u32 i;
    if (g->total == 0)
        return;
    if (g->elapsed < g->total + QUARTER / 8)
        g->elapsed += glide_tempo();
    for (i = 0; i < GLIDE_NV; i++) {
        struct glide_voice *v = &g->v[i];
        u32 e, t;
        if (v->from == v->to && !v->release_at_end) {
            v->cur = v->to;
            continue;
        }
        e = g->elapsed > v->delay ? g->elapsed - v->delay : 0;
        if (e >= g->total) {
            v->cur = v->to;
            v->from = v->to;
            if (v->release_at_end) {
                v->on = 0;                  /* glide_tx sends the note-off */
                v->release_at_end = 0;
            }
            continue;
        }
        t = e / ((g->total >> 16) ? (g->total >> 16) : 1);      /* Q16 progress; total >= 2.7M units, no overflow */
        if (t > 65536) t = 65536;
        t = curve(g->param.curv, t);
        v->cur = v->from + (s32)(((s32)(v->to - v->from) * (s32)(t >> 4)) >> 12);
    }
}

u16 glide_word(const struct glide_state *g, u32 i)
{
    const struct glide_voice *v = &g->v[i];
    s32 w = v->cur;
    if (v->from != v->to || g->elapsed < g->total)  /* drift detune only while moving */
        w += v->detune;
    if (w < 0) w = 0;
    if (w > 127 * SEMI) w = 127 * SEMI;
    return (u16)w;
}

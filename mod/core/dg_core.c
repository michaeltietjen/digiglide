/* DigiGlide core: model/digiglide.py in 32-bit fixed point. Every function names the model function it ports.
 * Rules for the ColdFire build: no float, no 64-bit types (libgcc's helpers are 68020 code), no zero-initialised
 * locals (memset), no 8-byte array strides. */
#include "dg_core.h"
#include "dg_tables.h"

#define C16 6553600                 /* one semitone in Q16 cents */
#define ONE29 (1 << 29)
#define ONE30 (1 << 30)
#define TIE16 66                    /* TIE = 1e-5 semitone, in Q16 cents */
#define JUMP_BLOCKS 30u              /* path_at: dur <= 0.02 s is a jump */
#define SUB_FRESH (750u << 12)      /* amb_play: the sub follows a fresh layout in 0.5 s (a jump: Q12 is fine) */
#define K_SCRB 46676911             /* 1 - exp(-4 * DT / 0.06), Q30 */
#define K045 241591910              /* 0.45, Q29 */
#define K009 48318382               /* 0.09 */
#define K065 348966093              /* 0.65 */
#define K1_035 1533916891           /* 1 / 0.35 */

enum { R_LOOSE = 1, R_SCATTER, R_EVOL, R_ORDER, R_DRIFT };
enum { MV_NONE, MV_BLOOM, MV_CASC_UP, MV_CASC_DOWN, MV_SPIRAL, MV_SWOOP, MV_SCATTER, MV_CONVERGE, MV_FALL, MV_EVOL };

static const uint8_t SCALES[4][7] = {{0, 2, 4, 5, 7, 9, 11}, {0, 2, 3, 5, 7, 8, 10}, {0, 2, 3, 5, 7, 9, 10},
                                     {0, 2, 4, 5, 7, 9, 10}};
static const uint8_t GLID16[10] = {0, 1, 2, 4, 8, 16, 32, 64, 128, 0};   /* sixteenths (index 9 = 256, below) */
static const uint8_t STAG2[7] = {0, 1, 2, 4, 6, 10, 16};                 /* STAGGERS in half sixteenths */
static const int16_t BASE_PAN[DG_NV] = {0, -13107, 13107, -6554, 6554, 0};
static const int16_t LEVEL[DG_NV] = {22938, 19661, 19661, 19661, 19661, 19661};
static const uint32_t INC[DG_NV] = {429497, 572662, 715828, 858993, 1002159, 1145325};    /* 0.15 + 0.05 k Hz */
static const uint32_t PH0[DG_NV] = {0, 1162060968u, 2324121937u, 3486182905u, 353276578, 1515337546};

/* ------------------------------------------------------------------ 32-bit helpers for 64-bit products */
typedef struct { uint32_t hi, lo; } u64p;

static u64p umul(uint32_t a, uint32_t b)
{
    uint32_t al = a & 0xFFFF, ah = a >> 16, bl = b & 0xFFFF, bh = b >> 16;
    uint32_t ll = al * bl, lh = al * bh, hl = ah * bl, hh = ah * bh;
    uint32_t mid = lh + (ll >> 16);
    uint32_t mid2 = (mid & 0xFFFF) + hl;
    u64p r;
    r.lo = (mid2 << 16) | (ll & 0xFFFF);
    r.hi = hh + (mid >> 16) + (mid2 >> 16);
    return r;
}

static uint32_t ushr(u64p x, uint32_t s)            /* low 32 bits of x >> s, s < 64 */
{
    if (s == 0)
        return x.lo;
    if (s < 32)
        return (x.lo >> s) | (x.hi << (32 - s));
    return x.hi >> (s - 32);
}

static int32_t mulsh(int32_t a, int32_t b, uint32_t s)   /* (a * b) >> s, truncated toward zero */
{
    uint32_t ua = a < 0 ? 0u - (uint32_t)a : (uint32_t)a;
    uint32_t ub = b < 0 ? 0u - (uint32_t)b : (uint32_t)b;
    uint32_t r = ushr(umul(ua, ub), s);
    return ((a < 0) != (b < 0)) ? -(int32_t)r : (int32_t)r;
}

static uint32_t nlz(uint32_t x)                     /* leading zeros (no __builtin_clz: libgcc is 68020 code) */
{
    uint32_t n = 0;
    if (x <= 0x0000FFFF) { n += 16; x <<= 16; }
    if (x <= 0x00FFFFFF) { n += 8; x <<= 8; }
    if (x <= 0x0FFFFFFF) { n += 4; x <<= 4; }
    if (x <= 0x3FFFFFFF) { n += 2; x <<= 2; }
    if (x <= 0x7FFFFFFF) { n += 1; }
    return n;
}

/* n / d for a 64-bit n whose quotient fits 32 bits (Hacker's Delight divlu: 16-bit digits, the CPU's 32/32 divide) */
static uint32_t udiv64(u64p n, uint32_t d)
{
    uint32_t u1 = n.hi, u0 = n.lo, s, vn1, vn0, un32, un21, un10, un1, un0, q1, q0, rhat;
    if (!u1)
        return u0 / d;
    if (u1 >= d)
        return 0xFFFFFFFFu;                         /* would overflow: never asked for */
    s = nlz(d);
    d <<= s;
    vn1 = d >> 16;
    vn0 = d & 0xFFFF;
    un32 = (u1 << s) | (s ? u0 >> (32 - s) : 0);
    un10 = u0 << s;
    un1 = un10 >> 16;
    un0 = un10 & 0xFFFF;
    q1 = un32 / vn1;
    rhat = un32 - q1 * vn1;
    while (q1 >= 65536 || q1 * vn0 > ((rhat << 16) | un1)) {
        q1--;
        rhat += vn1;
        if (rhat >= 65536)
            break;
    }
    un21 = (un32 << 16) + un1 - q1 * d;
    q0 = un21 / vn1;
    rhat = un21 - q0 * vn1;
    while (q0 >= 65536 || q0 * vn0 > ((rhat << 16) | un0)) {
        q0--;
        rhat += vn1;
        if (rhat >= 65536)
            break;
    }
    return (q1 << 16) + q0;
}

static uint32_t muldiv(uint32_t a, uint32_t b, uint32_t d)
{
    return udiv64(umul(a, b), d);
}

static uint32_t muldiv_r(uint32_t a, uint32_t b, uint32_t d)   /* a * b / d, rounded to nearest */
{
    u64p x = umul(a, b);
    uint32_t lo = x.lo + (d >> 1);
    if (lo < x.lo)
        x.hi++;
    x.lo = lo;
    return udiv64(x, d);
}

static int32_t floordiv(int32_t n, int32_t d)
{
    int32_t q = n / d;
    if ((n % d) != 0 && ((n < 0) != (d < 0)))
        q--;
    return q;
}

static int32_t imod12(int32_t x)
{
    x %= 12;
    return x < 0 ? x + 12 : x;
}

static uint32_t popcount12(uint32_t m)
{
    uint32_t c = 0;
    while (m) {
        c += m & 1;
        m >>= 1;
    }
    return c;
}

/* ------------------------------------------------------------------ seeded random (Rng) */
static uint32_t fmix32(uint32_t h)
{
    h ^= h >> 16;
    h *= 0x85EBCA6Bu;
    h ^= h >> 13;
    h *= 0xC2B2AE35u;
    h ^= h >> 16;
    return h;
}

static uint32_t rng_seed(const dg_track *t, uint32_t voice, uint32_t purpose)
{
    uint32_t h = fmix32(t->pattern * 0x9E3779B1u + 0x7F4A7C15u);
    h = fmix32(h ^ ((uint32_t)t->step * 0x85EBCA77u + 0x165667B1u));
    h = fmix32(h ^ (voice * 0xC2B2AE3Du + 0x27D4EB2Fu));
    h = fmix32(h ^ (purpose * 0x2545F491u + 0x61C88647u));
    return h ? h : 0x6D2B79F5u;
}

static uint32_t r24(uint32_t *x)
{
    uint32_t v = *x;
    v ^= v << 13;
    v ^= v >> 17;
    v ^= v << 5;
    *x = v;
    return v >> 8;
}

static uint32_t below(uint32_t *x, uint32_t n)
{
    return (r24(x) * n) >> 24;
}

/* ------------------------------------------------------------------ chords (rev 5: the model's chord_for) */
static const uint8_t TRIAD[4][3] = {{0, 4, 7}, {0, 3, 7}, {0, 5, 7}, {0, 3, 6}};      /* MAJ MIN SUS DIM */
static const uint8_t EXT_PART[8] = {0, 1, 2, 4, 8, 1 | 8, 2 | 8, 4 | 8};             /* bit 0: 6, 1: 7, 2: MAJ7, 3: 9 */

/* The chord one key plays. root: MIDI note; typ 0..3; ext 0..7; key: 0 = OFF, 1..12 C..B major, 13..24 C..B minor;
 * locks: bit 0 = TYPE p-locked on the step, bit 1 = EXT p-locked. -> pitch classes | scale key << 12 | scale << 16.
 * KEY set and the root in its scale: the scale's own triad and 6 / 7 / 9 (MAJ7 = the key's seventh too); otherwise, or
 * for a locked TYPE / EXT: TYPE's triad and EXT's literal intervals. */
uint32_t dg_chord_for(int32_t root, int32_t typ, int32_t ext, int32_t key, uint32_t locks)
{
    static const uint8_t SEMI[4] = {9, 10, 11, 14}, DEG[4] = {5, 6, 6, 8};
    int32_t r = imod12(root), tonic, minor, d = -1, k;
    uint32_t pcs = 0;
    const uint8_t *sc;
    if (key) {
        tonic = (key - 1) % 12;
        minor = (key - 1) / 12;
    } else {
        tonic = r;
        minor = typ == 1 || typ == 3;
    }
    sc = SCALES[minor];
    if (key)
        for (k = 0; k < 7; k++)
            if (sc[k] == imod12(r - tonic))
                d = k;
    if (d >= 0 && !(locks & 1)) {
        for (k = 0; k <= 4; k += 2)
            pcs |= 1u << imod12(tonic + sc[(d + k) % 7]);
    } else {
        for (k = 0; k < 3; k++)
            pcs |= 1u << imod12(r + TRIAD[typ][k]);
    }
    for (k = 0; k < 4; k++) {
        if (!((EXT_PART[ext] >> k) & 1))
            continue;
        if (d >= 0 && !(locks & 2))
            pcs |= 1u << imod12(tonic + sc[(d + DEG[k]) % 7]);
        else
            pcs |= 1u << imod12(r + SEMI[k]);
    }
    return pcs | (uint32_t)tonic << 12 | (uint32_t)minor << 16;
}

static const uint16_t SCALE_MASK[4] = {0xAB5, 0x5AD, 0x6AD, 0x6B5};   /* bit pc set if in the scale (from C) */

static int in_scale(const dg_track *t, int32_t n)
{
    return (SCALE_MASK[t->p.scl] >> imod12(n - t->key)) & 1;
}

static int32_t qkey(int32_t c16)
{
    return (c16 + 32) >> 6;
}

/* voices 0..n-1 sorted by (cur to the nearest cent, voice): stable insertion sort. (ORDR's order. Whole cents, so
 * that voices in unison, as when SCRB holds a Converge on its meeting point, tie here as they do in the model.) */
#define CKEY(c) (((c) + 32768) >> 16)
static void sort_by_cur(const dg_track *t, const int8_t *in, int n, int8_t *out)
{
    int a, b;
    for (a = 0; a < n; a++) {
        int8_t v = in[a];
        int32_t k = CKEY(t->v[(int)v].cur);
        b = a;
        while (b > 0 && CKEY(t->v[(int)out[b - 1]].cur) > k) {
            out[b] = out[b - 1];
            b--;
        }
        out[b] = v;
    }
}

/* voices 0..n-1 sorted by (qkey(ref), voice): the voice leader's order (ref = cur moved by the octave change) */
static void sort_by_ref(const int32_t *ref, int n, int8_t *out)
{
    int a, b;
    for (a = 0; a < n; a++) {
        int32_t k = qkey(ref[a]);
        b = a;
        while (b > 0 && qkey(ref[(int)out[b - 1]]) > k) {
            out[b] = out[b - 1];
            b--;
        }
        out[b] = (int8_t)a;
    }
}

/* voicelead: voices 0..n-1 -> (mv_v, mv_n) in the model's dict order (by reference pitch); bass_note: the note the
 * lowest voice takes (the root as played), or -1 */
static int voicelead(const int32_t *ref, int n, uint32_t pcs, int32_t bass_note, int8_t *mv_v, int32_t *mv_n)
{
    int32_t prev = 0, k, j, cand_hi = 0;
    uint32_t used = 0, nused = 0, npcs = popcount12(pcs);
    sort_by_ref(ref, n, mv_v);
    for (j = DG_CAND_HI; j >= DG_CAND_LO; j--)
        if (pcs & (1u << imod12(j))) {
            cand_hi = j;
            break;
        }
    k = 0;
    if (bass_note >= 0 && n > 1) {
        mv_n[0] = bass_note;
        used = 1u << imod12(bass_note);
        nused = 1;
        prev = mv_n[0];
        k = 1;
    }
    for (; k < n; k++) {
        int32_t c = ref[(int)mv_v[k]], best = -1, bc = 0;
        int32_t pc;
        j = prev + 1 > DG_CAND_LO ? prev + 1 : DG_CAND_LO;
        pc = imod12(j);
        for (; j <= DG_CAND_HI; j++, pc = pc == 11 ? 0 : pc + 1) {
            int32_t cost, d;
            if (!(pcs & (1u << pc)))
                continue;
            d = j * C16 - c;
            if (best >= 0 && d > bc)                    /* every later candidate costs more: done */
                break;
            cost = (d < 0 ? -d : d) + (((used >> pc) & 1) && nused < npcs ? 250 * 65536 : 0);
            if (best < 0 || cost < bc - TIE16) {
                best = j;
                bc = cost;
            }
        }
        if (best < 0)
            best = cand_hi;
        mv_n[k] = best;
        if (!((used >> imod12(best)) & 1))
            nused++;
        used |= 1u << imod12(best);
        prev = best;
    }
    return n;
}

/* ------------------------------------------------------------------ shapes (shape_at, path_at) */
static int32_t sin_cyc(uint32_t ph)                 /* sin(2 pi ph / 2^32), Q29 */
{
    uint32_t i = ph >> 21;
    int32_t a = DG_SIN[i], b = DG_SIN[i + 1];
    return a + mulsh(b - a, (int32_t)(ph & 0x1FFFFF), 21);
}

static int32_t mul29(int32_t a, int32_t b)
{
    return mulsh(a, b, 29);
}

static int32_t ease(int32_t p)
{
    return mul29(mul29(p, p), 3 * ONE29 - 2 * p);
}

static int32_t shape_at(int32_t p, int shape)
{
    if (p < 0)
        p = 0;
    if (p > ONE29)
        p = ONE29;
    switch (shape) {
    case 1:
    case 8:
        return p;
    case 2:
        return ease(p);
    case 3:
        return ease(p) + mul29(mul29(K045, sin_cyc((uint32_t)p << 2)), p);
    case 4: {
        int32_t u = ONE29 - p, u2 = mul29(u, u);
        return ONE29 - mul29(mul29(u2, u2), sin_cyc((uint32_t)p * 12u + 0x40000000u));
    }
    case 5: {
        int32_t q = p <= K065 ? 0 : mul29(p - K065, K1_035);
        return ease(q > ONE29 ? ONE29 : q);
    }
    case 6:
        return ease(p >= ONE29 / 4 ? ONE29 : p * 4);
    case 7:
        return ease(p) + mul29(mul29(K009, sin_cyc((uint32_t)p * 24u)), sin_cyc((uint32_t)p << 2));
    default: {
        uint32_t i = (uint32_t)p >> 18;
        int32_t a, b;
        if (i >= 2048)
            return DG_SMOOTH[2048];
        a = DG_SMOOTH[i];
        b = DG_SMOOTH[i + 1];
        return a + mulsh(b - a, (int32_t)((uint32_t)p & 0x3FFFF), 18);
    }
    }
}

/* the voice's pitch lim (Q12 blocks, > 0) into its glide */
static int32_t path_at(const dg_voice *v, uint32_t lim)
{
    int n = v->npath - 1;
    int32_t p;
    if (v->dur <= (JUMP_BLOCKS << v->tsh) || lim >= v->dur)
        return v->path[n];
    p = (int32_t)ushr(umul(lim, v->rcp), v->rsh);
    if (n == 1) {
        int32_t val = v->path[0] + mulsh(v->path[1] - v->path[0], shape_at(p, v->shape), 29);
        if (v->shape == 8)
            val = v->path[0] + floordiv(val - v->path[0] + 50 * 65536 + TIE16, C16) * C16;
        return val;
    }
    {
        uint32_t pn = ((uint32_t)p >> 1) * (uint32_t)n;  /* Q28 */
        int32_t i = (int32_t)(pn >> 28);
        if (i > n - 1)
            i = n - 1;
        return v->path[i] + mulsh(v->path[i + 1] - v->path[i], ease((int32_t)((pn & 0xFFFFFFF) << 1)), 29);
    }
}

/* ------------------------------------------------------------------ voices */
static int32_t anchor(const dg_track *t, int i)     /* cents */
{
    int32_t st = t->avoic <= 64 ? 200 + (220 * t->avoic) / 64 : 420 + ((t->avoic - 64) * 580) / 63;   /* voic_step */
    int32_t a = t->aroot * 100 + floordiv((t->apos - 64) * 2400, 64) + i * st;
    return a > DG_CAND_HI * 100 ? DG_CAND_HI * 100 : a < DG_CAND_LO * 100 ? DG_CAND_LO * 100 : a;
}

static dg_voice *ensure(dg_track *t, int i)        /* _ensure */
{
    dg_voice *v = &t->v[i];
    if (!v->started) {
        v->started = 1;
        int32_t a = anchor(t, i);                   /* cents: where VOIC puts this voice over the root */
        v->note = a / 100;
        v->cur = v->tgt = a * 65536;
    }
    if (!v->rng)
        v->rng = rng_seed(t, (uint32_t)i, R_DRIFT);
    return v;
}

#define KEEP 0xFFFFFFFFu

static void push(dg_track *t, int i, int jump, uint32_t glide, int shape, uint32_t delay, const int32_t *via, int nvia,
                 uint32_t tsh)
{
    dg_voice *v = &t->v[i];
    int32_t old = v->tgt, d;
    int k;
    v->tgt = v->note * C16;
    if (glide != KEEP)
        v->glide = glide;
    d = v->tgt - old;
    if (d > 32768 || d < -32768 || nvia) {
        v->path[0] = v->cur;
        for (k = 0; k < nvia; k++)
            v->path[1 + k] = via[k];
        v->path[1 + nvia] = v->tgt;
        v->npath = (uint8_t)(nvia + 2);
        v->t0 = t->b;
        v->delay = delay;
        v->dur = v->glide;
        v->tsh = tsh;
        v->shape = (uint8_t)shape;
        if (v->dur > (JUMP_BLOCKS << tsh)) {                        /* progress = el * rcp >> rsh, rcp in (2^30, 2^31] */
            uint32_t bits = 0, x = v->dur, e;
            u64p num;
            while (x) {
                bits++;
                x >>= 1;
            }
            v->rsh = bits + 1;
            e = 29 + v->rsh;
            num.hi = e >= 32 ? 1u << (e - 32) : 0;
            num.lo = e < 32 ? 1u << e : 0;
            v->rcp = udiv64(num, v->dur);
        }
    }
    if (jump) {
        v->cur = v->tgt;
        v->npath = 0;
    }
}

static uint32_t glid_q(const dg_track *t, const dg_params *p, uint32_t tsh)
{
    if (p->glid <= 9) {
        uint32_t n16 = p->glid == 9 ? 256 : GLID16[p->glid];
        return muldiv_r(n16 * 2700000u, 1u << tsh, t->tempo);   /* 1/16 bar = 2,700,000 / tempo word blocks */
    }
    return ((p->glid == 10 ? 15u : p->glid == 11 ? 30u : 60u) * 1500u) << tsh;
}

static void layout(const dg_params *p, int *n, int *sub)
{
    int c = p->vcnt > DG_NV ? DG_NV : p->vcnt;
    *sub = p->bass != 0;                            /* the mono bass voice: the slot after the chord voices */
    *n = c - (*sub ? 1 : 0);
    if (*n < 1)
        *n = 1;
}

/* route: delays (blocks << tsh) per voice for ORDR / STAG */
static void route(dg_track *t, const int8_t *mv_v, int m, uint32_t *delays, uint32_t tsh)
{
    int8_t seq[DG_NV];
    uint32_t st = STAG2[t->p.stag] * 1350000u;     /* half sixteenths -> blocks * tempo word */
    int k;
    for (k = 0; k < m; k++)
        delays[(int)mv_v[k]] = 0;
    if (t->p.ordr == 0 || st == 0 || m < 2)
        return;
    sort_by_cur(t, mv_v, m, seq);
    if (t->p.ordr == 2) {
        for (k = 0; k < m / 2; k++) {
            int8_t x = seq[k];
            seq[k] = seq[m - 1 - k];
            seq[m - 1 - k] = x;
        }
    } else if (t->p.ordr == 3) {
        int8_t r[DG_NV];
        int lo = 0, hi = m - 1, c = 0;
        for (k = 0; k < m; k++)
            r[k] = seq[k];
        while (lo <= hi) {
            seq[c++] = r[lo];
            if (hi != lo)
                seq[c++] = r[hi];
            lo++;
            hi--;
        }
    } else if (t->p.ordr == 4) {
        uint32_t x = rng_seed(t, 0xFF, R_ORDER);
        for (k = m - 1; k > 0; k--) {
            int j = (int)below(&x, (uint32_t)k + 1);
            int8_t s = seq[k];
            seq[k] = seq[j];
            seq[j] = s;
        }
    }
    for (k = 0; k < m; k++)
        delays[(int)seq[k]] = muldiv_r((uint32_t)k * st, 1u << tsh, t->tempo);
}

static int steps_via(const dg_track *t, int32_t frm, int32_t to, int32_t *out)
{
    /* scale notes strictly between, nearest first in the glide's direction, at most 10 (no big local array:
     * this runs in the audio interrupt) */
    int32_t lo = frm < to ? frm : to, hi = frm < to ? to : frm, n;
    int32_t a = floordiv(lo, C16), b = floordiv(hi, C16) + 1;   /* only the notes between the two pitches */
    int r = 0, k;
    if (a < 0)
        a = 0;
    if (b > 127)
        b = 127;
    for (k = 0; k <= b - a && r < 10; k++) {
        int32_t x;
        n = frm > to ? b - k : a + k;
        x = n * C16;
        if (x > lo + 1966080 + TIE16 && x < hi - 1966080 - TIE16 && in_scale(t, n))
            out[r++] = x;
    }
    return r;
}

/* rank: voices of the move list sorted by target note (stable in list order) */
static void rank_by_note(const int8_t *mv_v, const int32_t *mv_n, int m, int8_t *rk, int32_t *rn)
{
    int a, b;
    for (a = 0; a < m; a++) {
        b = a;
        while (b > 0 && rn[b - 1] > mv_n[a]) {
            rk[b] = rk[b - 1];
            rn[b] = rn[b - 1];
            b--;
        }
        rk[b] = mv_v[a];
        rn[b] = mv_n[a];
    }
}

static uint32_t glide_all(dg_track *t, const int8_t *mv_v, const int32_t *mv_n, int m, int move, uint32_t *tsh_out)
{
    const dg_params *p = &t->p;
    int path = p->path, shape = path == 9 ? 2 : path, k, j;
    uint32_t secs, delays[DG_NV], tsh = 12, bound;
    uint32_t gs[DG_NV], last = 0;
    int32_t svs[DG_NV][10];
    const int32_t *vps[DG_NV];
    int nvs[DG_NV];
    /* Q16 time if the longest glide and delay this plan can make, before it is fitted into GLID, fit 65536 blocks
     * (timing x2.5, a Cascade's 0.6, delays < 6 steps) */
    bound = (glid_q(t, p, 12) >> 12) * 4 + 6 * (STAG2[p->stag] * 1350000u / t->tempo) + 64;
    if (bound < 65536)
        tsh = 16;
    *tsh_out = tsh;
    secs = glid_q(t, p, tsh);
    int32_t via[DG_NV][DG_MAXPATH - 2];
    int nvia[DG_NV];
    int8_t rk[DG_NV];
    int32_t rn[DG_NV];
    for (k = 0; k < DG_NV; k++)
        nvia[k] = 0;
    route(t, mv_v, m, delays, tsh);
    rank_by_note(mv_v, mv_n, m, rk, rn);
    if (!secs) {                                    /* GLID 0 is a hard change: no Move, no delays */
        move = 0;
        for (k = 0; k < DG_NV; k++)
            delays[k] = 0;
    }
    if (move >= MV_BLOOM && move <= MV_FALL) {
        int32_t lo = mv_n[0], hi = mv_n[0];
        uint32_t nn = (uint32_t)(m > 0 ? m : 1);
        for (k = 1; k < m; k++) {
            if (mv_n[k] < lo)
                lo = mv_n[k];
            if (mv_n[k] > hi)
                hi = mv_n[k];
        }
        for (k = 0; k < m; k++) {
            int i = mv_v[k];
            int32_t c = mv_n[k];
            switch (move) {
            case MV_BLOOM:
                via[i][0] = lo * C16;
                nvia[i] = 1;
                break;
            case MV_SWOOP:
                via[i][0] = c * C16 - 1200 * 65536;
                nvia[i] = 1;
                break;
            case MV_FALL:
                via[i][0] = c * C16 + 1200 * 65536;
                nvia[i] = 1;
                break;
            case MV_CONVERGE:
                via[i][0] = (lo + hi) * 3276800;
                nvia[i] = 1;
                break;
            case MV_SCATTER: {
                int32_t opts[15];
                int no = 0;
                for (j = c - 7; j < c + 8; j++)
                    if (j != c && in_scale(t, j))
                        opts[no++] = j;
                if (no) {
                    uint32_t x = rng_seed(t, (uint32_t)i, R_SCATTER);
                    via[i][0] = opts[below(&x, (uint32_t)no)] * C16;
                    nvia[i] = 1;
                }
                break;
            }
            default:
                break;
            }
        }
        for (k = 0; k < m; k++) {
            int i = rk[k];
            if (move == MV_CASC_UP)
                delays[i] = muldiv_r(secs, 3u * (uint32_t)k, 5u * nn);
            else if (move == MV_CASC_DOWN)
                delays[(int)rk[m - 1 - k]] = muldiv_r(secs, 3u * (uint32_t)k, 5u * nn);
            else if (move == MV_SPIRAL) {
                via[i][0] = rn[k] * C16 + ((k % 2) ? 1200 * 65536 : -1200 * 65536);
                nvia[i] = 1;
            }
        }
        if (path == 9 || path == 8)
            shape = 2;
    }
    for (k = 0; k < m; k++) {
        int i = mv_v[k], r = 0, nv;
        dg_voice *v = &t->v[i];
        int32_t frm = v->cur, note = mv_n[k], *sv = svs[k], d0;
        const int32_t *vp = via[i];
        uint32_t g = secs, mm = (uint32_t)(m - 1 > 1 ? m - 1 : 1);
        v->note = note;
        nv = nvia[i];
        if (!nv && path == 9) {
            nv = steps_via(t, frm, note * C16, sv);
            vp = sv;
        }
        while (rk[r] != i)
            r++;
        switch (p->time) {
        case 1: {
            int32_t d = note * C16 - frm;
            uint32_t ad = (uint32_t)(d < 0 ? -d : d);
            if (ad < 11468800u)
                ad = 11468800u;                         /* 0.35 * 500 cents */
            if (ad > 81920000u)
                ad = 81920000u;                         /* 2.5 * 500 cents */
            g = muldiv_r(secs, ad, 32768000u);
            break;
        }
        case 2:
            g = muldiv_r(secs, 18u * mm - 9u * (uint32_t)r, 10u * mm);
            break;
        case 3:
            g = muldiv_r(secs, 6u * mm + 9u * (uint32_t)r, 10u * mm);
            break;
        case 4: {
            uint32_t x = rng_seed(t, (uint32_t)i, R_LOOSE);
            g = muldiv_r(secs, 3u * 16777216u + 5u * r24(&x), 5u * 16777216u);
            break;
        }
        default:
            break;
        }
        gs[k] = g;
        vps[k] = vp;
        nvs[k] = nv;
        d0 = note * C16 - v->tgt;                   /* (push's test: a voice that stays where it is lands nowhere) */
        if ((d0 > 32768 || d0 < -32768 || nv) && delays[i] + g > last)
            last = delays[i] + g;
    }
    /* GLID is the time until the last voice lands: every delay and duration is scaled by GLID / the latest landing
     * (model/digiglide.py glide_all). A Move's turning points are fractions of a voice's own glide and stay. */
    for (k = 0; k < m; k++) {
        int i = mv_v[k];
        uint32_t g = gs[k], d = delays[i];
        if (last) {                                 /* the landing is scaled, then split: the last voice's delay */
            uint32_t end = muldiv_r(d + g, secs, last);     /* and glide add up to GLID exactly */
            d = muldiv_r(d, secs, last);
            g = end - d;
        }
        push(t, i, 0, g, shape, d, vps[k], nvs[k], tsh);
    }
    return secs;
}

static void sub_follow(dg_track *t, const int32_t *mv_n, int m, uint32_t secs, uint32_t tsh, int sub)
{
    int n, s, i, dummy, was_on;
    int32_t lo;
    dg_voice *v;
    layout(&t->p, &n, &dummy);
    s = n;
    for (i = n + 1; i < DG_NV; i++)
        t->v[i].on = 0;
    if (s >= DG_NV)
        return;
    if (!sub || !m) {
        t->v[s].on = 0;
        return;
    }
    v = ensure(t, s);
    was_on = v->on;
    v->vib = 0;
    v->drift = 0;
    v->pan = 0;
    v->level = 19661;
    v->inc = INC[5];
    (void)mv_n;
    lo = t->aroot + 12 * ((t->p.bass - 1) % 3 - 2);  /* the root, BASS's octaves down (FOL-2 -1 0, SOL-2 -1 0) */
    v->note = lo;
    v->on = 1;
    push(t, s, !was_on, secs, 2, 0, 0, 0, tsh);
}

/* ------------------------------------------------------------------ public */
void dg_init(dg_track *t, uint32_t tempo_word, uint32_t pattern)
{
    int i, k;
    for (i = 0; i < DG_NV; i++) {
        dg_voice *v = &t->v[i];
        v->started = v->on = v->shape = v->npath = 0;
        v->note = 0;
        v->tgt = v->cur = 0;
        for (k = 0; k < DG_MAXPATH; k++)
            v->path[k] = 0;
        v->t0 = v->delay = v->dur = v->rcp = v->rsh = 0;
        v->tsh = 12;
        v->glide = 2u * 1500u * 4096u;
        v->dr = v->dr_t = v->dr_n = 0;
        v->ph = PH0[i];
        v->inc = INC[i];
        v->rng = 0;
        v->vib = v->drift = 0;
        v->pan = BASE_PAN[i];
        v->level = LEVEL[i];
    }
    t->p.key = 0; t->p.scl = 1; t->p.voic = 64; t->p.pos = 64; t->p.vcnt = 5; t->p.bass = 1; t->p.sprd = 77;
    t->p.move = 0; t->p.glid = 5; t->p.path = 0; t->p.time = 0; t->p.ordr = 0; t->p.stag = 0; t->p.drft = 8;
    t->p.vib = 4; t->p.scrb = 127;
    t->tempo = tempo_word;
    t->pattern = pattern;
    t->b = 0;
    t->key = 0;
    t->aroot = 60;
    t->avoic = 64;
    t->apos = 64;
    t->step = 0;
    t->scrb = t->scrb_t = ONE30;
}

/* reference pitch of voice i for the voice leader: its VOIC place when it is new or VOIC was turned, else where it
 * is, but never more than a fifth (LEASH) from that place */
static int32_t lead_ref(const dg_track *t, int i, uint32_t was, uint32_t cw)
{
    int32_t a = anchor(t, i) * 65536, c = t->v[i].cur;
    if ((cw & DG_CW_REVOICE) || !((was >> i) & 1))
        return a;
    if (c < a - DG_LEASH16)
        return a - DG_LEASH16;
    if (c > a + DG_LEASH16)
        return a + DG_LEASH16;
    return c;
}

void dg_trig(dg_track *t, int32_t step, const dg_params *p, uint32_t cw)
{
    int n, sub, i, any = 0;
    int8_t mv_v[DG_NV];
    int32_t mv_n[DG_NV], ref[DG_NV], root = (int32_t)((cw >> 12) & 0x7F), bass_note;
    uint32_t was = 0, pcs = cw & 0xFFF;
    t->step = step;
    t->p.key = p->key; t->p.scl = p->scl; t->p.voic = p->voic; t->p.pos = p->pos;   /* field by field: a struct */
    t->p.vcnt = p->vcnt; t->p.bass = p->bass; t->p.sprd = p->sprd; t->p.move = p->move; /* copy becomes memcpy */
    t->p.glid = p->glid; t->p.path = p->path; t->p.time = p->time; t->p.ordr = p->ordr;
    t->p.stag = p->stag; t->p.drft = p->drft; t->p.vib = p->vib; t->p.scrb = p->scrb;
    t->key = imod12(p->key);
    if (root < DG_ROOT_LO)
        root = DG_ROOT_LO;
    if (root > DG_ROOT_HI)
        root = DG_ROOT_HI;
    t->aroot = root;
    t->avoic = p->voic;
    t->apos = p->pos;
    bass_note = -1;                                 /* the chord voices all take their nearest tone */
    for (i = 0; i < DG_NV; i++)
        was |= (uint32_t)t->v[i].started << i;
    t->scrb_t = (int32_t)muldiv(p->scrb, ONE30, 127);
    layout(p, &n, &sub);
    if (p->bass >= 4) {                             /* BASS Solo: the bass voice alone, the chord muted */
        uint32_t tsh = (glid_q(t, p, 12) >> 12) * 4 + 64 < 65536 ? 16 : 12;
        for (i = 0; i < DG_NV; i++)
            if (i != n)
                t->v[i].on = 0;
        if ((cw & DG_CW_TAIL) && n < DG_NV && t->v[n].started)
            t->v[n].on = 1;
        sub_follow(t, mv_n, 1, glid_q(t, p, tsh), tsh, 1);
        return;
    }
    for (i = 0; i < n; i++) {
        dg_voice *v = &t->v[i];
        int32_t pan = mulsh(BASE_PAN[i], p->sprd * 65536 / 77, 16);
        v->vib = p->vib;
        v->drift = p->drft;
        v->inc = INC[i];
        v->pan = pan > 32767 ? 32767 : pan < -32768 ? -32768 : pan;
        v->level = LEVEL[i];
    }
    for (i = n + (sub ? 1 : 0); i < DG_NV; i++)
        t->v[i].on = 0;
    if (cw & DG_CW_TAIL)                            /* the released chord still rings: glide from it (the bass too) */
        for (i = 0; i < n + (sub ? 1 : 0) && i < DG_NV; i++)
            if (t->v[i].started)
                t->v[i].on = 1;
    for (i = 0; i < n; i++)
        any |= t->v[i].on;
    if (!any) {                                     /* fresh: lay the chord out, attack, no glide */
        for (i = 0; i < n; i++) {
            ensure(t, i);
            ref[i] = lead_ref(t, i, was, cw);
        }
        voicelead(ref, n, pcs, bass_note, mv_v, mv_n);
        for (i = 0; i < n; i++) {
            dg_voice *v = &t->v[(int)mv_v[i]];
            v->note = mv_n[i];
            v->on = 1;
            push(t, mv_v[i], 1, KEEP, 0, 0, 0, 0, 12);
        }
        sub_follow(t, mv_n, n, SUB_FRESH, 12, sub);
        return;
    }
    for (i = 0; i < n; i++)
        if (!t->v[i].on) {
            ensure(t, i);
            t->v[i].on = 1;
            push(t, i, 1, KEEP, 0, 0, 0, 0, 12);
        }
    if (p->move == MV_EVOL) {                       /* amb_evolve */
        int m = 0, j;
        uint32_t secs, tsh;
        for (i = 0; i < n; i++) {
            dg_voice *v = &t->v[i];
            int32_t cands[11];
            int nc = 0;
            for (j = v->note - 5; j < v->note + 6; j++)
                if (j != v->note && in_scale(t, j))
                    cands[nc++] = j;
            if (nc) {
                uint32_t x = rng_seed(t, (uint32_t)i, R_EVOL);
                mv_v[m] = (int8_t)i;
                mv_n[m++] = cands[below(&x, (uint32_t)nc)];
            }
        }
        if (m) {
            int32_t bass[DG_NV];
            secs = glide_all(t, mv_v, mv_n, m, 0, &tsh);
            for (i = 0; i < n; i++)
                bass[i] = t->v[i].note;
            sub_follow(t, bass, n, secs, tsh, sub);
        }
        return;
    }
    for (i = 0; i < n; i++)                         /* reference pitches (after any re-attack above) */
        ref[i] = lead_ref(t, i, was, cw);
    voicelead(ref, n, pcs, bass_note, mv_v, mv_n);
    {
        uint32_t tsh, secs = glide_all(t, mv_v, mv_n, n, p->move, &tsh);
        sub_follow(t, mv_n, n, secs, tsh, sub);
    }
}

void dg_gate_off(dg_track *t)
{
    int i;
    for (i = 0; i < DG_NV; i++)
        t->v[i].on = 0;
}

void dg_set_scrb(dg_track *t, int32_t value)
{
    t->scrb_t = (int32_t)muldiv((uint32_t)value, ONE30, 127);
}

uint32_t dg_block(dg_track *t, int32_t out_c16[DG_NV])
{
    uint32_t mask = 0;
    int i;
    int32_t d = t->scrb_t - t->scrb;
    t->scrb += mulsh(d, K_SCRB, 30);
    d = t->scrb_t - t->scrb;
    if (d < 1074 && d > -1074)
        t->scrb = t->scrb_t;
    for (i = 0; i < DG_NV; i++) {
        dg_voice *v = &t->v[i];
        if (!v->started) {
            out_c16[i] = 0;
            continue;
        }
        if (v->npath) {
            uint32_t k = t->b - v->t0 + 1, el;
            int pos, done;
            if (k >= (1u << (32 - v->tsh))) {           /* past any glide of this scale */
                pos = 1;
                el = 0xFFFFFFFFu;
            } else {
                pos = (k << v->tsh) > v->delay;
                el = pos ? (k << v->tsh) - v->delay : 0;
            }
            done = pos && el >= v->dur;
            if (!pos)
                v->cur = v->path[0];
            else {
                uint32_t lim = el;
                if (t->scrb < ONE30) {
                    uint32_t cap = ushr(umul(v->dur, (uint32_t)(t->scrb < 0 ? 0 : t->scrb)), 30);
                    if (cap < lim)
                        lim = cap;
                }
                v->cur = lim == 0 ? v->path[0] : path_at(v, lim);
            }
            if (done && t->scrb >= ONE30)
                v->npath = 0;
        }
        if (v->drift > 0) {
            if (--v->dr_n <= 0) {
                v->dr_t = ((int32_t)(2 * r24(&v->rng)) - 16777216) * v->drift;
                v->dr_n = 3000 + (int32_t)ushr(umul(r24(&v->rng), 6000), 24);
            }
            v->dr += (v->dr_t - v->dr) / 2250;
        }
        v->ph += v->inc;
        out_c16[i] = v->cur + (v->dr >> 8) + mulsh(v->vib * 65536, sin_cyc(v->ph), 29);
        mask |= 1u << i;
        if (v->on)
            mask |= 1u << (8 + i);
    }
    t->b++;
    return mask;
}

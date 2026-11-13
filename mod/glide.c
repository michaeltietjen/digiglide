/* GLIDE: chord glide machine for Digitone II OS 1.11 (ColdFire side).
 *
 * Hook: glide_stub (hooks.S) runs at the top of the audio ISR, right before the driver sends the 2688-byte frame at
 * 0x80005e60 to the DSP. glide_tx() rewrites that frame:
 *   - the GLIDE track reserves GLIDE_NV voices through the stock VOICE menu (VOICES = 4); stock then plays that track only
 *     on those voices and no other track uses them (notes/open_questions.md, Q1);
 *   - when stock starts a note on one of them (the "source" voice), GLIDE turns it into a chord: the source's sound
 *     record, velocity, level and machine are copied to every chord voice, each gets its chord tone in the note word;
 *   - the DSP follows the note word every block, fractional byte included (Q2): slides are only note-word updates.
 *
 * Frame layout (ColdFire view, big-endian halfwords): +0x02+2v note << 8, +0x22/+0x26 note-on mask, +0x24/+0x28 note-off
 * mask, +0x34+2v velocity, +0x54+2v velocity curve, +0x74+2v level, +0x94+2v machine, +0xda+146v sound record,
 * +0xa5a+2v voice -> track.
 */
#include "glide.h"

#define FRAME ((volatile u8 *)0x80005e60)

static inline u16 rd16(volatile u8 *f, u32 o) { return *(volatile u16 *)(f + o); }
static inline void wr16(volatile u8 *f, u32 o, u16 v) { *(volatile u16 *)(f + o) = v; }

struct glide_state G;                   /* everything GLIDE keeps between blocks (BSS, zeroed by the loader) */

/* Test fixture until M4's p-locks: when glide_seq_n > 0, chord trig k uses glide_seq[k % glide_seq_n] (the emulator tests
 * write this table through memory to sequence a progression). */
struct glide_params glide_seq[8];
u32 glide_seq_n;

void glide_init(void)
{
    u32 i;
    G.blocks = 0;
    G.src = -1;
    G.n = 0;
    G.active = 0;
    G.param = glide_defaults;
    for (i = 0; i < GLIDE_NV; i++) {
        G.v[i].cur = 0;
        G.v[i].on = 0;
        G.was_on[i] = 0;
    }
}

/* Copy the per-voice words and sound record of voice s to voice d (both in the frame). */
static void clone_voice(volatile u8 *f, u32 s, u32 d)
{
    volatile u32 *a = (volatile u32 *)(f + 0xda + 146 * s);
    volatile u32 *b = (volatile u32 *)(f + 0xda + 146 * d);
    volatile u16 *a2, *b2;
    u32 i;
    if (s == d)
        return;
    /* 146 B = 36 longwords + 1 halfword; records start on halfword boundaries (0xda + 146v is even) */
    if (((u32)a | (u32)b) & 3) {
        a2 = (volatile u16 *)a; b2 = (volatile u16 *)b;
        for (i = 0; i < 73; i++)
            b2[i] = a2[i];
    } else {
        for (i = 0; i < 36; i++)
            b[i] = a[i];
        ((volatile u16 *)b)[72] = ((volatile u16 *)a)[72];
    }
    wr16(f, 0x34 + 2 * d, rd16(f, 0x34 + 2 * s));
    wr16(f, 0x54 + 2 * d, rd16(f, 0x54 + 2 * s));
    wr16(f, 0x74 + 2 * d, rd16(f, 0x74 + 2 * s));
    wr16(f, 0x94 + 2 * d, rd16(f, 0x94 + 2 * s));
    wr16(f, 0xa5a + 2 * d, rd16(f, 0xa5a + 2 * s));
}

void glide_tx(void)
{
    volatile u8 *f = FRAME;
    u16 on = rd16(f, 0x22), off = rd16(f, 0x24);
    u16 mine = (u16)(((1u << GLIDE_NV) - 1) << GLIDE_V0);
    u16 non = on & ~mine, noff = off & ~mine;     /* stock's masks for every other voice pass through unchanged */
    s32 v, s = -1;
    u32 i;

    G.blocks++;
    if (G.param.track >= 16 || G.param.bypass) {
        return;
    }

    for (v = GLIDE_V0; v < GLIDE_V0 + GLIDE_NV; v++)    /* a new note of the GLIDE track this block? (lowest voice wins) */
        if ((on >> v) & 1 && rd16(f, 0xa5a + 2 * v) == G.param.track) {
            s = v;
            break;
        }

    if (s >= 0) {
        s32 root = (s32)(rd16(f, 0x02 + 2 * s) >> 8);   /* the trig's note transposes ROOT (spec: keyboard still works) */
        G.src = s;
        if (glide_seq_n && glide_seq_n <= 8) {
            /* byte offset by hand: an 8-byte-strided index makes GCC emit scale 8, which ColdFire lacks */
            volatile u32 off8 = (G.trigs % glide_seq_n) << 3;
            const u8 *q = (const u8 *)glide_seq + off8;
            u8 *p = (u8 *)&G.param;
            for (i = 0; i < sizeof(struct glide_params); i++)
                p[i] = q[i];
        }
        G.n = glide_chord(&G.param, root, G.target);
        glide_assign(&G, s);                           /* M1: fresh chord, M2+: voice leading / slides */
        G.active = 1;
    }

    if (G.active && G.src >= 0) {
        s32 src = G.src;
        int src_off = (off >> src) & 1;
        if (src_off)
            for (i = 0; i < GLIDE_NV; i++)
                G.v[i].on = 0;                         /* the trig ended: release the whole chord */
        glide_tick(&G);                                /* slides keep moving through the release tail */
        for (i = 0; i < GLIDE_NV; i++) {
            u32 d = GLIDE_V0 + i;
            clone_voice(f, src, d);                    /* every block: modulation / envelopes follow the source */
            wr16(f, 0x02 + 2 * d, glide_word(&G, i));
            if (G.v[i].start)
                non |= 1u << d;
            if (G.was_on[i] && !G.v[i].on)
                noff |= 1u << d;
            G.was_on[i] = G.v[i].on;
            G.v[i].start = 0;
        }
        if (src_off)
            G.active = 2;                              /* released: keep cloning for the release tail */
    }

    wr16(f, 0x22, non); wr16(f, 0x26, non);
    wr16(f, 0x24, noff); wr16(f, 0x28, noff);
}

/* GLIDE shared definitions. voicelead.c is plain C with no firmware addresses: it builds for the ColdFire mod and for the
 * host unit tests (tests/test_voicelead.c). */
#ifndef GLIDE_H
#define GLIDE_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long u32;
typedef signed char s8;
typedef short s16;
typedef long s32;

#define GLIDE_NV 4                 /* chord voices: triads use 3, 7ths / 9ths / quartal use 4 */
#define GLIDE_V0 0                 /* first DSP voice of the GLIDE track's reserved block (track 1, VOICES = 4) */
#define SEMI 256                   /* pitch unit: 1/256 semitone = the note word's resolution */

enum { CHRD_MAJ, CHRD_MIN, CHRD_SUS2, CHRD_SUS4, CHRD_7, CHRD_MAJ7, CHRD_M7, CHRD_ADD9, CHRD_MAJ9, CHRD_5OCT,
       CHRD_QUARTAL, CHRD_N };
enum { VOIC_CLOSE, VOIC_SPREAD, VOIC_DROP2, VOIC_OPEN, VOIC_N };
enum { CURV_LINEAR, CURV_EASE_OUT, CURV_EASE_IN_OUT, CURV_N };
enum { GLID_0, GLID_32, GLID_16, GLID_8, GLID_4, GLID_2, GLID_1BAR, GLID_2BAR, GLID_4BAR, GLID_8BAR, GLID_N };

struct glide_params {
    u8 track;                      /* 0..15; >= 16 = off */
    u8 bypass;
    u8 root;                       /* MIDI note of ROOT (C3 = 48); the trig note transposes it relative to C4 (60) */
    u8 chrd;                       /* CHRD_* */
    u8 voic;                       /* VOIC_* */
    u8 glid;                       /* GLID_* (tempo-synced) */
    u8 curv;                       /* CURV_* */
    u8 drft;                       /* 0..127 */
};

struct glide_voice {
    s32 cur;                       /* sounding pitch (1/256 semitone) */
    s32 from, to;                  /* slide endpoints */
    s32 detune;                    /* DRFT detune for this slide (1/256 semitone) */
    u32 delay;                     /* DRFT start delay (sequencer units) */
    u8 on;                         /* sounding (not released) */
    u8 start;                      /* attack this block */
    u8 release_at_end;             /* surplus voice: release when its slide ends */
    u8 pad;
};

struct glide_state {
    u32 blocks;                    /* hook calls (proves the hook is live) */
    s32 src;                       /* DSP voice stock started for the current chord */
    u32 n;                         /* tones in the current chord */
    u32 active;                    /* 0 idle, 1 sounding, 2 released */
    struct glide_params param;
    s32 target[GLIDE_NV];          /* chord tones of the current chord (1/256 semitone), ascending */
    struct glide_voice v[GLIDE_NV];
    u32 elapsed, total;            /* slide progress in sequencer units (2 x tempo word per block) */
    u32 seed;
    u32 trigs;                     /* chord trigs seen (tests) */
    s32 last_cost;                 /* voice-leading score of the last assignment (tests) */
    u8 was_on[GLIDE_NV];           /* note-on state sent last block (note-off edges) */
};

extern const struct glide_params glide_defaults;

/* voicelead.c */
u32 glide_chord(const struct glide_params *p, s32 trig_note, s32 *out);   /* -> tone count; out ascending */
void glide_assign(struct glide_state *g, s32 src);                        /* new chord: voices -> tones, starts */
void glide_tick(struct glide_state *g);                                   /* advance slides one block */
u16 glide_word(const struct glide_state *g, u32 i);                       /* note word for chord voice i */
u32 glide_units(u32 glid);                                                /* GLID -> sequencer units */
u32 glide_tempo(void);                                                    /* units per block (tempo word x 2) */

#endif

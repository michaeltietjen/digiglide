/* Host tests of the voice-leading core: cc -DGLIDE_HOST -I.. test_voicelead.c ../voicelead.c && ./a.out */
#include <stdio.h>
#include <string.h>
#include "glide.h"
static u32 tempo = 120 * 120 * 2;
u32 glide_tempo(void) { return tempo; }
static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); } } while (0)

static void trig(struct glide_state *g, int root, int chrd)
{
    for (int b = 0; b < 6000 && g->active; b++) glide_tick(g);   /* the previous slide finishes (1 bar = 3000 blocks) */
    g->param.root = (u8)root; g->param.chrd = (u8)chrd;
    g->n = glide_chord(&g->param, 60, g->target);
    glide_assign(g, 0);
    g->active = 1;
}
static void show(const char *what, struct glide_state *g)
{
    printf("%-26s", what);
    for (int i = 0; i < GLIDE_NV; i++)
        printf("  v%d %s %6.2f->%6.2f", i, g->v[i].on ? "on " : "off", g->v[i].from / 256.0, g->v[i].to / 256.0);
    printf("  cost %.2f\n", g->last_cost / 256.0);
}
static int voice_at(struct glide_state *g, double from, double to)
{
    for (int i = 0; i < GLIDE_NV; i++)
        if (g->v[i].on && g->v[i].from == (s32)(from * 256) && g->v[i].to == (s32)(to * 256)) return i;
    return -1;
}
int main(void)
{
    struct glide_state g; s32 t[4]; u32 n;
    memset(&g, 0, sizeof g); g.param = glide_defaults; g.param.drft = 0; g.param.glid = GLID_1BAR;

    n = glide_chord(&g.param, 60, t);
    CHECK(n == 3 && t[0] == 48 * 256 && t[1] == 52 * 256 && t[2] == 55 * 256, "C maj close from C3 = 48 52 55");
    g.param.chrd = CHRD_MAJ7; n = glide_chord(&g.param, 60, t);
    CHECK(n == 4 && t[3] == 59 * 256, "maj7 has 4 voices, top B");
    g.param.chrd = CHRD_MAJ; g.param.voic = VOIC_SPREAD; n = glide_chord(&g.param, 60, t);
    CHECK(t[0] == 48 * 256 && t[1] == 55 * 256 && t[2] == 64 * 256, "spread: C G E'");
    g.param.voic = VOIC_DROP2; n = glide_chord(&g.param, 60, t);
    CHECK(t[0] == 40 * 256 && t[1] == 48 * 256 && t[2] == 55 * 256, "drop-2: E, C G");
    g.param.voic = VOIC_CLOSE;
    n = glide_chord(&g.param, 62, t);
    CHECK(t[0] == 50 * 256, "trig note D4 transposes ROOT C3 up 2");

    /* M2: C maj -> A min holds C and E, moves G to A */
    trig(&g, 48, CHRD_MAJ); show("C maj (first trig)", &g);
    CHECK(g.v[0].start && g.v[1].start && g.v[2].start && !g.v[3].on, "first trig attacks 3 voices");
    trig(&g, 45, CHRD_MIN); show("-> A min", &g);
    CHECK(voice_at(&g, 48, 48) >= 0, "C holds");
    CHECK(voice_at(&g, 52, 52) >= 0, "E holds");
    CHECK(voice_at(&g, 55, 57) >= 0, "G slides up to A");
    CHECK(g.last_cost == 2 * 256, "total movement 2 semitones");
    for (int i = 0; i < GLIDE_NV; i++) CHECK(!g.v[i].start, "no retrigger while sounding (voice %d)", i);

    /* A min -> F maj -> G maj: minimal movement, no crossings */
    trig(&g, 41, CHRD_MAJ); show("-> F maj", &g);
    CHECK(voice_at(&g, 48, 48) >= 0 && voice_at(&g, 57, 57) >= 0 && voice_at(&g, 52, 53) >= 0, "Am->F: C, A hold; E->F");
    trig(&g, 43, CHRD_MAJ); show("-> G maj", &g);
    CHECK(g.last_cost == 6 * 256, "F->G: 6 semitones, the minimum for this pair (%.2f)", g.last_cost / 256.0);

    /* 3 -> 4 voices: the 4th tone attacks fresh on the free voice */
    trig(&g, 48, CHRD_MAJ7); show("-> C maj7", &g);
    { int starts = 0; for (int i = 0; i < 4; i++) starts += g.v[i].start; CHECK(starts == 1, "one new voice attacks"); }
    /* 4 -> 3: the surplus voice glides to a kept tone and releases at the end */
    trig(&g, 45, CHRD_MIN); show("-> A min", &g);
    { int rel = 0; for (int i = 0; i < 4; i++) rel += g.v[i].release_at_end; CHECK(rel == 1, "one surplus voice releases"); }

    /* slides: GLID 1 bar at 120 BPM = 2 s = 3000 blocks; ease-out ends exactly on target */
    memset(&g, 0, sizeof g); g.param = glide_defaults; g.param.drft = 0; g.param.glid = GLID_1BAR;
    trig(&g, 48, CHRD_MAJ);
    g.param.root = 45; g.param.chrd = CHRD_MIN; g.n = glide_chord(&g.param, 60, g.target); glide_assign(&g, 0);
    show("C maj -> A min (timed)", &g);
    int gv = voice_at(&g, 55, 57); s32 mid = 0;
    for (int b = 0; b < 3000; b++) { glide_tick(&g); if (b == 1499) mid = g.v[gv].cur; }
    CHECK(g.v[gv].cur == 57 * 256, "slide lands on A after 1 bar (%.3f)", g.v[gv].cur / 256.0);
    CHECK(mid > 56.4 * 256 && mid < 56.6 * 256, "ease-out at half time = 75%% of the way (%.3f)", mid / 256.0);

    /* GLID 0: hard change attacks fresh */
    g.param.glid = GLID_0; trig(&g, 41, CHRD_MAJ);
    { int starts = 0; for (int i = 0; i < 4; i++) starts += g.v[i].start; CHECK(starts == 3, "GLID 0 retriggers"); }

    printf(fails ? "%d FAILED\n" : "OK\n", fails);
    return fails != 0;
}

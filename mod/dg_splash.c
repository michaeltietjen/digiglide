/* DigiGlide's boot splash (image 35).
 *
 * Stock start-up: Elektron's static logo screen, then the intro task (entry 0x400d3d86 on 1.11, priority 7) plays the
 * intro: its loop calls a step function (0x400d3c64) once a tick of PIT3 (30 a second: prescaler 512, modulus 8593)
 * until the step returns 0, then stops the timer and lets the start go on. The step builds a Bitmap over the draw
 * buffer, has the intro's routine draw the frame, and sends it with the display flush.
 *
 * The hook is the step's entry (hooks_dg.S, dg_splash_stub). Stock's intro runs as it is, untouched. When its step
 * says "over", the stub answers "go on" instead and calls dg_splash_frame once a tick: it copies a stored frame into
 * the draw buffer and flushes it with stock's own diff flush, until the frames have had their ticks. Then the step
 * says "over" and stock goes on as always. Nothing here runs again after that.
 *
 * A build that played the splash in place of stock's intro was tried and never left the intro in the emulator (the
 * frame clock stopped after one tick): there is no such mode.
 *
 * Only MAIN OS code is touched. The STARTUP menu ([FUNC] at power on) is in the bootstrap, before any of this.
 * How the frames get here: build_dg.py (splash_gen) writes dg_splash_gen.h from mod/splash/. The idea of drawing in
 * the intro's slot is dnfw's bootscreen mod and Digiwerk's boot mark; this code is DigiGlide's own. */
#include <stdint.h>
#include "dg_splash_gen.h"      /* SPLASH_N, SPLASH_TICKS[SPLASH_N], SPLASH_FR[SPLASH_N][1024] (the panel's layout) */

#define FB_FRONT (*(uint8_t *volatile *)OSA_402A0B88)   /* the buffer the next flush sends */
#define DRAW_BUF (*(uint8_t *volatile *)OSA_42C4BAC8)   /* the intro's own copy of that pointer */
typedef uint8_t *(*flush_fn)(void);                     /* sends FB_FRONT, swaps the buffers, returns the new front */

uint32_t dg_splash_phase;                               /* 0: stock's intro runs; 1: the splash (the stub sets it) */
uint32_t dg_splash_ticks, dg_splash_shown;              /* ticks spent and frames sent (tests) */
uint32_t dg_splash_sum;                                 /* the last frame sent, summed (tests) */
static uint32_t cur = 0xFFFFFFFFu;

int dg_splash_frame(void)                               /* one tick: 1 = go on, 0 = the splash is over */
{
    uint32_t f, t = 0, i, sum = 0;
    for (f = 0; f < SPLASH_N; f++) {
        t += SPLASH_TICKS[f];
        if (dg_splash_ticks < t)
            break;
    }
    if (f >= SPLASH_N)
        return 0;
    dg_splash_ticks++;
    if (f != cur) {
        uint8_t *dst = FB_FRONT;
        const uint8_t *src = SPLASH_FR[f];
        if (!dst)
            return 0;                                   /* no display buffer: nothing to show, start as stock */
        for (i = 0; i < 1024; i++) {
            dst[i] = src[i];
            sum = sum * 31 + src[i];
        }
        cur = f;
        DRAW_BUF = ((flush_fn)OSA_40131CF2)();      /* stock's diff flush, as its own frames after the first */
        dg_splash_shown++;
        dg_splash_sum = sum;
    }
    return 1;
}

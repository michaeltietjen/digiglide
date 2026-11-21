/* jsr dg_stub replaces `move.l 0x402876f8,%d0` (6 bytes) at 0x40025e82, at the top of the audio ISR right before the
 * driver sends the frame at 0x80005e60. The ISR saved every register at entry and the code after reads only d0 and the
 * flags of that move: the stub calls dg_tx, restores the scratch registers, then replays the move LAST so the
 * following `bnes` sees its flags (movem and rts leave the CCR alone). Same site and stub as GLIDE M1-M3. */
    .text
    .globl  dg_stub
dg_stub:
    lea     -16(%sp),%sp
    movem.l %d1/%a0-%a1/%d0,(%sp)
    jsr     dg_tx
    movem.l (%sp),%d1/%a0-%a1/%d0
    lea     16(%sp),%sp
    move.l  OSA_402876F8,%d0
    rts

/* image 35, the boot splash (dg_splash.c). jsr dg_splash_stub replaces `lea -28(%sp),%sp ; move.l %d2,-(%sp)`
 * (6 bytes), the entry of the intro's step function, which the intro task calls once a tick with no arguments and
 * whose byte result means "go on" (1) or "over" (0). While stock's intro runs the stub calls the step's body as a
 * subroutine (the two displaced instructions replayed, then on into the step) and passes its result on; when the
 * step says "over" the splash takes the ticks until it is over too. */
    .globl  dg_splash_stub
dg_splash_stub:
    tst.l   dg_splash_phase
    bne.s   2f
    move.l  (%sp)+,%a0                  /* the step, after the displaced instructions */
    pea     1f(%pc)                     /* its rts comes back here */
    lea     -28(%sp),%sp
    move.l  %d2,-(%sp)
    jmp     (%a0)
1:  tst.b   %d0
    beq.s   3f
    rts                                 /* stock's intro goes on */
3:  moveq   #1,%d0
    move.l  %d0,dg_splash_phase
    jsr     dg_splash_frame
    rts
2:  addq.l  #4,%sp                      /* (the return into the step is not used) */
    jsr     dg_splash_frame
    rts

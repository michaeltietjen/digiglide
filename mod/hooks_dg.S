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

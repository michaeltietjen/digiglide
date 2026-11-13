/* jsr glide_stub replaces `move.l 0x402876f8,%d0` (6 bytes) at 0x40025e82, at the top of the audio ISR right before the
 * driver sends the frame at 0x80005e60. The ISR saved every register at entry and the code after reads only d0 and the
 * flags of that move: the stub calls glide_tx, restores the scratch registers, then replays the move LAST so the
 * following `bnes` sees its flags (movem and rts leave the CCR alone). */
    .text
    .globl  glide_stub
glide_stub:
    lea     -16(%sp),%sp
    movem.l %d1/%a0-%a1/%d0,(%sp)
    jsr     glide_tx
    movem.l (%sp),%d1/%a0-%a1/%d0
    lea     16(%sp),%sp
    move.l  0x402876f8,%d0
    rts

| derived from angellinares/dnfw csrc/usbprobe/probe.S (AGPL-3.0-or-later), itself derived from irpina/digihealth
| (sysinfo.s), GPL-2.0-or-later, used under GPL-3.0 within an AGPL-3.0-or-later project.
|
| DigiGlide's read-only USB SysEx probe: F0 00 20 3C 7D 00 <pack7 body> F7, dnfw's usbprobe protocol (its host tool
| tools/dn2probe.py talks to it), reduced to the two commands that need no hook besides the SysEx router's:
|
|   request  <pack7: u16 seq, u8 cmd, args>
|   reply    <pack7: u16 seq, u8 cmd|0x80, u8 status, payload>     status 0 ok, 1 refused argument, 2 unknown command
|   HELLO (1)  -> u16 proto (3), u32 audio frames since boot, the build's tag ("DG <build>")
|   PEEK  (3)  u32 addr, u16 len (1..1024) -> u32 addr, the bytes. DDR, the on-chip SRAM and the SSI0 audio windows
|              only: never a peripheral register.
|   STATS (2) is not built (it needs hooks in the audio ISR and the scheduler): it answers status 2.
|
| There is no write command. USB only. The router drops device 0x7D itself after the hook, so stock's own SysEx
| handling is untouched. Addresses are OS 1.11's, through the OSA_ table (port/addr_1.12.json).
#define XSTR(x) STR(x)
#define STR(x) #x
        .equ PROTO,       3
        .equ C_HELLO,     1
        .equ C_PEEK,      3
        .equ PEEK_MAX,    1024
        .equ NRANGES,     3
        .equ RQ_MAX,      16
        .equ PORT_USB,    2
        .equ AUD_RX,      0x4e6df100
        .equ AUD_TX,      0x4e6e0100
        .equ AUD_N,       4096

        .bss
        .balign 4
rq:     .skip   0x20                    | a request, unpacked
rp:     .skip   0x420                   | a reply before packing: 4 + 4 + PEEK_MAX
        .globl  dg_probe_tx
dg_probe_tx:
tx:     .skip   0x4C0                   | a reply as sent

        .text
| At the router hook (was: lea ELK_HDR,%a3), once per F0 message other than F0 7E, in the MIDI input task.
| a0 = a1 = the message, F0..F7; d1 = its length; d2 = where it came from (2 or 4 USB). a0, a1, d1, d2 must
| survive; d0, d3, a2 are free.
        .globl  dg_probe_rx
dg_probe_rx:
        lea     -16(%sp), %sp
        movem.l %d1-%d2/%a0-%a1, (%sp)
        moveq   #8, %d0
        cmp.l   %d0, %d1
        blt.s   9f
        moveq   #PORT_USB, %d0
        cmp.l   %d0, %d2
        beq.s   1f
        moveq   #4, %d0
        cmp.l   %d0, %d2
        bne.s   9f
1:      lea     probe_hdr, %a2
        moveq   #6, %d3
2:      move.b  (%a0)+, %d0
        cmp.b   (%a2)+, %d0
        bne.s   9f
        subq.l  #1, %d3
        bne.s   2b
        move.l  %d1, %d0
        subq.l  #7, %d0
        moveq   #-9, %d3
        cmp.b   0(%a0,%d0.l), %d3
        bne.s   9f
        bsr.w   diag_rx
9:      movem.l (%sp), %d1-%d2/%a0-%a1
        lea     16(%sp), %sp
        lea     OSA_40207AE6, %a3       | the instruction this replaced
        rts

diag_rx:
        lea     -32(%sp), %sp
        movem.l %d2-%d7/%a2-%a3, (%sp)
        lea     rq, %a3
        lea     1(%a3), %a1
        moveq   #RQ_MAX, %d1
        bsr.w   unpack7
        move.l  %d0, %d5
        moveq   #3, %d1
        cmp.l   %d1, %d5
        blt.w   99f
        lea     rp, %a2
        move.b  1(%a3), (%a2)
        move.b  2(%a3), 1(%a2)
        moveq   #0, %d2
        move.b  3(%a3), %d2
        move.l  %d2, %d0
        bset    #7, %d0
        move.b  %d0, 2(%a2)
        clr.b   3(%a2)
        lea     4(%a2), %a1
        subq.l  #C_HELLO, %d2
        beq.s   10f
        subq.l  #C_PEEK - C_HELLO, %d2
        beq.s   30f
        moveq   #2, %d0
        move.b  %d0, 3(%a2)
        bra.w   80f

10:     moveq   #PROTO, %d0
        move.w  %d0, (%a1)+
        move.l  OSA_4058E8D4, (%a1)+
        lea     probe_tag, %a0
11:     move.b  (%a0)+, %d0
        move.b  %d0, (%a1)+
        bne.s   11b
        bra.w   80f

30:     moveq   #9, %d1
        cmp.l   %d1, %d5
        blt.s   39f
        move.l  4(%a3), %d3
        moveq   #0, %d4
        move.w  8(%a3), %d4
        beq.s   39f
        cmpi.l  #PEEK_MAX, %d4
        bhi.s   39f
        lea     peek_ranges, %a0
        moveq   #NRANGES, %d2
31:     move.l  %d3, %d1
        sub.l   (%a0), %d1
        bcs.s   32f
        add.l   %d4, %d1
        move.l  4(%a0), %d0
        sub.l   (%a0), %d0
        cmp.l   %d0, %d1
        bls.s   33f
32:     addq.l  #8, %a0
        subq.l  #1, %d2
        bne.s   31b
        bra.s   39f
33:     move.l  %d3, (%a1)+
        movea.l %d3, %a0
34:     move.b  (%a0)+, %d0
        move.b  %d0, (%a1)+
        subq.l  #1, %d4
        bne.s   34b
        bra.s   80f
39:     moveq   #1, %d0
        move.b  %d0, 3(%a2)

80:     move.l  %a1, %d0
        sub.l   %a2, %d0
        movea.l %a2, %a0
        lea     tx+6, %a1
        bsr.w   pack7
        lea     tx, %a0
        move.l  probe_hdr, %d1
        move.l  %d1, (%a0)
        move.w  probe_hdr+4, %d1
        move.w  %d1, 4(%a0)
        addq.l  #6, %d0
        moveq   #-9, %d1
        move.b  %d1, 0(%a0,%d0.l)
        addq.l  #1, %d0
        pea     2.w
        clr.l   -(%sp)
        move.l  %d0, -(%sp)
        pea     tx
        jsr     OSA_401233F2            | SYSEX_SEND(buf, len, abort*, port)
        lea     16(%sp), %sp
99:     movem.l (%sp), %d2-%d7/%a2-%a3
        lea     32(%sp), %sp
        rts

| unpack7(a0 src, d0 len, a1 dst, d1 room) -> d0 bytes out. MidiRpc's
| packing: each group of up to 7 bytes follows a byte whose bit 6-k is byte
| k's bit 7.
unpack7:
        lea     -16(%sp), %sp
        movem.l %d2-%d5, (%sp)
        move.l  %d0, %d2                | bytes left
        moveq   #0, %d3                 | bytes out
1:      tst.l   %d2
        beq.s   9f
        moveq   #0, %d4
        move.b  (%a0)+, %d4             | the group's top bits
        subq.l  #1, %d2
        moveq   #7, %d0
2:      tst.l   %d2
        beq.s   9f
        add.l   %d4, %d4                | this byte's top bit to bit 7
        move.b  (%a0)+, %d5
        subq.l  #1, %d2
        bclr    #7, %d5
        btst    #7, %d4
        beq.s   3f
        bset    #7, %d5
3:      cmp.l   %d1, %d3
        bcc.s   4f                      | no room: drop it
        move.b  %d5, (%a1)+
        addq.l  #1, %d3
4:      subq.l  #1, %d0
        bne.s   2b
        bra.s   1b
9:      move.l  %d3, %d0
        movem.l (%sp), %d2-%d5
        lea     16(%sp), %sp
        rts

| pack7(a0 src, d0 len, a1 dst) -> d0 bytes out.
pack7:
        lea     -16(%sp), %sp
        movem.l %d2-%d4/%a2, (%sp)
        move.l  %a1, %d4                | where the output starts
1:      tst.l   %d0
        beq.s   9f
        movea.l %a1, %a2                | the group's header byte
        addq.l  #1, %a1
        moveq   #0, %d2                 | header
        moveq   #0x40, %d3              | its bit for this byte
2:      move.b  (%a0)+, %d1
        btst    #7, %d1
        beq.s   3f
        or.l    %d3, %d2
3:      bclr    #7, %d1
        move.b  %d1, (%a1)+
        subq.l  #1, %d0
        beq.s   4f
        lsr.l   #1, %d3
        bne.s   2b
4:      move.b  %d2, (%a2)
        bra.s   1b
9:      move.l  %a1, %d0
        sub.l   %d4, %d0
        movem.l (%sp), %d2-%d4/%a2
        lea     16(%sp), %sp
        rts


        .balign 4
peek_ranges:
        .long   0x40000000, 0x48000000  | DDR
        .long   0x80000000, 0x80010000  | the on-chip SRAM
        .long   AUD_RX, AUD_TX + AUD_N  | the SSI0 audio windows
probe_hdr:
        .byte   0xF0, 0x00, 0x20, 0x3C, 0x7D, 0x00
        .balign 4
        .globl  dg_probe_tag
dg_probe_tag:
probe_tag:
        .ascii  "DG "
        .asciz  XSTR(DG_BUILD)
        .balign 4

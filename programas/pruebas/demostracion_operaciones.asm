      MOV A,0x05
      OUT

      MOV [0xF0],A
      MOV A,0
      ADD
      MOV [0xF1],A
      MOV B,0xFF
      MOV A,[0xF0]
      XOR
      MOV B,[0xF1]
      OUT

      MOV [0xF0],A
      MOV A,0
      ADD
      MOV [0xF1],A
      MOV B,0xFF
      MOV A,[0xF0]
      XOR
      MOV B,[0xF1]
      OUT

      MOV B,0x03
      OUT

      MOV [0xF0],A
      MOV A,0xFF
      XOR
      MOV [0xF1],A
      MOV B,[0xF1]
      MOV A,[0xF0]
      OUT

      ADD
      OUT

      MOV [0xF0],A
      MOV A,0
      ADD
      MOV [0xF1],A
      MOV B,[0xF0]
      MOV A,0
      SUB
      MOV B,[0xF1]
      OUT

      MOV B,0x0F
      OUT

      AND
      OUT

      MOV [0xF0],A
      MOV A,0
      SUB
      MOV [0xF1],A
      MOV B,[0xF1]
      MOV A,[0xF0]
      OUT

      OR
      OUT

      XOR
      OUT

      MOV B,0x0E
      OUT

      SUB
      OUT

      HLT

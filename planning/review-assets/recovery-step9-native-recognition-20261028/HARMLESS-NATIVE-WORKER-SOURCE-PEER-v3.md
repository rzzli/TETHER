# Native worker v3: one-line source clearance

Source `11490803ed4a3e68937c7bf685f31a042752f3c8681347c67f2bf4cd46721be6` differs from c22 only by `expected = utf8(expected_w)` after64lowercasehex validation. The ASCII hash bytes are preserved through the existing strict converter; implicit wchar-to-char iterator construction is removed. No new API family or behavior/policy change is introduced. /MD and /W4 /WX remain.

**CLEAR for source delta only.** No compiler/API/worker ran; successful compilation and any execution remain separate gates. Failed prior source/build stay preserved.

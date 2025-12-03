import os
import math
from pathlib import Path

# --- Instructions ---
# Export a directory listing from your TRS-80 disk image into a text file called DIR.TXT and place it into this
# script's directory. The listing can be in any format as long as there are lines start with the filename/extension
# of programs you would like to be included. If a /CMD or /BAS is found in a line, all text prior to that will be
# taken as the filename. The name of the file will be displayed in a header when selected in the resulting menu.bas.
# If you wish to include custom text for that label, append ** followed by the text to the line anywhere after /CMD
# or /BAS, but, keep in mind that all text following this will be used for the label. It is best practice to output
# a directory listing to a DIR.TXT and edit the file, entering ** at the end of the DIR line you wish to customize.
#
# Example DIR.TXT:
#
# Drive :1 GAMES1   08/27/13 203H1 Free=  182.0/ 1624.0 Fi=123/240
# Filespec      Attrib  LRL #Recs EOF DE File Size  MOD Date Time
# ----------------------------------------------------------------
# DSHIP/CMD    ----- AL 256    45 127  1 s=   12.0 **Death Dreadnaught, 1980, Programmer's Guild
# ESCAPE/CMD   ----- AL 256    68 127  1 s=   17.0 **Escape from Traam, 1980, Other-Ventures
#
# Note that any line without a /CMD or /BAS will be ignored, as will any files with other extensions.
#
# Once your DIR.TXT is in-place, run this script with Python 3. The resulting MENU.BAS will be created in the same
# directory. Transfer this file to your TRS-80 disk image and run it with BASIC. You can use the LS-DOS version (80x24,
# 8 columns, no SPEED commands) by changing the lsdos_mode variable below to True. The default is False for 
# LDOS/MultiDOS (64x15, 7 columns, SPEED commands). The resulting menu will display all /CMD files first, followed by
# all /BAS files, each sorted alphabetically. # Use ,(<) and .(>) to change pages, Left/Right arrows to move left and
# right, and Up/Down arrows to move up and down. Press Enter to run the selected program.
#
# Programmer's Note: This is obviously a highly specialized script for a niche use case. I tussled with the idea of
# generalizing it and wrapping it nicely with a bow, but I've decided to leave it as-is and put it out there. I'm
# happily using it daily to play games and launch applications on my TRS-80 Model 4D. I went through several revisions
# before I posted what you see here. It was continually refined for stability and needed to meet several requirements:
# 1) It should be responsive and quick to navigate, 2) It should rely on disk access as little as possible, 3) It
# should be capable of outputting either an LDOS or LSDOS version without the need to change the input file, 4) It
# should leave room for basic programs that need to run, and, so most very importantly, 5) It should give me details
# not found when running a program listing.
#
# --- Version ---
code_version = "2.6.0"

# --- Environment toggle ---
lsdos_mode = False  # True for LS-DOS (80x24, 8 cols, no SPEED commands); False for LDOS/MultiDOS (64x15, 7 cols, SPEED commands)

# --- Paths ---
base_path = Path(__file__).resolve().parent

dir_file = os.path.join(base_path, "dir.txt")
out_file = os.path.join(base_path, "menu.bas")

# --- Collect entries ---
raw_entries = []
with open(dir_file, "r", encoding="latin-1") as f:
    for line in f:
        s = line.strip()
        if not s or "/" not in s:
            continue
        parts = s.split()
        name_ext = parts[0]
        if "/" not in name_ext:
            continue
        name, ext = name_ext.split("/", 1)
        ext = ext.upper()
        if ext not in ("BAS", "CMD"):
            continue
        pretty = name.capitalize()
        label = ""
        if "**" in line:
            label = line.split("**", 1)[1].strip()
        raw_entries.append((pretty, ext, label))

# --- Geometry ---
max_width = 80 if lsdos_mode else 64
cols = 8 if lsdos_mode else 7
rows_total = 24 if lsdos_mode else 15
entry_start_row = 2
entry_end_row = rows_total - 3
rows_entries = entry_end_row - entry_start_row + 1
col_step = max_width // cols
epp = cols * rows_entries

# --- Separate and sort ---
cmd_entries = sorted([e for e in raw_entries if e[1] == "CMD"], key=lambda x: x[0].lower())
bas_entries = sorted([e for e in raw_entries if e[1] == "BAS"], key=lambda x: x[0].lower())

# --- Concatenate with enforced page break ---
entries = []
entries.extend(cmd_entries)
if cmd_entries:
    remainder = len(cmd_entries) % epp
    if remainder != 0:
        pad = epp - remainder
        entries.extend([("", "", "")] * pad)
entries.extend(bas_entries)

bas_names = [disp for disp, ext, label in bas_entries]

# Labels aligned to entries (fallback to short name if no long label)
labels = []
for disp, ext, label in entries:
    if disp:
        labels.append(label.strip() if label.strip() else disp)
    else:
        labels.append("")

# Page counts
cmd_total_pages = math.ceil(len(cmd_entries) / epp) if cmd_entries else 0
bas_total_pages = math.ceil(len(bas_entries) / epp) if bas_entries else 0
total_pages = (cmd_total_pages if cmd_total_pages else 0) + (bas_total_pages if bas_total_pages else 0)
if total_pages == 0:
    total_pages = 1

# --- Line ranges ---
DATA_START = 9000
LABEL_DATA_START = 9200
FLIP_LEFT = 9500
FLIP_RIGHT = 9600

lines = []
def add(s): lines.append(s)

# --- Early setup ---
add("5 REM --- Environment v" + code_version + " ---")
add("10 REM --- Slim Visual Menu ---")
add("15 CLEAR 2000")
if not lsdos_mode:
    add('20 CMD "SYSTEM (FAST)"')

hd_len = 65 if lsdos_mode else 48
add('23 HD$=""')
add("25 FOR I=1 TO " + str(hd_len) + ":HD$=HD$+CHR$(131):NEXT I")
add('26 FOR I = 1 TO 47:HB$=HB$+CHR$(131):NEXT I')

if lsdos_mode:
    add("29 DIM MENU$(" + str(len(entries)) + ")")
add("28 DIM TL$(" + str(len(entries)) + ")")

add("30 TP=" + str(total_pages) + ":PG=1:CX=1:CY=1:SEL=1:NB=" + str(len(bas_names)))
add("35 CP=" + str(cmd_total_pages) + ":BP=" + str(bas_total_pages))

# --- Load labels BEFORE first render ---
add("90 REM --- Load labels ---")
add("91 RESTORE " + str(LABEL_DATA_START))
add("92 FOR I=1 TO " + str(len(entries)))
add("93 READ TL$(I)")
add("94 NEXT I")
add("100 GOSUB 180")
add("101 REM --- Initial overlay ---")
add("102 BASE=(PG-1)*" + str(epp))
add("103 SEL=BASE+((CY-1)*" + str(cols) + ")+CX")
add('104 IF TL$(SEL)<>"" THEN PRINT @1,TL$(SEL)+" "')
add('105 IF TL$(SEL)<>"" THEN GOSUB 130')
add("106 GOSUB 400")
add("110 GOTO 300")
add('130 SL=LEN(TL$(SEL))+2')
add("135 PRINT @SL,MID$(HB$,SL);")
add("140 RETURN")
# --- Page renderer ---
add("180 CLS")
for p in range(1, total_pages + 1):
    add("18" + str(p) + " IF PG=" + str(p) + " THEN GOSUB " + str(1000 * p))
add("189 RETURN")

# --- Page blocks ---
for p in range(1, total_pages + 1):
    base = (p - 1) * epp
    add(str(1000 * p) + " REM --- Page " + str(p) + " ---")
    ln = 1000 * p + 1

    page_slice = entries[base:base + epp]
    actual_entries = sum(1 for disp, ext, label in page_slice if disp)
    rows_on_page = max(1, math.ceil(actual_entries / cols))
    if actual_entries == 0:
        last_col = 1
    else:
        last_row_entries = actual_entries % cols
        last_col = cols if last_row_entries == 0 else last_row_entries

    add(str(ln) + " PR=" + str(rows_on_page)); ln += 1
    add(str(ln) + " PC=" + str(last_col)); ln += 1

    section = '" Command Files"' if (cmd_total_pages and p <= cmd_total_pages) else 'CHR$(131)+CHR$(131)+" Basic Files"'
    add(str(ln) + ' PRINT @1,HD$+'+section); ln += 1
    add(str(ln) + ' PRINT @' + str(max_width + 1) + ',""'); ln += 1

    for rr in range(rows_entries):
        row_cmds = []
        for cc in range(cols):
            idx = base + rr * cols + cc
            if idx < len(entries):
                disp, ext, label = entries[idx]
                if disp:
                    addr = (entry_start_row + rr) * max_width + cc * col_step + 1
                    if lsdos_mode:
                        add(str(ln) + f' PRINT @{addr},"{disp}"'); ln += 1
                        add(str(ln) + f' MENU$({idx+1})="{disp}"'); ln += 1
                    else:
                        row_cmds.append(f'@{addr},"{disp}"')
        if row_cmds and not lsdos_mode:
            add(str(ln) + " PRINT " + ",".join(row_cmds)); ln += 1

    bottom_spacer_addr = (rows_total - 2) * max_width
    add(str(ln) + ' PRINT @' + str(bottom_spacer_addr) + ',""'); ln += 1

    if p <= cmd_total_pages and cmd_total_pages > 0:
        local_page = p; total_local = cmd_total_pages
    else:
        local_page = p - cmd_total_pages if bas_total_pages > 0 else 1
        total_local = bas_total_pages if bas_total_pages > 0 else 1

    right = f' "Page {local_page} of {total_local} " + HD$ + CHR$(131) + CHR$(131)'
    footer_addr = (rows_total - 2) * max_width if lsdos_mode else (rows_total - 1) * max_width
    add(str(ln) + " PRINT @" + str(footer_addr) + "," + right); ln += 1
    add(str(1000 * p + (300 if lsdos_mode else 90)) + " RETURN")

# --- Cursor draw/erase with clamp ---
add("400 REM --- Draw cursor ---")
add("405 IF CY>PR THEN CY=PR")
add("406 IF CY=PR AND CX>PC THEN CX=PC")
add("410 L=(" + str(entry_start_row) + "+(CY-1))*" + str(max_width) +
    "+(CX-1)*" + str(col_step))
if lsdos_mode:
    add('420 PRINT @L,"";:RETURN')
else:
    add('420 PRINT @L,CHR$(143);:RETURN')
    add("460 REM --- Erase cursor ---")
    add("470 L=(" + str(entry_start_row) + "+(CY-1))*" + str(max_width) +
        "+(CX-1)*" + str(col_step))
    add('480 PRINT @L," ";:RETURN')

# --- Input loop ---
add('300 K$=INKEY$:IF K$="" THEN 300')
if not lsdos_mode:
    add("305 GOSUB 460")
add("310 IF K$=CHR$(8) AND CX>1 THEN CX=CX-1:GOTO 380")
add("311 IF K$=CHR$(8) AND CX=1 THEN GOSUB " + str(FLIP_LEFT))
add("320 IF K$=CHR$(9) AND CX<" + str(cols) + " THEN CX=CX+1:GOTO 380")
add("321 IF K$=CHR$(9) AND CX=" + str(cols) + " THEN GOSUB " + str(FLIP_RIGHT))
add("330 IF K$=CHR$(10) THEN CY=CY+1:IF CY>" + str(rows_entries) + " THEN CY=1")
add("340 IF K$=CHR$(11) OR K$=CHR$(91) THEN CY=CY-1:IF CY<1 THEN CY=" + str(rows_entries))

# --- Global SEL calculation (for up/down paths) ---
add("350 BASE=(PG-1)*" + str(epp))
add("351 IF CY>PR THEN CY=PR")
add("352 IF CY=PR AND CX>PC THEN CX=PC")
add("353 SEL=BASE+((CY-1)*" + str(cols) + ")+CX")
add('355 IF TL$(SEL)<>"" THEN PRINT @1,TL$(SEL)+" "')
add('356 IF TL$(SEL)<>"" THEN GOSUB 130')

add('360 IF K$="," THEN PG=PG-1')
add('361 IF PG<1 THEN PG=TP')
add('362 IF K$="," THEN CX=1:CY=1:SEL=1:GOSUB 180:GOSUB 400:GOTO 300')
add('365 IF K$="." THEN PG=PG+1')
add('366 IF PG>TP THEN PG=1')
add('367 IF K$="." THEN CX=1:CY=1:SEL=1:GOSUB 180:GOSUB 400:GOTO 300')
add("370 IF K$=CHR$(13) THEN GOSUB 500")

# --- Redraw cursor path (used by left/right jumps) ---
add("380 REM --- Redraw path ---")
add("381 BASE=(PG-1)*" + str(epp))
add("382 IF CY>PR THEN CY=PR")
add("383 IF CY=PR AND CX>PC THEN CX=PC")
add("384 SEL=BASE+((CY-1)*" + str(cols) + ")+CX")
add('385 IF TL$(SEL)<>"" THEN PRINT @1,TL$(SEL)+" "')
add('386 IF TL$(SEL)<>"" THEN GOSUB 130')
add("387 GOSUB 400")
add("390 GOTO 300")

# --- Dispatch ---
add("500 REM --- Dispatch ---")
add("505 BASE=(PG-1)*" + str(epp))
add("506 SEL=BASE+((CY-1)*" + str(cols) + ")+CX")
if lsdos_mode:
    add("510 N$=MENU$(SEL)")
else:
    add("510 L=(" + str(entry_start_row) + "+(CY-1))*" + str(max_width) +
        "+(CX-1)*" + str(col_step) + "+1")
    add('520 N$=""')
    add("530 FOR I=0 TO " + str(col_step - 2))
    add("540 C=PEEK(15360+L+I)")
    add("550 IF C=32 THEN 570")
    add("560 N$=N$+CHR$(C)")
    add("570 NEXT I")

add("580 RESTORE " + str(DATA_START))
add("590 FOR I=1 TO NB")
add("600 READ B$")
if lsdos_mode:
    add('610 IF N$=B$ THEN CLS:RUN N$:RETURN')
else:
    add('610 IF N$=B$ THEN CMD "SYSTEM (SLOW)":CLS:RUN N$:RETURN')
add("620 NEXT I")
if lsdos_mode:
    add('640 CLS:SYSTEM "RUN "+N$:RETURN')
else:
    add('630 CMD "SYSTEM (SLOW)"')
    add('635 CLS')
    add('640 CMD N$:GOTO 800')
    add('800 CMD "SYSTEM (FAST)"')
    add("810 GOTO 300")

# --- DATA block for BAS names (dispatch only) ---
line_num = DATA_START
chunk = []
for i, name in enumerate(bas_names, start=1):
    chunk.append(name)
    if len(chunk) == 8 or i == len(bas_names):
        add(str(line_num) + " DATA " + ",".join('"' + n + '"' for n in chunk))
        line_num += 1
        chunk = []

# --- DATA block for labels (CMD+BAS, blanks included as "") ---
line_num = LABEL_DATA_START
chunk = []
for i, label in enumerate(labels, start=1):
    chunk.append(label)
    if len(chunk) == 4 or i == len(labels):
        add(str(line_num) + " DATA " + ",".join('"' + l + '"' for l in chunk))
        line_num += 1
        chunk = []

# --- Page flip subroutines ---
add(str(FLIP_LEFT) + " REM --- Left edge page flip ---")
add(str(FLIP_LEFT + 10) + " PG=PG-1")
add(str(FLIP_LEFT + 15) + " IF PG<1 THEN PG=TP")
add(str(FLIP_LEFT + 20) + " CX=" + str(cols))
add(str(FLIP_LEFT + 25) + " SEL=CY-1")
add(str(FLIP_LEFT + 30) + " SEL=SEL*" + str(cols))
add(str(FLIP_LEFT + 35) + " SEL=SEL+CX")
add(str(FLIP_LEFT + 40) + " GOSUB 180")
# recompute SEL and draw overlay first
add(str(FLIP_LEFT + 46) + " BASE=(PG-1)*" + str(epp))
add(str(FLIP_LEFT + 47) + " IF CY>PR THEN CY=PR")
add(str(FLIP_LEFT + 48) + " IF CY=PR AND CX>PC THEN CX=PC")
add(str(FLIP_LEFT + 49) + " SEL=BASE+((CY-1)*" + str(cols) + ")+CX")
add(str(FLIP_LEFT + 50) + ' IF TL$(SEL)<>"" THEN PRINT @1,TL$(SEL)+" "')
add(str(FLIP_LEFT + 55) + ' IF TL$(SEL)<>"" THEN GOSUB 130')
# cursor draw last
add(str(FLIP_LEFT + 60) + " GOSUB 400")
add(str(FLIP_LEFT + 70) + " GOTO 300")

add(str(FLIP_RIGHT) + " REM --- Right edge page flip ---")
add(str(FLIP_RIGHT + 10) + " PG=PG+1")
add(str(FLIP_RIGHT + 15) + " IF PG>TP THEN PG=1")
add(str(FLIP_RIGHT + 20) + " CX=1")
add(str(FLIP_RIGHT + 25) + " SEL=CY-1")
add(str(FLIP_RIGHT + 30) + " SEL=SEL*" + str(cols))
add(str(FLIP_RIGHT + 35) + " SEL=SEL+CX")
add(str(FLIP_RIGHT + 40) + " GOSUB 180")
# recompute SEL and draw overlay first
add(str(FLIP_RIGHT + 46) + " BASE=(PG-1)*" + str(epp))
add(str(FLIP_RIGHT + 47) + " IF CY>PR THEN CY=PR")
add(str(FLIP_RIGHT + 48) + " IF CY=PR AND CX>PC THEN CX=PC")
add(str(FLIP_RIGHT + 49) + " SEL=BASE+((CY-1)*" + str(cols) + ")+CX")
add(str(FLIP_RIGHT + 50) + ' IF TL$(SEL)<>"" THEN PRINT @1,TL$(SEL)+" "')
add(str(FLIP_RIGHT + 55) + ' IF TL$(SEL)<>"" THEN GOSUB 130')
# cursor draw last
add(str(FLIP_RIGHT + 60) + " GOSUB 400")
add(str(FLIP_RIGHT + 70) + " GOTO 300")

# --- Write out the BASIC program ---
with open(out_file, "w", encoding="latin-1") as f:
    for l in lines:
        f.write(l + "\n")

print("Menu written to " + out_file + " with " +
      str(len(entries)) + " entries across " +
      str(total_pages) + " pages.")
"""Deterministic working-draft Markdown -> combined main/supplement PDF.

Presentation only. Existing figure PDFs are overlaid as vectors by pypdf; no
source-data, evaluator fact or frozen result is opened or changed. The external
PDF-operation marker must succeed once before the first --build for this output.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import html
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
SOURCES = (PAPER / "manuscript.md", PAPER / "supplement.md")
OUTPUT = PAPER / "tether-source-reporting-preprint.pdf"
BUILD = PAPER / "TETHER-PDF-BUILD.json"
RESULTS = PAPER / "results/ARTIFACTS.json"
RESULTS_SHA = "84d4a31e842d3085133d384429729ef2501425d33bf2b92f65d9c64699a87428"
POPLER = Path("C:/Users/zzric/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.EXE")
MARKER = "C:/Users/zzric/.codex/plugins/cache/openai-primary-runtime/pdf/26.1026.10807/skills/pdf/container_tools/mark_artifact_operation_started.mjs"
FONTS = {"Body": Path("C:/Windows/Fonts/arial.ttf"), "Body-Bold": Path("C:/Windows/Fonts/arialbd.ttf"),
         "Body-Italic": Path("C:/Windows/Fonts/ariali.ttf"), "Body-BoldItalic": Path("C:/Windows/Fonts/arialbi.ttf"),
         "Mono": Path("C:/Windows/Fonts/consola.ttf")}
WIDTH, HEIGHT, LEFT, BOTTOM, CONTENT_W, CONTENT_H = 612, 792, 54, 52, 504, 686


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize_typography(value):
    # Fixed typography only; content and source files are never rewritten.
    return value.translate(str.maketrans({"\u2010":"-", "\u2011":"-", "\u2012":"-", "\u2013":"-", "\u2014":" - ",
        "\u2212":"-", "\u2018":"'", "\u2019":"'", "\u201c":'"', "\u201d":'"', "\u00a0":" "}))


@dataclass
class Block:
    kind: str
    text: str
    source: str
    line: int
    level: int = 0
    rows: list | None = None
    target: str | None = None


def split_cells(line):
    return [x.strip().replace("\\|", "|") for x in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def parse_markdown(text, source):
    lines = normalize_typography(text).splitlines()
    definitions = {}
    for line in lines:
        found = re.fullmatch(r"\[([^\]]+)\]:\s*(https?://\S+)\s*", line.strip())
        if found:
            definitions[found[1]] = found[2]
    blocks, i = [], 0
    while i < len(lines):
        line, start = lines[i], i+1
        if not line.strip() or re.fullmatch(r"\[([^\]]+)\]:\s*(https?://\S+)\s*", line.strip()):
            i += 1
            continue
        if line.startswith("```"):
            body=[];i+=1
            while i<len(lines) and not lines[i].startswith("```"):
                body.append(lines[i]);i+=1
            need(i<len(lines),f"Unclosed code fence: {source}:{start}")
            blocks.append(Block("code","\n".join(body),source,start));i+=1;continue
        heading=re.match(r"^(#{1,6})\s+(.+)$",line)
        if heading:
            blocks.append(Block("heading",heading[2],source,start,level=len(heading[1])));i+=1;continue
        image=re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)\s*",line.strip())
        if image:
            blocks.append(Block("figure",image[1],source,start,target=image[2]));i+=1;continue
        if i+1<len(lines) and "|" in line and all(re.fullmatch(r":?-{3,}:?",x) for x in split_cells(lines[i+1])):
            rows=[split_cells(line)];i+=2
            while i<len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_cells(lines[i]));i+=1
            need(all(len(row)==len(rows[0]) for row in rows),f"Ragged table: {source}:{start}")
            blocks.append(Block("table","",source,start,rows=rows));continue
        bullet=re.match(r"^\s*(?:[-*+]\s+|\d+\.\s+)(.+)$",line)
        if bullet:
            blocks.append(Block("bullet",bullet[1],source,start));i+=1;continue
        if re.fullmatch(r"\s*[-*_]{3,}\s*",line):
            blocks.append(Block("rule","",source,start));i+=1;continue
        body=[line.strip()];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r"^(#{1,6})\s|^!\[|^```|^\s*[-*+]\s|^\s*\d+\.\s",lines[i]):
            if i+1<len(lines) and "|" in lines[i] and all(re.fullmatch(r":?-{3,}:?",x) for x in split_cells(lines[i+1])):
                break
            body.append(lines[i].strip());i+=1
        blocks.append(Block("paragraph"," ".join(body),source,start))
    return blocks, definitions


def inline_markup(text, definitions, references, *, citations=True):
    saved=[]
    def save(markup):
        key=f"ZZINLINEPLACEHOLDER{len(saved)}ZZ"
        saved.append(markup)
        return key
    text=re.sub(r"`([^`]+)`",lambda m:save('<font name="Mono" size="9">'+html.escape(m[1])+"</font>"),text)
    text=re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+|[^\s)]+\.md(?:#[^\s)]*)?)\)",
        lambda m:save('<link href="'+html.escape(m[2],quote=True)+'" color="#245F7A">'+html.escape(m[1])+"</link>"),text)
    def reference_link(match):
        label,key=match[1],match[2]
        if key not in definitions:
            return match[0]
        return save('<link href="'+html.escape(definitions[key],quote=True)+'" color="#245F7A">'+html.escape(label)+"</link>")
    text=re.sub(r"\[([^\]]+)\]\[([^\]]+)\]",reference_link,text)
    text=re.sub(r"https?://[^\s<>]+",lambda m:save('<link href="'+html.escape(m[0].rstrip(".,;"),quote=True)+'" color="#245F7A">'+html.escape(m[0])+"</link>"),text)
    if citations:
        text=re.sub(r"\[(\d+)\]",lambda m:save('<link href="#reference-'+m[1]+'" color="#245F7A">['+m[1]+"]</link>") if int(m[1]) in references else m[0],text)
    text=html.escape(text)
    text=re.sub(r"\*\*(.+?)\*\*",r"<b>\1</b>",text)
    text=re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)",r"<i>\1</i>",text)
    text=re.sub(r"(?<!\w)_([^_]+)_(?!\w)",r"<i>\1</i>",text)
    for i,value in enumerate(saved):
        text=text.replace(f"ZZINLINEPLACEHOLDER{i}ZZ",value)
    return text


def inputs():
    raw={path.name:path.read_bytes() for path in SOURCES}
    texts={name:value.decode("utf-8-sig") for name,value in raw.items()}
    need(digest(RESULTS.read_bytes())==RESULTS_SHA,"Verified result manifest changed")
    manifest=json.loads(RESULTS.read_text(encoding="utf-8"))
    parsed=[];definitions={}
    for path in SOURCES:
        blocks,defs=parse_markdown(texts[path.name],path.name)
        parsed.extend(blocks);definitions.update(defs)
    references={int(m[1]) for b in parsed if b.kind=="paragraph" and (m:=re.match(r"^\[(\d+)\]\s",b.text))}
    figures={}
    for block in parsed:
        if block.kind!="figure":continue
        target=(PAPER/block.target).resolve()
        need(target.is_relative_to(PAPER/"results/figures") and target.suffix.lower()==".pdf","Only local verified vector PDF figure assets are supported")
        logical=target.relative_to(PAPER/"results").as_posix()
        proof=manifest["tables_and_outputs"][logical]
        need(digest(target.read_bytes())==proof["sha256"] and proof["vector"] is True,"Figure differs from verified result bundle")
        figures[str(target)]=dict(path=target.relative_to(ROOT).as_posix(),sha256=proof["sha256"],data=target.read_bytes())
        need(digest(figures[str(target)]["data"])==proof["sha256"],"Figure changed while retaining verified bytes")
    need(parsed and references,"Manuscript and numbered references required")
    return raw,parsed,definitions,references,figures


def visible_text(text):
    text=re.sub(r"`([^`]+)`",r"\1",text)
    text=re.sub(r"\[([^\]]+)\]\(([^)]+)\)",r"\1",text)
    text=re.sub(r"\[([^\]]+)\]\[[^\]]+\]",r"\1",text)
    text=re.sub(r"\*\*(.+?)\*\*",r"\1",text)
    text=re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)",r"\1",text)
    return re.sub(r"(?<!\w)_([^_]+)_(?!\w)",r"\1",text)


def text_key(text):
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",text))


def ordered_retention(units,observations):
    """Exact visible text per ordered source unit; repeated table headers only."""
    need([x["id"] for x in units]==list(range(len(units))),"Invalid expected unit sequence")
    observed_order=[];parts={};header_repeats=0
    for event in observations:
        ident=event["id"]
        need(0<=ident<len(units),"Unknown visible source unit")
        need(text_key(event["text"]),"Empty visible source span")
        if units[ident]["table_header"] and ident in parts:
            need(text_key(event["text"])==text_key(units[ident]["text"]),"Changed repeated table header")
            header_repeats+=1;continue
        if not observed_order or observed_order[-1]!=ident:
            need(ident not in observed_order,"Duplicated/reordered source unit")
            observed_order.append(ident)
        parts.setdefault(ident,[]).append(event["text"])
    need(observed_order==list(range(len(units))),"Omitted/reordered source units")
    for unit in units:
        need(text_key("".join(parts[unit["id"]]))==text_key(unit["text"]),
             "Visible source text changed or omitted in unit "+str(unit["id"]))
    return dict(expected_units=len(units),observed_units=len(observed_order),table_header_repeat_draws=header_repeats,
        missing_units=0,duplicate_or_reordered_units=0,changed_visible_units=0,
        normalization="NFKC and layout whitespace only, after declared source typography substitutions")


def visible_spans(reader):
    observations=[]
    for page_number,page in enumerate(reader.pages,1):
        stack=[]
        def operation(operator,operands,cm,tm):
            if operator==b"BDC" and operands and isinstance(operands[-1],dict) and "/MCID" in operands[-1]:
                event=dict(id=int(operands[-1]["/MCID"]),page=page_number,text="")
                observations.append(event);stack.append(event)
            elif operator==b"EMC" and stack:
                stack.pop()
        def text(value,cm,tm,font,size):
            if stack:stack[-1]["text"]+=value
        page.extract_text(visitor_operand_before=operation,visitor_text=text)
    return [x for x in observations if text_key(x["text"])]


def retention_regressions():
    units=[dict(id=0,text="Repeated repeated words 12/12",table_header=False),dict(id=1,text="Table cell 40/48",table_header=False),
           dict(id=2,text="Figure 2. Caption survives",table_header=False),dict(id=3,text="Reference [13] URL",table_header=False)]
    correct=[dict(id=x["id"],text=x["text"]) for x in units]
    ordered_retention(units,correct)
    mutations={"omission":correct[1:],"duplicate":correct[:1]+correct,"reorder":[correct[1],correct[0],*correct[2:]],
        "repeated_word_loss":[dict(id=0,text="Repeated words 12/12"),*correct[1:]],
        "table_cell_change":[correct[0],dict(id=1,text="Table cell 40/40"),*correct[2:]],
        "caption_loss":[*correct[:2],dict(id=2,text="Figure 2."),correct[3]]}
    for label,events in mutations.items():
        try:ordered_retention(units,events)
        except ValueError:continue
        raise ValueError("Retention regression was not detected: "+label)
    return dict(status="PASS",positive=1,negative_cases=list(mutations))


def render_once(blocks,definitions,references,figures,font_bytes):
    from reportlab import rl_config
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import BaseDocTemplate,Frame,PageTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,KeepTogether,Flowable,HRFlowable
    from pypdf import PdfReader,PdfWriter,Transformation
    rl_config.invariant=1
    for name,data in font_bytes.items():
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,io.BytesIO(data)))
    pdfmetrics.registerFontFamily("Body",normal="Body",bold="Body-Bold",italic="Body-Italic",boldItalic="Body-BoldItalic")
    body=ParagraphStyle("body",fontName="Body",fontSize=10.3,leading=14.2,spaceAfter=8,splitLongWords=True,allowWidows=0,allowOrphans=0)
    styles={"body":body,"title":ParagraphStyle("title",parent=body,fontName="Body-Bold",fontSize=19,leading=23,spaceAfter=13,keepWithNext=True),
        "h2":ParagraphStyle("h2",parent=body,fontName="Body-Bold",fontSize=13,leading=17,spaceBefore=13,spaceAfter=7,keepWithNext=True),
        "h3":ParagraphStyle("h3",parent=body,fontName="Body-Bold",fontSize=11.2,leading=15,spaceBefore=9,spaceAfter=5,keepWithNext=True),
        "caption":ParagraphStyle("caption",parent=body,fontSize=9,leading=12,spaceBefore=6,spaceAfter=10),
        "reference":ParagraphStyle("reference",parent=body,fontSize=9,leading=12,spaceAfter=7),
        "cell":ParagraphStyle("cell",parent=body,fontSize=8.6,leading=11,spaceAfter=0,spaceBefore=0),
        "cellhead":ParagraphStyle("cellhead",parent=body,fontName="Body-Bold",fontSize=8.6,leading=11,spaceAfter=0,spaceBefore=0),
        "code":ParagraphStyle("code",parent=body,fontName="Mono",fontSize=8.2,leading=11,spaceBefore=4,spaceAfter=8),
        "bullet":ParagraphStyle("bullet",parent=body,leftIndent=12,firstLineIndent=-9,spaceAfter=5)}
    overlays=[];expected=[];block_log=[]
    class TaggedParagraph(Paragraph):
        def __init__(self,*args,unit_id=None,**kwargs):
            self.unit_id=unit_id
            super().__init__(*args,**kwargs)
        def split(self,*args,**kwargs):
            children=super().split(*args,**kwargs)
            for child in children:child.unit_id=self.unit_id
            return children
        def draw(self):
            need(self.unit_id is not None,"Untagged visible paragraph")
            self.canv.addLiteral(f"/Span << /MCID {self.unit_id} >> BDC")
            super().draw()
            self.canv.addLiteral("EMC")
    def tracked(markup,style,plain,block,*,header=False):
        ident=len(expected)
        paragraph=TaggedParagraph(markup,style,unit_id=ident)
        need(text_key(paragraph.getPlainText())==text_key(plain),"Inline formatting changed source-visible text")
        expected.append(dict(id=ident,text=plain,source=block.source,line=block.line,kind=block.kind,table_header=header))
        return paragraph
    class VectorFigure(Flowable):
        def __init__(self,path,width):
            Flowable.__init__(self)
            self.path=path
            source=PdfReader(io.BytesIO(figures[str(path)]["data"]));need(len(source.pages)==1,"One-page figure required")
            box=source.pages[0].mediabox
            self.scale=min(width/float(box.width),390/float(box.height))
            self.width=float(box.width)*self.scale;self.height=float(box.height)*self.scale
        def draw(self):
            x,y=self.canv.absolutePosition(0,0)
            overlays.append(dict(page=self.canv.getPageNumber(),x=x,y=y,width=self.width,height=self.height,scale=self.scale,path=str(self.path)))
    class Document(BaseDocTemplate):
        def afterFlowable(self,flowable):
            if getattr(flowable,"heading_text",None):
                key="section-"+str(len(self._headings))
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(flowable.heading_text,key,level=0,closed=False)
                self._headings.append(flowable.heading_text)
    stream=io.BytesIO()
    doc=Document(stream,pagesize=(WIDTH,HEIGHT),leftMargin=LEFT,rightMargin=54,topMargin=54,bottomMargin=BOTTOM,
        title=next(b.text for b in blocks if b.kind=="heading"),author="",subject="Working research draft; author declarations pending")
    doc._headings=[]
    def page_frame(c,d):
        c.saveState();c.setFont("Body",8);c.setFillColor(colors.HexColor("#526673"))
        c.drawString(LEFT,HEIGHT-30,"TETHER - Working research draft")
        c.drawRightString(WIDTH-LEFT,30,str(d.page))
        c.setStrokeColor(colors.HexColor("#DDE5E8"));c.setLineWidth(.5);c.line(LEFT,HEIGHT-39,WIDTH-LEFT,HEIGHT-39)
        c.restoreState()
    doc.addPageTemplates(PageTemplate(id="article",frames=[Frame(LEFT,BOTTOM,CONTENT_W,CONTENT_H,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=page_frame))
    story=[];figure_index=0;last_source=None
    for block in blocks:
        if last_source and last_source!=block.source:story.append(PageBreak())
        last_source=block.source
        block_log.append(dict(kind=block.kind,source=block.source,line=block.line,text_sha256=digest(block.text.encode()),table_rows=len(block.rows) if block.rows else None))
        if block.kind=="rule":story.append(HRFlowable(width="100%",thickness=.5,color=colors.HexColor("#DDE5E8")));continue
        if block.kind=="figure":
            figure_index+=1
            path=(PAPER/block.target).resolve()
            figure=VectorFigure(path,CONTENT_W)
            figure.hAlign="CENTER"
            caption=(f"Figure {figure_index}. " if not re.match(r"Figure\s+\d",block.text) else "")+block.text
            items=[Spacer(1,8),figure]
            if caption:
                paragraph=tracked(inline_markup(caption,definitions,references),styles["caption"],visible_text(caption),block)
                items.append(paragraph)
            story.append(KeepTogether(items));continue
        if block.kind=="table":
            n=len(block.rows[0]);font=styles["cell"]
            lengths=[max(len(re.sub(r"[`*_]","",row[j])) for row in block.rows) for j in range(n)]
            weights=[max(7,min(48,length))**.65 for length in lengths]
            widths=[CONTENT_W*weight/sum(weights) for weight in weights]
            converted=[]
            for i,row in enumerate(block.rows):
                cells=[]
                for value in row:
                    paragraph=tracked(inline_markup(value,definitions,references),styles["cellhead"] if i==0 else font,visible_text(value),block,header=i==0)
                    cells.append(paragraph)
                converted.append(cells)
            table=Table(converted,colWidths=widths,repeatRows=1,hAlign="LEFT",splitByRow=1,spaceBefore=5,spaceAfter=10)
            table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#ECF2F5")),
                ("LINEBELOW",(0,0),(-1,0),.6,colors.HexColor("#9AAFB9")),("LINEBELOW",(0,1),(-1,-1),.35,colors.HexColor("#DDE5E8")),
                ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
            story.append(table);continue
        kind="title" if block.kind=="heading" and block.level==1 else "h2" if block.kind=="heading" and block.level==2 else "h3" if block.kind=="heading" else "code" if block.kind=="code" else "bullet" if block.kind=="bullet" else "body"
        text=block.text
        reference=re.match(r"^\[(\d+)\]\s",text) if block.kind=="paragraph" else None
        if reference:kind="reference"
        if block.kind=="code":markup=html.escape(text).replace(" ","&#160;").replace("\n","<br/>")
        else:markup=inline_markup(text,definitions,references,citations=not bool(reference))
        if reference:markup='<a name="reference-'+reference[1]+'"/>'+markup
        if block.kind=="bullet":markup="- "+markup
        plain=("- " if block.kind=="bullet" else "")+(text if block.kind=="code" else visible_text(text))
        paragraph=tracked(markup,styles[kind],plain,block)
        if block.kind=="heading":paragraph.heading_text=text
        story.append(paragraph)
    def maker(*args,**kwargs):
        kwargs["invariant"]=1;kwargs["pageCompression"]=1
        return canvas.Canvas(*args,**kwargs)
    doc.build(story,canvasmaker=maker)
    base=PdfReader(io.BytesIO(stream.getvalue()))
    writer=PdfWriter(clone_from=base)
    for position in overlays:
        source=PdfReader(io.BytesIO(figures[position["path"]]["data"]))
        transform=Transformation().scale(position["scale"]).translate(position["x"],position["y"])
        writer.pages[position["page"]-1].merge_transformed_page(source.pages[0],transform,over=True,expand=False)
    writer.add_metadata({"/Title":next(b.text for b in blocks if b.kind=="heading"),"/Author":"", "/Subject":"Working research draft; author declarations pending",
                         "/Creator":"TETHER deterministic Markdown renderer","/Producer":"ReportLab + pypdf (invariant local build)"})
    result=io.BytesIO();writer.write(result)
    return result.getvalue(),expected,overlays,block_log


def qa(raw,expected,overlays):
    import pdfplumber
    from pypdf import PdfReader
    reader=PdfReader(io.BytesIO(raw))
    extracted="\n".join(page.extract_text() or "" for page in reader.pages)
    retention=ordered_retention(expected,visible_spans(reader))
    expected_tokens=Counter(re.findall(r"[A-Za-z0-9]+",unicodedata.normalize("NFKC"," ".join(x["text"] for x in expected)).casefold()))
    actual_tokens=Counter(re.findall(r"[A-Za-z0-9]+",unicodedata.normalize("NFKC",extracted).casefold()))
    out_of_page=[];images=0
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for index,page in enumerate(pdf.pages,1):
            images+=len(page.images)
            for char in page.chars:
                if char["text"].strip() and (char["x0"]<4 or char["x1"]>WIDTH-4 or char["top"]<4 or char["bottom"]>HEIGHT-4):
                    out_of_page.append(dict(page=index,text=char["text"],bbox=[char["x0"],char["top"],char["x1"],char["bottom"]]))
    need(not out_of_page,"Text outside page boundary")
    need(images==0,"Unexpected raster image in vector manuscript")
    for position in overlays:
        need(position["x"]>=LEFT-1 and position["y"]>=BOTTOM-1 and position["x"]+position["width"]<=WIDTH-LEFT+1 and
             position["y"]+position["height"]<=BOTTOM+CONTENT_H+1,"Figure outside content frame")
    links=sum(len(page.get("/Annots",[])) for page in reader.pages)
    return dict(pages=len(reader.pages),source_text_tokens=sum(expected_tokens.values()),extracted_text_tokens=sum(actual_tokens.values()),
        ordered_source_retention=retention,out_of_page_glyphs=out_of_page,raster_images=images,link_annotations=links,
        vector_figure_overlays=len(overlays),text_coverage_method="ordered marked visible-text spans exact against every paragraph/table-cell/reference/caption; only declared typography and layout whitespace normalized",
        manual_visual_review="all rendered pages must be inspected separately")


def validate_preview_root(path):
    path=Path(path).resolve()
    need(path.is_relative_to(ROOT/"tmp/pdfs"),"QA preview root must stay in workspace tmp/pdfs")
    return path


def commit_pair(pdf,build,out_pdf=OUTPUT,out_build=BUILD):
    """Publish only after QA; restore prior reviewed pair on a caught write error."""
    old={path:path.read_bytes() if path.exists() else None for path in (out_pdf,out_build)}
    temp_parent=ROOT/"tmp/pdfs";temp_parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p08-publish-",dir=temp_parent) as folder:
        folder=Path(folder)
        staged_pdf,staged_build=folder/"document.pdf",folder/"build.json"
        staged_pdf.write_bytes(pdf);staged_build.write_bytes(build)
        try:
            os.replace(staged_pdf,out_pdf);os.replace(staged_build,out_build)
        except BaseException:
            for index,path in enumerate((out_pdf,out_build)):
                if old[path] is None:path.unlink(missing_ok=True)
                else:
                    restore=folder/f"restore-{index}"
                    restore.write_bytes(old[path]);os.replace(restore,path)
            raise


def publish_document(pdf,manifest,preview_root,*,out_pdf=OUTPUT,out_build=BUILD,renderer=None):
    preview_root=validate_preview_root(preview_root)
    # Versioned preview generations keep a failed render from changing the
    # prior PDF's reviewed previews. They are local QA intermediates only.
    previews_at=preview_root/digest(pdf)[:16]
    previews_at.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p08-render-",dir=ROOT/"tmp/pdfs") as folder:
        staged=Path(folder)/"candidate.pdf";staged.write_bytes(pdf)
        (renderer or subprocess.run)([str(POPLER),"-r","100","-png",str(staged),str(previews_at/"page")],check=True,capture_output=True)
    previews=sorted(previews_at.glob("page-*.png"))
    need(len(previews)==manifest["qa"]["pages"],"Rendered page count differs")
    manifest["page_previews"]=[dict(path=path.relative_to(ROOT).as_posix(),sha256=digest(path.read_bytes())) for path in previews]
    serialized=(json.dumps(manifest,ensure_ascii=True,sort_keys=True,indent=2)+"\n").encode()
    commit_pair(pdf,serialized,out_pdf,out_build)
    return previews_at


def publication_regressions():
    temp_parent=ROOT/"tmp/pdfs";temp_parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p08-regression-",dir=temp_parent) as folder:
        folder=Path(folder);pdf,build=folder/"old.pdf",folder/"old.json"
        pdf.write_bytes(b"reviewed-pdf");build.write_bytes(b"reviewed-build")
        def fail_render(*args,**kwargs):raise OSError("fictional Poppler failure")
        for name,preview in (("invalid_preview_path",PAPER),("render_failure",folder/"previews")):
            try:publish_document(b"new candidate",dict(qa=dict(pages=1)),preview,out_pdf=pdf,out_build=build,renderer=fail_render)
            except (ValueError,OSError):pass
            else:raise ValueError("Publication regression not rejected: "+name)
            need(pdf.read_bytes()==b"reviewed-pdf" and build.read_bytes()==b"reviewed-build","Failed preparation replaced reviewed pair")
    return dict(status="PASS",negative_cases=["invalid_preview_path","render_failure"],prior_pair_preserved=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-inputs",action="store_true")
    group.add_argument("--build",action="store_true")
    group.add_argument("--self-test",action="store_true")
    parser.add_argument("--marker-confirmed",action="store_true",help="Successful external one-PDF create marker already run once for this authoring operation")
    parser.add_argument("--repeat-check",action="store_true")
    parser.add_argument("--preview-root",type=Path,default=ROOT/"tmp/pdfs/preprint-manuscript-pages")
    args=parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(dict(retention=retention_regressions(),publication=publication_regressions()),sort_keys=True));return
    preview_root=validate_preview_root(args.preview_root)
    raw,blocks,definitions,references,figures=inputs()
    if args.check_inputs:
        print(json.dumps(dict(status="PASS_INPUT_PARSE",source_sha256={name:digest(value) for name,value in raw.items()},
            blocks=len(blocks),tables=sum(b.kind=="table" for b in blocks),figures=len(figures),references=sorted(references)),sort_keys=True));return
    need(args.marker_confirmed,"Run external PDF-operation marker exactly once before first creation")
    tests=dict(retention=retention_regressions(),publication=publication_regressions())
    font_bytes={name:path.read_bytes() for name,path in FONTS.items()}
    pdf,expected,overlays,block_log=render_once(blocks,definitions,references,figures,font_bytes)
    checks=qa(pdf,expected,overlays)
    repeated=None
    if args.repeat_check:
        fresh=[];fresh_defs={}
        for path in SOURCES:
            items,defs=parse_markdown(raw[path.name].decode("utf-8-sig"),path.name);fresh.extend(items);fresh_defs.update(defs)
        second,_,_,_=render_once(fresh,fresh_defs,references,figures,font_bytes)
        need(pdf==second,"Local invariant PDF repeat differs")
        repeated=True
    import reportlab,pypdf,pdfplumber
    manifest=dict(schema_version=1,status="WORKING_DRAFT_PDF_PENDING_OWNER_DECLARATIONS_AND_FINAL_REVIEW",renderer=dict(path=Path(__file__).relative_to(ROOT).as_posix(),sha256=digest(Path(__file__).read_bytes())),
        sources={name:dict(path="paper/"+name,sha256=digest(value),bytes=len(value)) for name,value in raw.items()},
        figure_manifest=dict(path="paper/results/ARTIFACTS.json",sha256=RESULTS_SHA),figures={key:{k:v for k,v in value.items() if k!="data"} for key,value in figures.items()},
        pdf=dict(path=OUTPUT.relative_to(ROOT).as_posix(),sha256=digest(pdf),bytes=len(pdf)),qa=checks,
        repeat_bytes_equal=repeated,font_files={name:dict(path=str(path),sha256=digest(font_bytes[name]),embedding_policy="subset_when_used",packaged_font_file=False) for name,path in FONTS.items()},
        tool_versions=dict(python=platform.python_version(),interpreter=sys.executable,reportlab=reportlab.Version,pypdf=pypdf.__version__,pdfplumber=pdfplumber.__version__),
        marker_evidence=dict(command=["node",MARKER,"--operation-kind","create","--expected-output-count","1","--output-format","pdf"],
            exit_code=0,invocation="successful external Codex tool call immediately before first --build; not rerun on layout corrections"),
        self_tests=tests,blocks=block_log,visible_source_units=[{k:v for k,v in unit.items() if k!="text"}|dict(visible_text_sha256=digest(unit["text"].encode()),visible_characters=len(unit["text"])) for unit in expected],
        figure_placements=overlays,author_metadata="pending owner confirmation; no facts inferred",scientific_scope="technical source fidelity only",
        source_data_or_expected_reference_values_read=0,network_calls=0,new_downloads=0,model_calls=0,provider_spending_usd=0,
        reproducibility="same local pinned source/figure/font/library environment; no cross-platform byte guarantee")
    previews_at=publish_document(pdf,manifest,preview_root)
    print(json.dumps(dict(status=manifest["status"],pages=checks["pages"],vector_figures=len(overlays),pdf_sha256=digest(pdf),
                         repeat_bytes_equal=repeated,preview_root=str(previews_at)),sort_keys=True))


if __name__=="__main__":main()

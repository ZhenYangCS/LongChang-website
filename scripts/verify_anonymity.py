"""Audit every site file and archive member; identities may occur only in the author block.

The identity list is read from that block, never duplicated in this script.
Reports and optional OCR samples must live outside the project page.
"""
import argparse
import base64
from collections import Counter
import concurrent.futures
import gzip
import hashlib
from html import unescape
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit
import zipfile

SITE = Path(__file__).resolve().parents[1]
AUTHOR_BLOCK = re.compile(r'<!-- AUTHORS_BEGIN:.*?<!-- AUTHORS_END -->', re.S)
DATA_IMAGE = re.compile(r'data:(image/[\w.+-]+);base64,([A-Za-z0-9+/=]+)')
TEXT_TYPES = {'.html','.js','.css','.json','.csv','.txt','.md','.py','.sh','.yml','.yaml','.xml','.svg'}
IMAGE_TYPES = {'.png','.webp','.gif','.jpg','.jpeg'}


class AuthorIdentities(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack=[]; self.active=[]; self.terms=[]; self.links=[]

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag); attrs=dict(attrs)
        kind='author' if 'data-author-name' in attrs else 'affiliation' if 'data-author-affiliation' in attrs else None
        if kind:
            self.active.append(dict(depth=len(self.stack),kind=kind,parts=[]))
            if attrs.get('href'):self.links.append(attrs['href'])

    def handle_data(self, data):
        for item in self.active:item['parts'].append(data)

    def handle_endtag(self, tag):
        depth=len(self.stack)
        for item in self.active[:]:
            if item['depth']==depth:
                self.terms.append((item['kind'],' '.join(''.join(item['parts']).split())))
                self.active.remove(item)
        if self.stack:self.stack.pop()


def identities(path, extra):
    html=path.read_text(); blocks=AUTHOR_BLOCK.findall(html)
    if len(blocks)!=1:raise ValueError('Expected one isolated author block in the identity source.')
    parser=AuthorIdentities();parser.feed(blocks[0]);terms=parser.terms
    if not any(kind=='author' for kind,_ in terms):
        raise ValueError('Use an identified page as --identity-source, even when auditing an anonymous export.')
    for link in parser.links:
        parsed=urlsplit(unescape(link))
        if parsed.hostname and parsed.hostname.endswith('.github.io'):
            terms.append(('profile',parsed.hostname.removesuffix('.github.io')))
        elif parsed.hostname and not parsed.hostname.endswith('google.com'):
            terms.append(('profile',parsed.hostname.removeprefix('www.')))
        for value in parse_qs(parsed.query).get('user',[]):terms.append(('profile',value))
    terms.extend(('extra',value) for value in extra)
    patterns=[]; binary=[]
    for i,(kind,value) in enumerate(terms):
        words=re.findall(r'[A-Za-z0-9]+|[\u3400-\u9fff]+',value)
        if not words:continue
        expr=r'(?<![A-Za-z])'+r'[\W_]*'.join(map(re.escape,words))+r'(?![A-Za-z])'
        label=f'{kind}_{i+1}'
        needles=[word.casefold() for word in words]
        patterns.append((label,re.compile(expr,re.I),needles))
        # Short initials can occur by chance in compressed image/video bytes.
        # They are checked in decoded text, metadata, font names and OCR instead.
        if len(''.join(words))>=5 and value.isascii():binary.append((label,re.compile(expr.encode(),re.I),[word.encode() for word in needles]))
    return patterns,binary,len(parser.terms)


class Audit:
    def __init__(self,args):
        self.args=args;self.root=args.root.resolve();self.records=[];self.findings=[];self.domains=Counter();self.emails={};self.ocr=[]
        self.text_patterns,self.byte_patterns,self.identity_count=identities(args.identity_source,args.extra_term)
        self.work=Path(tempfile.mkdtemp(prefix='page-anonymity-'))
        self.ffmpeg=None
        try:
            import imageio_ffmpeg
            self.ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:pass

    def finding(self,path,kind,label=None,detail=None):
        item=dict(path=path,kind=kind)
        if label:item['identity']=label
        if detail:item['detail']=detail
        if item not in self.findings:self.findings.append(item)

    def text(self,text,path,context='text'):
        text=unescape(text)
        text=re.sub(r'\\u([0-9a-fA-F]{4})',lambda m:chr(int(m[1],16)),text)
        text=re.sub(r'\\[nrt]',' ',text)
        text=DATA_IMAGE.sub('',text)
        folded=text.casefold()
        for label,pattern,needles in self.text_patterns:
            if all(needle in folded for needle in needles) and pattern.search(text):self.finding(path,context,label)
        if '@' in text:
            for email in re.findall(r'\b[A-Za-z0-9._%+-]{1,64}@(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24}\b',text):
                self.emails.setdefault(email,set()).add(path)
        for url in re.findall(r'https?://[^\s<>"\x00]+',text):
            try:
                host=urlsplit(url.rstrip(').,;')).hostname
                if host:self.domains[host]+=1
            except ValueError:pass

    def image(self,data,path,digest):
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            info={key:str(value) for key,value in im.info.items() if key not in {'icc_profile'}}
            info['exif']=str(dict(im.getexif()))
            if im.info.get('icc_profile'):self.text(im.info['icc_profile'].decode('latin1'),path,'image profile')
            self.text(json.dumps(info,ensure_ascii=False),path,'image metadata')
            if self.args.ocr:
                frames=sorted({0,getattr(im,'n_frames',1)//2,getattr(im,'n_frames',1)-1})
                for frame in frames:
                    im.seek(frame);rgba=im.convert('RGBA');background=Image.new('RGBA',im.size,'white');background.alpha_composite(rgba)
                    target=self.work/f'{digest}-{frame}.png';background.convert('RGB').save(target)
                    self.ocr.append((path+f'#frame={frame}',target))

    def video(self,data,path,digest,local):
        if not self.ffmpeg:raise RuntimeError('imageio-ffmpeg is required for video metadata inspection')
        if local is None:
            local=self.work/(digest+'.mp4');local.write_bytes(data)
        proc=subprocess.run([self.ffmpeg,'-hide_banner','-i',str(local)],capture_output=True,text=True,timeout=30)
        if 'Video:' not in proc.stderr:raise RuntimeError('Could not read video metadata')
        self.text(proc.stderr,path,'video metadata')
        if self.args.ocr:
            match=re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)',proc.stderr)
            if not match:raise RuntimeError('Could not determine video duration')
            duration=int(match[1])*3600+int(match[2])*60+float(match[3])
            for i,seconds in enumerate([0,duration/2,max(0,duration-.1)]):
                target=self.work/f'{digest}-video-{i}.png'
                subprocess.run([self.ffmpeg,'-loglevel','error','-y','-ss',str(seconds),'-i',str(local),'-frames:v','1',str(target)],check=True,capture_output=True,timeout=30)
                self.ocr.append((path+f'#time={seconds:.2f}',target))

    def inspect(self,data,path,local=None,depth=0):
        suffix=Path(path).suffix.lower();digest=hashlib.sha256(data).hexdigest()
        record=dict(path=path,bytes=len(data),sha256=digest,checks=['filename','bytes']);self.records.append(record)
        self.text(path,path,'filename')
        content=data
        if path=='index.html' and not self.args.require_anonymous:
            html=data.decode();blocks=AUTHOR_BLOCK.findall(html)
            if len(blocks)!=1:self.finding(path,'invalid author block')
            content=AUTHOR_BLOCK.sub('<!-- isolated author block -->',html).encode()
            record['checks'].append('author block excluded')
        folded=content.lower()
        for label,pattern,needles in self.byte_patterns:
            if all(needle in folded for needle in needles) and pattern.search(content):self.finding(path,'bytes',label)
        if depth>8:self.finding(path,'inspection failed',detail='Archive nesting exceeds eight levels');return
        start=len(self.findings)
        try:
            if suffix=='.zip' or data.startswith(b'PK\x03\x04'):
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    for entry in archive.infolist():
                        if not entry.is_dir():self.inspect(archive.read(entry),path+'!'+entry.filename,depth=depth+1)
                    self.text(archive.comment.decode('utf-8','replace'),path,'archive comment')
                record['checks'].append('all archive members and CRCs')
            elif suffix=='.gz' or data.startswith(b'\x1f\x8b'):
                self.inspect(gzip.decompress(data),path+'!'+Path(path).stem,depth=depth+1)
                record['checks'].append('decompressed content and CRC')
            elif suffix in TEXT_TYPES or '\x00' not in content[:4000].decode('utf-8','replace') and suffix in {'','.gitignore'}:
                text=content.decode('utf-8','replace');self.text(text,path)
                for i,m in enumerate(DATA_IMAGE.finditer(text)):
                    extension={'image/svg+xml':'.svg','image/webp':'.webp','image/png':'.png','image/jpeg':'.jpg'}.get(m[1],'.png')
                    self.inspect(base64.b64decode(m[2]),f'{path}#image-{i}{extension}',depth=depth+1)
                record['checks'].append('decoded text and embedded images')
            elif suffix=='.pdf':
                from pypdf import PdfReader
                reader=PdfReader(io.BytesIO(data));self.text(str(reader.metadata),path,'PDF metadata')
                if reader.xmp_metadata:self.text(reader.xmp_metadata.stream.get_data().decode('utf-8','replace'),path,'PDF XMP')
                for i,page in enumerate(reader.pages):
                    self.text(page.extract_text() or '',path+f'#page={i+1}','PDF text')
                    for annotation in page.get('/Annots',[]):self.text(str(annotation.get_object()),path+f'#page={i+1}','PDF annotations')
                for name,values in reader.attachments.items():
                    for value in values:self.inspect(value,path+'!'+name,depth=depth+1)
                record['checks'].append(f'PDF metadata, annotations, attachments and all {len(reader.pages)} pages')
            elif suffix in IMAGE_TYPES:
                self.image(data,path,digest);record['checks'].append('image metadata and profiles')
            elif suffix=='.mp4':
                self.video(data,path,digest,local);record['checks'].append('video metadata')
            elif suffix in {'.ttf','.woff','.woff2','.otf'}:
                from fontTools.ttLib import TTFont
                with TTFont(io.BytesIO(data)) as font:
                    for name in font['name'].names:self.text(name.toUnicode(),path,'font metadata')
                    if 'meta' in font:self.text(str(font['meta'].data),path,'font metadata')
                record['checks'].append('font metadata')
        except Exception as error:self.finding(path,'inspection failed',detail=f'{type(error).__name__}: {error}')
        record['findings']=len(self.findings)-start

    def run_ocr(self):
        import shutil
        if not shutil.which('tesseract'):raise RuntimeError('tesseract is required for --ocr')
        unique={};aliases={}
        for label,path in self.ocr:
            digest=hashlib.sha256(path.read_bytes()).hexdigest();unique.setdefault(digest,path);aliases.setdefault(digest,[]).append(label)
        def recognize(item):
            digest,path=item
            env=dict(os.environ);env['OMP_THREAD_LIMIT']='1'
            proc=subprocess.run(['tesseract',str(path),'stdout','-l','eng','--psm','11'],capture_output=True,text=True,check=True,timeout=90,env=env)
            return digest,proc.stdout
        completed=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.workers) as pool:
            for digest,text in pool.map(recognize,unique.items()):
                for label in aliases[digest]:self.text(text,label,'OCR')
                completed+=1
                if completed%100==0:print(f'OCR: {completed}/{len(unique)} unique samples checked.',flush=True)
        return dict(samples=len(self.ocr),unique_samples=len(unique),scope='All static images; first/middle/last frames of every animated image and video.')

    def run(self):
        files=sorted(path for path in self.root.rglob('*') if path.is_file())
        for i,path in enumerate(files):
            self.inspect(path.read_bytes(),str(path.relative_to(self.root)),local=path)
            if (i+1)%250==0:print(f'Files: {i+1}/{len(files)} checked.',flush=True)
        optical=self.run_ocr() if self.args.ocr else None
        report=dict(root=str(self.root),files=len(files),inspected_objects=len(self.records),identity_terms=self.identity_count,
                    author_exception=not self.args.require_anonymous,ocr=optical,findings=self.findings,
                    domains=dict(self.domains.most_common()),emails={key:sorted(paths) for key,paths in self.emails.items()},records=self.records)
        self.args.report.parent.mkdir(parents=True,exist_ok=True);self.args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(f"Checked {len(files)} files and {len(self.records)-len(files)} archive members/embedded images; {len(self.findings)} findings. Report: {self.args.report}",flush=True)
        for finding in self.findings[:40]:print(json.dumps(finding,ensure_ascii=False),flush=True)
        return not self.findings


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=SITE)
    parser.add_argument('--identity-source',type=Path,default=SITE/'index.html')
    parser.add_argument('--report',type=Path,default=Path('/tmp/project-page-anonymity-audit.json'))
    parser.add_argument('--extra-term',action='append',default=[])
    parser.add_argument('--require-anonymous',action='store_true')
    parser.add_argument('--ocr',action='store_true')
    parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args()
    if args.report.resolve().is_relative_to(args.root.resolve()):parser.error('Write audit reports outside the project page.')
    raise SystemExit(0 if Audit(args).run() else 1)


if __name__=='__main__':main()

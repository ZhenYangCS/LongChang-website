"""Static preview with byte ranges for videos and fresh editable assets."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import gzip
import io


class PreviewHandler(SimpleHTTPRequestHandler):
    compressed = {}
    def end_headers(self):
        if self.path.split('?')[0].endswith(('.html','.js','.css','.json')) or self.path.split('?')[0].endswith('/'):
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def send_head(self):
        self.byte_range = None
        path = Path(self.translate_path(self.path))
        header = self.headers.get('Range')
        if not header and path.is_file() and path.suffix in {'.js','.css','.json','.xml','.wasm','.svg'} and 'gzip' in self.headers.get('Accept-Encoding',''):
            stat=path.stat();key=str(path)
            cached=self.compressed.get(key)
            if not cached or cached[0]!=stat.st_mtime_ns:
                cached=(stat.st_mtime_ns,gzip.compress(path.read_bytes(),compresslevel=6));self.compressed[key]=cached
            payload=cached[1]
            self.send_response(200)
            self.send_header('Content-Type',self.guess_type(str(path)))
            self.send_header('Content-Encoding','gzip')
            self.send_header('Vary','Accept-Encoding')
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers()
            return io.BytesIO(payload)
        if not header or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
        if not match or not any(match.groups()):
            self.send_error(400, 'A single byte range is required')
            return None
        start = int(match[1]) if match[1] else max(0, size - int(match[2]))
        end = min(size - 1, int(match[2])) if match[1] and match[2] else size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        stream = path.open('rb')
        stream.seek(start)
        self.byte_range = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(self.byte_range))
        self.end_headers()
        return stream

    def copyfile(self, source, outputfile):
        try:
            if self.byte_range is None:
                return super().copyfile(source, outputfile)
            remaining = self.byte_range
            while remaining:
                chunk = source.read(min(remaining, 128 * 1024))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--bind', default='0.0.0.0')
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1],
                        help='Static root; use the parent of a packaged site to test a repository subpath')
    args = parser.parse_args()
    handler = partial(PreviewHandler, directory=str(args.directory.resolve()))
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f'LongChang preview listening on {args.bind}:{args.port}', flush=True)
    server.serve_forever()

import struct

BLOCK_SIZE = 512
MAX_BLOCKS = 1024
FAT_FREE = 0x0000
FAT_EOF = 0xFFFF
MAX_FILENAME_LEN = 32
DIR_ENTRIES = 64

class ZXFS:
    def __init__(self, image_path):
        self.image_path = image_path
        self.fat = [FAT_FREE]*MAX_BLOCKS
        self.dir = []
        self.fp = None

    def open(self, mode='r+b'):
        self.fp = open(self.image_path, mode)
        if 'r' in mode:
            self.load()

    def close(self):
        if self.fp:
            self.fp.close()
            self.fp = None

    def load(self):
        self.fp.seek(0)
        hdr = self.fp.read(4)
        if hdr != b'ZXFS':
            raise print('\033[1;37mzxfs: \x1b[1;31mfatal error:\033[0m Not a ZXFS filesystem\n\033[1;37mzxfs: \x1b[1;31msyntax error:\033[0m python:')
        self.fat = list(struct.unpack('<' + 'H'*MAX_BLOCKS, self.fp.read(2*MAX_BLOCKS)))
        self.dir = []
        for _ in range(DIR_ENTRIES):
            raw = self.fp.read(1+MAX_FILENAME_LEN+4+4*16)
            if raw == b'' or len(raw) < (1+MAX_FILENAME_LEN+4+4*16):
                break
            fn_len = raw[0]
            if fn_len == 0 or fn_len > MAX_FILENAME_LEN:
                continue
            name = raw[1:1+fn_len].decode()
            size = struct.unpack('<I', raw[1+MAX_FILENAME_LEN:1+MAX_FILENAME_LEN+4])[0]
            blocks_raw = raw[1+MAX_FILENAME_LEN+4:]
            blocks = list(struct.unpack('<' + 'I'*16, blocks_raw))
            blocks = [b for b in blocks if b != 0]
            self.dir.append({'name':name,'size':size,'blocks':blocks})

    def save(self):
        self.fp.seek(0)
        self.fp.write(b'ZXFS')
        self.fp.write(struct.pack('<' + 'H'*MAX_BLOCKS, *self.fat))
        for entry in self.dir:
            fn_bytes = entry['name'].encode()
            fn_len = len(fn_bytes)
            fn_field = fn_bytes + b'\x00'*(MAX_FILENAME_LEN - fn_len)
            size_field = struct.pack('<I', entry['size'])
            blocks_field = struct.pack('<' + 'I'*16, *(entry['blocks'] + [0]*(16-len(entry['blocks']))))
            self.fp.write(struct.pack('B', fn_len) + fn_field + size_field + blocks_field)
        rem = DIR_ENTRIES - len(self.dir)
        self.fp.write(b'\x00'*rem*(1+MAX_FILENAME_LEN+4+4*16))
        self.fp.flush()

    def find_free_block(self):
        for i in range(1, MAX_BLOCKS):
            if self.fat[i] == FAT_FREE:
                return i
        return None

    def allocate_blocks(self, count):
        blocks = []
        for _ in range(count):
            b = self.find_free_block()
            if b is None:
                return None
            blocks.append(b)
            self.fat[b] = FAT_EOF
        for i in range(len(blocks)-1):
            self.fat[blocks[i]] = blocks[i+1]
        return blocks

    def write_file(self, filename, data):
        if len(filename) > MAX_FILENAME_LEN:
            raise Exception('Filename too long')
        blocks_needed = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
        blocks = self.allocate_blocks(blocks_needed)
        if blocks is None:
            raise Exception('No space')
        for i, b in enumerate(blocks):
            self.fp.seek(b*BLOCK_SIZE)
            chunk = data[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE]
            chunk += b'\x00'*(BLOCK_SIZE - len(chunk))
            self.fp.write(chunk)
        for e in self.dir:
            if e['name'] == filename:
                for b in e['blocks']:
                    self.fat[b] = FAT_FREE
                e['blocks'] = blocks
                e['size'] = len(data)
                return
        if len(self.dir) >= DIR_ENTRIES:
            raise Exception('Directory full')
        self.dir.append({'name':filename,'size':len(data),'blocks':blocks})

    def list_files(self):
        return [(e['name'], e['size']) for e in self.dir]

    def read_file(self, filename):
        for e in self.dir:
            if e['name'] == filename:
                data = bytearray()
                for b in e['blocks']:
                    self.fp.seek(b*BLOCK_SIZE)
                    chunk = self.fp.read(BLOCK_SIZE)
                    data.extend(chunk)
                return data[:e['size']]
        return None


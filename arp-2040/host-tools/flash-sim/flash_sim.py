"""
flash_sim.py — Host-side 16 MB QSPI flash simulator
Maps a file to the same API as firmware/include/hal/IStorage.h
"""
import os, struct, hashlib, io
from dataclasses import dataclass, field
from typing import Optional, List

CAPACITY = 16 * 1024 * 1024  # 16 MB
PAGE_SIZE = 256

MAGIC_ACTIVE  = 0x41505246  # "APRF"
MAGIC_STAGING = 0x53505246  # "SPRF"
MAGIC_EMPTY   = 0x00000000


@dataclass
class ImageMetadata:
    magic: int = MAGIC_EMPTY
    version: int = 0
    image_length: int = 0
    payload_crc32: int = 0
    metadata_crc32: int = 0
    timestamp_unix: int = 0
    source: int = 0
    flags: int = 0
    reserved: bytes = field(default=b'\x00' * 32)

    # 8 fields × 4 bytes + 32 reserved = 64 bytes total
    SIZE: int = 64

    def to_bytes(self) -> bytes:
        hdr = struct.pack(
            '<IIIIIIII',
            self.magic, self.version, self.image_length,
            self.payload_crc32, self.metadata_crc32,
            self.timestamp_unix, self.source, self.flags
        )
        return hdr + self.reserved

    @classmethod
    def from_bytes(cls, data: bytes) -> 'ImageMetadata':
        # Expect exactly 64 bytes: 8 uint32_t (32 bytes) + 32 bytes reserved
        if len(data) < 64:
            raise ValueError(f"ImageMetadata requires 64 bytes, got {len(data)}")
        fields = struct.unpack('<IIIIIIII', data[:32])
        return cls(
            magic=fields[0], version=fields[1], image_length=fields[2],
            payload_crc32=fields[3], metadata_crc32=fields[4],
            timestamp_unix=fields[5], source=fields[6], flags=fields[7],
            reserved=data[32:64]
        )


def crc32(data: bytes) -> int:
    import zlib
    return 0xFFFFFFFF & (zlib.crc32(data) ^ 0xFFFFFFFF)


class FlashSimulator:
    def __init__(self, path: str = ':memory:'):
        self.path = path
        if path == ':memory:':
            self._data = bytearray(CAPACITY)
        else:
            size = os.path.getsize(path) if os.path.exists(path) else 0
            if size < CAPACITY:
                with open(path, 'wb') as f:
                    f.write(b'\xFF' * CAPACITY)
            with open(path, 'r+b') as f:
                self._data = bytearray(f.read())

    def _check_bounds(self, offset: int, length: int):
        if offset < 0 or offset + length > CAPACITY:
            raise ValueError(f"Flash access out of bounds: 0x{offset:08X}+{length}")

    def read(self, offset: int, length: int) -> bytes:
        self._check_bounds(offset, length)
        return bytes(self._data[offset:offset + length])

    def write(self, offset: int, data: bytes):
        self._check_bounds(offset, len(data))
        for i, b in enumerate(data):
            self._data[offset + i] = b
        self._persist()

    def erase(self, offset: int, length: int):
        self._check_bounds(offset, length)
        for i in range(length):
            self._data[offset + i] = 0xFF
        self._persist()

    def program_page(self, page_addr: int, data: bytes):
        """Program a single 256-byte page. Bits can only transition 1→0."""
        if len(data) != PAGE_SIZE:
            raise ValueError(f"Page program requires exactly {PAGE_SIZE} bytes")
        self._check_bounds(page_addr, PAGE_SIZE)
        for i in range(PAGE_SIZE):
            self._data[page_addr + i] &= data[i]
        self._persist()

    def read_metadata(self, offset: int) -> ImageMetadata:
        raw = self.read(offset, 64)
        return ImageMetadata.from_bytes(raw)

    def write_image_staging(self, staging_offset: int, payload: bytes,
                            version: int = 1, source: int = 0) -> ImageMetadata:
        """Write payload + metadata to staging region."""
        meta_offset = staging_offset
        payload_offset = staging_offset + 64

        # Phase 1: write payload
        self.erase(payload_offset, len(payload))
        self.write(payload_offset, payload)

        # Phase 2: build metadata
        meta = ImageMetadata(
            magic=MAGIC_STAGING,
            version=version,
            image_length=len(payload),
            payload_crc32=crc32(payload),
            timestamp_unix=int(__import__('time').time()),
            source=source
        )
        meta.metadata_crc32 = crc32(meta.to_bytes()[:32])

        # Phase 3: write metadata
        meta_bytes = meta.to_bytes()
        self.erase(meta_offset, len(meta_bytes))
        self.write(meta_offset, meta_bytes)

        return meta

    def promote_image(self, active_meta_offset: int, staging_meta_offset: int) -> bool:
        """Atomic promotion: copy staging metadata to active location."""
        staging_meta = self.read_metadata(staging_meta_offset)
        if staging_meta.magic != MAGIC_STAGING:
            return False
        if staging_meta.payload_crc32 != crc32(
                self.read(staging_meta_offset + 64, staging_meta.image_length)):
            return False

        # Write active metadata (this is the atomic switch)
        active_meta = staging_meta
        active_meta.magic = MAGIC_ACTIVE
        active_meta_bytes = active_meta.to_bytes()
        self.erase(active_meta_offset, len(active_meta_bytes))
        self.write(active_meta_offset, active_meta_bytes)
        return True

    def verify_region(self, meta_offset: int) -> bool:
        meta = self.read_metadata(meta_offset)
        if meta.magic not in (MAGIC_ACTIVE, MAGIC_STAGING):
            return False
        payload = self.read(meta_offset + 64, meta.image_length)
        return crc32(payload) == meta.payload_crc32

    def dump(self, path: str):
        with open(path, 'wb') as f:
            f.write(self._data)

    def load(self, path: str):
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) != CAPACITY:
            raise ValueError(f"Flash dump size mismatch: {len(data)} != {CAPACITY}")
        self._data = bytearray(data)

    def _persist(self):
        if self.path != ':memory:' and hasattr(self, '_file'):
            self._file.seek(0)
            self._file.write(self._data)
            self._file.flush()

    def __enter__(self):
        if self.path != ':memory:':
            self._file = open(self.path, 'r+b')
        return self

    def __exit__(self, *args):
        if hasattr(self, '_file'):
            self._file.close()

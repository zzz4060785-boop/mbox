"""Upload validation based on file signatures, not browser-provided MIME alone."""

import socket
import struct

IMAGE_SIGNATURES = {
    "jpg": ((0, b"\xff\xd8\xff"),),
    "jpeg": ((0, b"\xff\xd8\xff"),),
    "png": ((0, b"\x89PNG\r\n\x1a\n"),),
    "gif": ((0, b"GIF87a"), (0, b"GIF89a")),
    "webp": ((0, b"RIFF"), (8, b"WEBP")),
}


def has_valid_image_signature(uploaded_file, extension):
    checks = IMAGE_SIGNATURES.get(extension.lower())
    if not checks:
        return False
    position = uploaded_file.stream.tell()
    header = uploaded_file.stream.read(16)
    uploaded_file.stream.seek(position)
    # WEBP requires both RIFF and WEBP; other formats allow alternative signatures.
    if extension.lower() == "webp":
        return all(header[offset:offset + len(value)] == value for offset, value in checks)
    return any(header[offset:offset + len(value)] == value for offset, value in checks)


def has_valid_media_signature(uploaded_file, extension):
    extension = extension.lower()
    if extension in IMAGE_SIGNATURES:
        return has_valid_image_signature(uploaded_file, extension)
    position = uploaded_file.stream.tell()
    header = uploaded_file.stream.read(32)
    uploaded_file.stream.seek(position)
    if extension in {"mp4", "m4a"}:
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if extension == "webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    if extension == "wav":
        return header.startswith(b"RIFF") and header[8:12] == b"WAVE"
    if extension == "ogg":
        return header.startswith(b"OggS")
    if extension == "mp3":
        return header.startswith(b"ID3") or (
            len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
        )
    return False


def is_safe_upload(uploaded_file, extension, config):
    if not has_valid_media_signature(uploaded_file, extension):
        return False
    host = config.get("CLAMAV_HOST", "").strip()
    required = bool(config.get("UPLOAD_SCAN_REQUIRED"))
    if not host:
        return not required
    position = uploaded_file.stream.tell()
    try:
        with socket.create_connection((host, int(config.get("CLAMAV_PORT", 3310))), timeout=10) as connection:
            connection.sendall(b"zINSTREAM\0")
            while True:
                chunk = uploaded_file.stream.read(65536)
                if not chunk:
                    break
                connection.sendall(struct.pack("!I", len(chunk)) + chunk)
            connection.sendall(struct.pack("!I", 0))
            result = connection.recv(4096)
        return b"OK" in result and b"FOUND" not in result
    except OSError:
        return not required
    finally:
        uploaded_file.stream.seek(position)

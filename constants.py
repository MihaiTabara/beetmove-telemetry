ZIP_MAX_SIZE_IN_MB = 10
ZIP_MAX_COMPRESSION_RATIO = 10
CACHE_CONTROL_MAXAGE = 3600 * 4

MIME_MAP = {
    '': 'text/plain',
    '.aar': 'application/java-archive',
    '.apk': 'application/vnd.android.package-archive',
    '.asc': 'text/plain',
    '.beet': 'text/plain',
    '.bundle': 'application/octet-stream',
    '.bz2': 'application/octet-stream',
    '.checksums': 'text/plain',
    '.dmg': 'application/x-iso9660-image',
    '.jar': 'application/java-archive',
    '.json': 'application/json',
    '.mar': 'application/octet-stream',
    '.md5': 'text/plain',
    '.msi': 'application/x-msi',
    '.pkg': 'application/x-newton-compatible-pkg',
    '.pom': 'application/xml',
    '.sha1': 'text/plain',
    '.snap': 'application/octet-stream',
    '.xpi': 'application/x-xpinstall',
}

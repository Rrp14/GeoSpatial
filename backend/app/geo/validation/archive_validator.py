import re
import stat
import zipfile
from pathlib import PurePosixPath
from app.core.exceptions import AppError


def extract_shapefile(path, destination, settings):
    def reject(message, code="INVALID_ARCHIVE"):
        raise AppError(code, message)
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > settings.max_archive_files:
                reject("Archive contains too many members.", "ARCHIVE_TOO_LARGE")
            limit = settings.max_archive_uncompressed_mb * 1024 * 1024
            if sum(m.file_size for m in members) > limit:
                reject("Archive expands beyond the configured limit.", "ARCHIVE_TOO_LARGE")
            seen, datasets = set(), {}
            for member in members:
                name = member.filename
                parts = PurePosixPath(name).parts
                if not parts or name.startswith("/") or "\\" in name or ":" in name or any(p in ("..", ".") for p in parts):
                    reject("Archive contains an unsafe path.")
                if any(not re.fullmatch(r"[\w .-]+", p) or p.endswith((".", " ")) for p in parts):
                    reject("Archive contains an unsupported path.")
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)) or member.flag_bits & 1:
                    reject("Links, special files and encrypted members are not supported.")
                canonical = name.lower().rstrip("/")
                if canonical in seen:
                    reject("Archive contains duplicate paths.")
                seen.add(canonical)
                if member.is_dir():
                    continue
                p = PurePosixPath(canonical)
                if p.suffix not in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                    reject("Archive contains an unexpected component.")
                datasets.setdefault(str(p.with_suffix("")), set()).add(p.suffix)
            if len(datasets) != 1:
                reject("Provide exactly one Shapefile dataset.")
            stem, suffixes = next(iter(datasets.items()))
            if not {".shp", ".shx", ".dbf"} <= suffixes:
                reject("Shapefile requires .shp, .shx and .dbf components.", "SHAPEFILE_COMPONENT_MISSING")
            if ".prj" not in suffixes:
                reject("The dataset does not define a CRS (.prj is missing).", "CRS_MISSING")
            written = 0
            for member in members:
                if member.is_dir():
                    continue
                target = destination / member.filename.lower()
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as output:
                    while chunk := source.read(65536):
                        written += len(chunk)
                        if written > limit:
                            reject("Archive expansion limit exceeded.", "ARCHIVE_TOO_LARGE")
                        output.write(chunk)
            return destination / (stem + ".shp")
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
        reject("The ZIP archive is corrupt or unsupported.")

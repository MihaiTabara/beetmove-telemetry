"""
Module with zip-manipulating functions to serve pushing telemetry artifacts
under maven.mozilla.org
"""
import os
import zipfile
import requests


from constants import (
    ZIP_MAX_COMPRESSION_RATIO,
    ZIP_MAX_SIZE_IN_MB,
)


def download_zip_archive(url, zip_path):
    # switch to asyncio
    ret = requests.get(url)

    # FIXME: switch to NamedTemporaryFile here
    with open(zip_path, 'wb') as f:
        f.write(ret.content)


def check_archive_itself(zip_path):
    zip_size = os.path.getsize(zip_path)
    zip_size_in_mb = zip_size // (1024 * 1024)

    if zip_size_in_mb > ZIP_MAX_SIZE_IN_MB:
        raise Exception(
            f"Archive {zip_path} is too big. Max accepted size (in MB): {zip_size_in_mb}"
        )

    if not zipfile.is_zipfile(zip_path):
        raise Exception(
            f"Archive {zip_path} is not a valid zip file"
        )


def _fetch_zip_metadata(zip_file):
    return {
        info.filename: {
            'compress_size': info.compress_size,
            'file_size': info.file_size,
        }
        for info in zip_file.infolist() if not info.is_dir()
    }


def extract_and_check_output_files(zip_file, relative_paths_in_archive):
    zip_path = zip_file.filename
    if not os.path.isabs(zip_path):
        raise Exception(f'Archive {zip_path} is not absolute path')

    extract_to = '{}.out'.format(zip_path)
    expected_full_paths_per_relative_path = {
        path_in_archive: os.path.join(extract_to, path_in_archive)
        for path_in_archive in relative_paths_in_archive
    }
    zip_file.extractall(extract_to)
    return expected_full_paths_per_relative_path


def ensure_files_in_archive_have_decent_sizes(zip_path, zip_metadata):
    for file_name, file_metadata in zip_metadata.items():
        compressed_size = file_metadata['compress_size']
        real_size = file_metadata['file_size']
        compressed_size_size_in_mb = compressed_size // (1024 * 1024)

        if compressed_size_size_in_mb > ZIP_MAX_SIZE_IN_MB:
            raise Exception(
                'In archive "{}", compressed file "{}" is too big. Max accepted size (in MB): {}. File size (in MB): {}'.format(
                    zip_path, file_name, ZIP_MAX_SIZE_IN_MB, compressed_size_size_in_mb
                )
            )

        compression_ratio = real_size / compressed_size
        if compression_ratio > ZIP_MAX_COMPRESSION_RATIO:
            raise Exception(
                'In archive "{}", file "{}" has a suspicious compression ratio. Max accepted: {}. Found: {}'.format(
                    zip_path, file_name, ZIP_MAX_COMPRESSION_RATIO, compression_ratio
                )
            )


def check_extract_and_delete_zip_archive(zip_path):
    # sanity check the archive itself
    check_archive_itself(zip_path)

    with zipfile.ZipFile(zip_path) as zip_file:
        zip_metadata = _fetch_zip_metadata(zip_file)
        relative_paths_in_archive = list(zip_metadata.keys())

        ensure_files_in_archive_have_decent_sizes(zip_path,
                                                  zip_metadata)
        extracted_files = extract_and_check_output_files(zip_file, relative_paths_in_archive)

    # os.remove(zip_path)
    return extracted_files

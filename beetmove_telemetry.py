import aiohttp
import asyncio
import boto3
import argparse
import json
import mimetypes
import os
import requests
import sys
import zipfile

from context import Context

ZIP_MAX_SIZE_IN_MB = 10
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


def check_extract_and_delete_zip_archive(zip_path):
    # sanity check the archive itself
    check_archive_itself(zip_path)

    with zipfile.ZipFile(zip_path) as zip_file:
        zip_metadata = _fetch_zip_metadata(zip_file)
        relative_paths_in_archive = list(zip_metadata.keys())

        # TODO: add ensure_files_in_archive_have_decent_sizes
        # TODO: ensure_all_expected_files_are_present_in_archive

        extracted_files = extract_and_check_output_files(zip_file, relative_paths_in_archive)
    # TODO: to uncomment this to remove the archive in the end
    # os.remove(zip_path)
    return extracted_files


async def _process_future_exceptions(tasks, raise_at_first_error):
    succeeded_results = []
    error_results = []

    if tasks:
        await asyncio.wait(tasks)
        for task in tasks:
            exc = task.exception()
            if exc:
                if raise_at_first_error:
                    raise exc
                else:
                    error_results.append(exc)
            else:
                succeeded_results.append(task.result())

    return succeeded_results, error_results


async def raise_future_exceptions(tasks):
    succeeded_results, _ = await _process_future_exceptions(tasks, raise_at_first_error=True)
    return succeeded_results


async def put(context, url, headers, abs_filename, session=None):
    session = session or context.session
    with open(abs_filename, "rb") as fh:
        async with session.put(url, data=fh, headers=headers, compress=False) as resp:
            log.info("put {}: {}".format(abs_filename, resp.status))
            response_text = await resp.text()
            if response_text:
                log.info(response_text)
            if resp.status not in (200, 204):
                raise Exception(
                    "Bad status {}".format(resp.status),
                )
    return resp


async def upload_to_s3(context, s3_key, path):
    product = 'telemetry'
    mime_type = mimetypes.guess_type(path)[0]
    if not mime_type:
        raise Exception(f"Unable to discover valid mime-type for path ({path}), "
                        "mimetypes.guess_type() returned {mime_type}")
    api_kwargs = {
        'Bucket': context.bucket,
        'Key': s3_key,
        'ContentType': mime_type,
    }
    headers = {
        'Content-Type': mime_type,
        'Cache-Control': 'public, max-age=%d' % CACHE_CONTROL_MAXAGE,
    }
    creds = context.config['bucket_config'][context.bucket]['credentials']
    s3 = boto3.client('s3', aws_access_key_id=creds['id'], aws_secret_access_key=creds['key'],)
    url = s3.generate_presigned_url('put_object', api_kwargs, ExpiresIn=1800, HttpMethod='PUT')

    # FIXME: add proper logging
    print(f"upload_to_s3: {path} -> s3://{context.bucket}/{s3_key}")
    await put(context, url, headers, path, session=context.session)


async def move_beets(context):
    # FIXME: add argapse cmd argument for version
    context.version = '0.0.1-TESTING7'

    uploads = []
    for file, local_path in context.extracted_files.items():
        # TODO: to fix via regex etraction here
        if 'forUnitTests' in file:
            destination = f"maven2/org/mozilla/telemetry/glean/{context.version}/{file}"
        else:
            destination = f"maven2/org/mozilla/telemetry/glean-forUnitTests/{context.version}/{file}"

        uploads.append(
            asyncio.ensure_future(
                upload_to_s3(context=context, s3_key=destination, path=local_path)
            )
        )

        await raise_future_exceptions(uploads)


async def async_main(context):
    # TODO: manually download artifacts from Github and bake them in a zip
    # TODO: bash script to do that for you

    # download the release archive from Github
    # TODO: uncomment this before final testing
    # download_zip_archive(context.release_url, context.zip_path)

    # explode zip archive
    context.extracted_files = check_extract_and_delete_zip_archive(context.zip_path)

    # XXX: do we need another session here?
    await move_beets(context)


async def _handle_asyncio_loop(async_main, context):
    async with aiohttp.ClientSession() as session:
        context.session = session
        try:
            await async_main(context)
        except Exception as exc:
            sys.exit(exc.exit_code)


def load_json_or_yaml(string, is_path=False, file_type='json',
                      message="Failed to load %(file_type)s: %(exc)s"):
    _load_fh = json.load
    _load_str = json.loads

    try:
        if is_path:
            with open(string, 'r') as fh:
                contents = _load_fh(fh)
        else:
            contents = _load_str(string)
        return contents
    except (OSError, ValueError, yaml.scanner.ScannerError) as exc:
        if exception is not None:
            repl_dict = {'exc': str(exc), 'file_type': file_type}
            raise exception(message % repl_dict)


def setup_mimetypes():
    mimetypes.init()
    # in py3 we must exhaust the map so that add_type is actually invoked
    list(map(
        lambda ext_mimetype: mimetypes.add_type(ext_mimetype[1], ext_mimetype[0]), MIME_MAP.items()
    ))


def sync_main(async_main, release_url, zip_path, script_config, bucket):
    context = Context()
    context.release_url = release_url
    context.zip_path = zip_path
    context.bucket = bucket

    context.config = {}
    context.config.update(load_json_or_yaml(script_config, is_path=True))

    setup_mimetypes()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_handle_asyncio_loop(async_main, context))


def main():
    parser = argparse.ArgumentParser(description='Telemetry upload')
    parser.add_argument('--release-url', dest='release_url',
                        action='store', required=True)
    parser.add_argument('--script-config', dest='script_config',
                        action='store', required=True)
    parser.add_argument('--bucket', dest='bucket',
                        action='store', required=True)

    args = parser.parse_args()
    if not args.release_url:
        exit(1)

    zip_path = '/tmp/target.zip'
    sync_main(async_main, args.release_url, zip_path,
              args.script_config, args.bucket)


__name__=='__main__' and main()

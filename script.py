""" Main script to push to maven.mozilla.org"""
import argparse
import asyncio
import aiohttp

from context import Context
from utils import (
    load_json_or_yaml, setup_mimetypes, _handle_asyncio_loop,
    upload_to_s3, raise_future_exceptions
)
from zip import (
    download_zip_archive,
    check_extract_and_delete_zip_archive,
)


GLEAN_PACKAGES = [
    'glean',
    'glean-forUnitTests',
    'glean-gradle-plugin'
]


async def move_beets(context):
    """TODO"""
    uploads = []
    for file, local_path in context.extracted_files.items():
        for package_name in GLEAN_PACKAGES:
            if file.startswith(f"{package_name}-{context.version}"):
                destination = f"maven2/org/mozilla/telemetry/{package_name}/{context.version}/{file}"
                break
        else:
            continue

        uploads.append(
            asyncio.ensure_future(
                upload_to_s3(context=context, s3_key=destination, path=local_path)
            )
        )

        await raise_future_exceptions(uploads)


async def async_main(context):
    """TODO"""
    # download the release archive from Github
    download_zip_archive(context.release_url, context.zip_path)

    # explode zip archive
    context.extracted_files = check_extract_and_delete_zip_archive(context.zip_path)

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        context.session = session
        await move_beets(context)


def sync_main(async_main, release_url, zip_path, script_config,
              bucket, version, dry_run):
    """TODO"""
    context = Context()
    context.release_url = release_url
    context.zip_path = zip_path
    context.bucket = bucket
    context.version = version
    context.dry_run = dry_run

    context.config = {}
    context.config.update(load_json_or_yaml(script_config, is_path=True))

    setup_mimetypes()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_handle_asyncio_loop(async_main, context))


def main():
    """TODO"""
    parser = argparse.ArgumentParser(description='Telemetry upload')
    parser.add_argument('--release-url', dest='release_url',
                        action='store', required=True)
    parser.add_argument('--script-config', dest='script_config',
                        action='store', required=True)
    parser.add_argument('--bucket', dest='bucket',
                        action='store', required=True)
    parser.add_argument('--version', dest='version',
                        action='store', required=True)
    parser.add_argument('--dry-run', default=False,
                        action='store_true')

    args = parser.parse_args()
    if not args.release_url:
        sys.exit(1)

    zip_path = '/tmp/target.zip'
    sync_main(async_main, args.release_url, zip_path,
              args.script_config, args.bucket, args.version,
              args.dry_run)


__name__ == '__main__' and main()

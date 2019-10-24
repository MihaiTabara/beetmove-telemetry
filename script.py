import aiohttp
import asyncio
import argparse

from context import Context
from utils import (
    load_json_or_yaml, setup_mimetypes, _handle_asyncio_loop,
    upload_to_s3, raise_future_exceptions
)
from zip import (
    download_zip_archive,
    check_extract_and_delete_zip_archive,
)


async def move_beets(context):
    # FIXME: add argapse cmd argument for version
    context.version = '19.0.0'

    uploads = []
    for file, local_path in context.extracted_files.items():
        # TODO: to fix via regex etraction here
        if 'forUnitTests' in file:
            destination = f"maven2/org/mozilla/telemetry/glean-forUnitTests/{context.version}/{file}"
        else:
            destination = f"maven2/org/mozilla/telemetry/glean/{context.version}/{file}"

        uploads.append(
            asyncio.ensure_future(
                upload_to_s3(context=context, s3_key=destination, path=local_path)
            )
        )

        await raise_future_exceptions(uploads)


async def async_main(context):
    # download the release archive from Github
    download_zip_archive(context.release_url, context.zip_path)

    # explode zip archive
    context.extracted_files = check_extract_and_delete_zip_archive(context.zip_path)

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        context.session = session
        await move_beets(context)


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


__name__ == '__main__' and main()

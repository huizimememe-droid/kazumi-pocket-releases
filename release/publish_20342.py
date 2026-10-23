"""Publish verified 20342 artifacts; signing credentials never leave the build machine."""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler

REPO = 'huizimememe-droid/kazumi-pocket-releases'
CONFIG = json.loads(Path(__file__).with_name('verified-20342.json').read_text(encoding='utf8'))
RELEASE_ID = CONFIG['releaseId']
TAG = 'pocket-20342'
APK = CONFIG['apk']['name']
APK_HASH = CONFIG['apk']['sha256']
SOURCE_HASH = CONFIG['source']['sha256']
MANIFEST_HASH = CONFIG['manifest']['sha256']


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith('https://'):
            raise ValueError('Refusing non-HTTPS redirect')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected:
            redirected.remove_header('Authorization')
        return redirected


def api(path, method='GET', data=None, binary=False):
    headers = {
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/octet-stream' if binary else 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'KazumiPocket-Release-Validation',
    }
    body = None if data is None else json.dumps(data).encode()
    if body is not None:
        headers['Content-Type'] = 'application/json'
    request = Request('https://api.github.com/repos/' + REPO + '/' + path,
                      data=body, headers=headers, method=method)
    with build_opener(SafeRedirect()).open(request, timeout=45) as response:
        raw = response.read(2 * 1024 * 1024)
    return raw if binary else (json.loads(raw) if raw else None)


def validate(release, manifest_bytes):
    if release['id'] != RELEASE_ID or release['tag_name'] != TAG:
        raise ValueError('Wrong release identity')
    assets = release['assets']
    apk = next(a for a in assets if a['name'] == APK)
    source = next(a for a in assets if a['name'] == CONFIG['source']['name'])
    manifest_asset = next(a for a in assets if a['name'] == 'update.json')
    for asset, digest, size in [(apk, APK_HASH, CONFIG['apk']['size']),
                                (source, SOURCE_HASH, CONFIG['source']['size']),
                                (manifest_asset, MANIFEST_HASH, CONFIG['manifest']['size'])]:
        if asset.get('digest') != 'sha256:' + digest or asset['size'] != size:
            raise ValueError('Uploaded artifact integrity mismatch')
    if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_HASH:
        raise ValueError('Downloaded manifest checksum mismatch')
    manifest = json.loads(manifest_bytes)
    expected = {
        'schemaVersion': 1, 'channel': 'kazumi-pocket',
        'packageId': 'com.predidit.kazumi.pocket',
        'version': '2.4.1', 'buildNumber': 20342,
        'sha256': APK_HASH,
        'apkUrl': f'https://github.com/{REPO}/releases/download/{TAG}/{APK}',
        'releaseUrl': f'https://github.com/{REPO}/releases/tag/{TAG}',
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError('Manifest is inconsistent with the app channel')
    return source


def main():
    release = api(f'releases/{RELEASE_ID}')
    if release['id'] != RELEASE_ID or release['tag_name'] != TAG:
        raise ValueError('Wrong release identity')
    local_manifest = Path(__file__).with_name('update.json').read_bytes()
    if hashlib.sha256(local_manifest).hexdigest() != MANIFEST_HASH:
        raise ValueError('Committed manifest checksum mismatch')
    existing = next((a for a in release['assets'] if a['name'] == 'update.json'), None)
    if existing is None or existing.get('state') != 'uploaded':
        if not release['draft']:
            raise ValueError('Refusing to modify published release assets')
        if existing:
            api(f"releases/assets/{existing['id']}", 'DELETE')
        request = Request(f'https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets?name=update.json',
            data=local_manifest, method='POST', headers={
                'Authorization': 'Bearer '+os.environ['GH_TOKEN'],
                'Content-Type': 'application/json', 'User-Agent': 'KazumiPocket-Release-Validation'})
        with build_opener(SafeRedirect()).open(request, timeout=45) as response:
            json.loads(response.read(1024*1024))
        release = api(f'releases/{RELEASE_ID}')
    manifest_id = next(a['id'] for a in release['assets'] if a['name'] == 'update.json')
    source = validate(release, api(f'releases/assets/{manifest_id}', binary=True))
    latest_before = api('releases/latest')
    if latest_before['tag_name'].startswith('pocket-') and int(latest_before['tag_name'].split('-')[-1]) > 20342:
        raise ValueError('Refusing to roll back a newer release')
    if release['draft']:
        release = api(f'releases/{RELEASE_ID}', 'PATCH', {
            'tag_name': TAG, 'draft': False, 'prerelease': False, 'make_latest': 'true',
        })
    latest = api('releases/latest')
    if latest['id'] != RELEASE_ID or latest['draft'] or latest['tag_name'] != TAG:
        raise ValueError('Latest release verification failed')
    print('Verified and published:', latest['html_url'])
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as output:
            output.write('APK, matching source and update manifest verified.\n\n' + latest['html_url'] + '\n')


if __name__ == '__main__':
    main()

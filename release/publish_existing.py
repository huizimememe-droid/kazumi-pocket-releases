"""Publish the already uploaded, verified 20341 release without signing secrets."""
import hashlib
import json
import os
from urllib.request import Request, build_opener, HTTPRedirectHandler

REPO = 'huizimememe-droid/kazumi-pocket-releases'
RELEASE_ID = 421454766
TAG = 'pocket-20341'
APK = 'KazumiPocket-2.4.1-independent-updates.apk'
APK_HASH = '1f15120bfd9a8604a673f9604a57ccce6cc6b2e261288e1f88b92ec83e16111a'
SOURCE_HASH = '84cb08d1fa90cb93a217e6cd5e6ebf352f98e433f3689d1e64527e082adb201c'
MANIFEST_HASH = '90efbb01bfcf4d5d1ceb96046f34d782f2a9e68f1a0cfa20a2f3b57ea4a230e7'


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
    return raw if binary else json.loads(raw)


def validate(release, manifest_bytes):
    if release['id'] != RELEASE_ID or release['tag_name'] != TAG:
        raise ValueError('Wrong release identity')
    assets = release['assets']
    apk = next(a for a in assets if a['name'] == APK)
    source = next(a for a in assets if a['name'].endswith('.zip'))
    manifest_asset = next(a for a in assets if a['name'] == 'update.json')
    for asset, digest, size in [(apk, APK_HASH, 33605490),
                                (source, SOURCE_HASH, 25878876),
                                (manifest_asset, MANIFEST_HASH, 791)]:
        if asset.get('digest') != 'sha256:' + digest or asset['size'] != size:
            raise ValueError('Uploaded artifact integrity mismatch')
    if hashlib.sha256(manifest_bytes).hexdigest() != MANIFEST_HASH:
        raise ValueError('Downloaded manifest checksum mismatch')
    manifest = json.loads(manifest_bytes)
    expected = {
        'schemaVersion': 1, 'channel': 'kazumi-pocket',
        'packageId': 'com.predidit.kazumi.pocket',
        'version': '2.4.1', 'buildNumber': 20341,
        'sha256': APK_HASH,
        'apkUrl': f'https://github.com/{REPO}/releases/download/{TAG}/{APK}',
        'releaseUrl': f'https://github.com/{REPO}/releases/tag/{TAG}',
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError('Manifest is inconsistent with the app channel')
    return source


def main():
    release = api(f'releases/{RELEASE_ID}')
    manifest_id = next(a['id'] for a in release['assets'] if a['name'] == 'update.json')
    source = validate(release, api(f'releases/assets/{manifest_id}', binary=True))
    if source['name'] != 'KazumiPocket-2.4.1-source.zip':
        api(f"releases/assets/{source['id']}", 'PATCH', {'name': 'KazumiPocket-2.4.1-source.zip'})
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

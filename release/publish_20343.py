import hashlib,json,os,sys
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
class SafeRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if not newurl.startswith('https://'):raise ValueError('Non-HTTPS redirect')
  redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
  if redirected:redirected.remove_header('Authorization')
  return redirected
urlopen=build_opener(SafeRedirect()).open
ROOT=Path(__file__).resolve().parents[1]
REPO='huizimememe-droid/kazumi-pocket-releases'
BUILD=20343
TAG=f'pocket-{BUILD}'
RELEASE_ID=423836096
def digest(data):return hashlib.sha256(data).hexdigest()
def assemble(publication):
 out=ROOT/'dist';out.mkdir(exist_ok=True)
 for f in publication['files']:
  name=f['name']
  if Path(name).name!=name or not name.endswith(('.apk','.zip')):raise ValueError('Invalid artifact name')
  h=hashlib.sha256();size=0
  with (out/name).open('wb') as w:
   for part in f['parts']:
    p=(ROOT/part).resolve()
    if not p.is_relative_to((ROOT/'payload/20343').resolve()):raise ValueError('Invalid payload path')
    b=p.read_bytes();h.update(b);size+=len(b);w.write(b)
  if h.hexdigest()!=f['sha256'] or size!=f['size']:raise ValueError('Artifact integrity mismatch')
 m=publication['update'];apk=next(f for f in publication['files'] if f['name'].endswith('.apk'))
 expected={'schemaVersion':1,'channel':'kazumi-pocket','packageId':'com.predidit.kazumi.pocket','buildNumber':BUILD,'version':'2.4.2','upstreamVersion':'2.4.2','sha256':apk['sha256'],'apkUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{apk["name"]}','releaseUrl':f'https://github.com/{REPO}/releases/tag/{TAG}'}
 if any(m.get(k)!=v for k,v in expected.items()):raise ValueError('Wrong manifest identity')
 (out/'update.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return out
def api(path,method='GET',data=None):
 b=None if data is None else json.dumps(data).encode()
 req=Request(f'https://api.github.com/repos/{REPO}/{path}',data=b,method=method,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'KazumiPocket-Verified-Publish'})
 with urlopen(req,timeout=60)as r:return json.loads(r.read())
def main():
 publication=json.loads((ROOT/'release/publication-20343.json').read_text(encoding='utf8'));out=assemble(publication)
 release=api(f'releases/{RELEASE_ID}')
 if release['id']!=RELEASE_ID or release['tag_name']!=TAG:raise ValueError('Wrong release')
 if not release['draft']:raise ValueError('Release already public; refusing changes')
 for file in [*(out/f['name'] for f in publication['files']),out/'update.json']:
  b=file.read_bytes();existing=next((a for a in release['assets'] if a['name']==file.name),None)
  if existing:
   if existing.get('digest')!='sha256:'+digest(b) or existing['size']!=len(b):raise ValueError('Existing draft asset differs')
   continue
  req=Request(f'https://uploads.github.com/repos/{REPO}/releases/{RELEASE_ID}/assets?name={file.name}',data=b,method='POST',headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Content-Type':'application/octet-stream','User-Agent':'KazumiPocket-Verified-Publish'})
  with urlopen(req,timeout=180)as r:asset=json.loads(r.read())
  if asset.get('digest')!='sha256:'+digest(b) or asset['size']!=len(b):raise ValueError('Upload integrity mismatch')
 latest=api('releases/latest')
 if latest['tag_name'].startswith('pocket-') and int(latest['tag_name'].split('-')[-1])>=BUILD:raise ValueError('Newer or equal release already latest')
 release=api(f'releases/{RELEASE_ID}','PATCH',{'draft':False,'prerelease':False,'make_latest':'true','body':publication['notes']})
 if release['draft'] or release['tag_name']!=TAG:raise ValueError('Publish failed')
 with urlopen(f'https://github.com/{REPO}/releases/latest/download/update.json',timeout=60)as r:live=r.read()
 if live!=(out/'update.json').read_bytes():raise ValueError('Public latest manifest mismatch')
 print('PUBLISHED_AND_PUBLIC_MANIFEST_VERIFIED',release['html_url'])
if __name__=='__main__':main()

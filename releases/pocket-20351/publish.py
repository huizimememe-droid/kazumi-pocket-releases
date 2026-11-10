import os,json,urllib.request,urllib.error,hashlib
repo=os.environ['GITHUB_REPOSITORY']
assert repo=='huizimememe-droid/kazumi-pocket-releases'
base='https://api.github.com/repos/'+repo
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Pocket-Release-20351'}
def api(path,data=None,method='GET'):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode()if data is not None else None,headers={**headers,'Content-Type':'application/json'},method=method)
 with urllib.request.urlopen(req,timeout=25)as r:return json.load(r)
folder='releases/pocket-20351/'
raw=open(folder+'update.json','rb').read()
manifest=json.loads(raw)
assert manifest['buildNumber']==20351 and manifest['channel']=='kazumi-pocket'
expected={a['name']:a for a in json.load(open(folder+'files.json'))}
assert len(raw)==expected['update.json']['size']
assert hashlib.sha256(raw).hexdigest()==expected['update.json']['sha256']
release=api('/releases/440034493')
assert release['tag_name']=='pocket-20351'
rid=release['id']
assets=api('/releases/'+str(rid)+'/assets?per_page=100')
for a in assets:
 if a['name'] in expected:
  spec=expected[a['name']]
  assert a['state']=='uploaded'and a['size']==spec['size']and a['digest']=='sha256:'+spec['sha256'],'Unexpected existing asset; never overwrite'
if not any(a['name']=='update.json'for a in assets):
 assert release['draft'],'Never modify a published incomplete release'
 upload=release['upload_url'].split('{')[0]
 assert upload=='https://uploads.github.com/repos/'+repo+'/releases/'+str(rid)+'/assets'
 req=urllib.request.Request(upload+'?name=update.json',data=raw,headers={**headers,'Content-Type':'application/octet-stream'},method='POST')
 with urllib.request.urlopen(req,timeout=25)as r:a=json.load(r)
 assert a['state']=='uploaded'and a['digest']=='sha256:'+expected['update.json']['sha256']
assets=api('/releases/'+str(rid)+'/assets?per_page=100')
missing=[]
for name,spec in expected.items():
 found=[a for a in assets if a['name']==name]
 if not found:missing.append(name);continue
 a=found[0]
 assert a['state']=='uploaded'and a['size']==spec['size']and a['digest']=='sha256:'+spec['sha256']
if missing:
 assert release['draft']
 print('DRAFT_READY='+json.dumps({'id':rid,'url':release['html_url'],'missing':missing}))
 print('No latest/update-channel change: waiting for the exact verified APK and source ZIP.')
else:
 release=api('/releases/'+str(rid),{'draft':False,'make_latest':'true'},'PATCH')
 assert not release['draft']
 print('PUBLISHED='+release['html_url'])

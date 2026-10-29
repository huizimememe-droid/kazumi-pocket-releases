"""Finish the authorized release only after all uploaded bytes match."""
import os,json,urllib.request,hashlib
repo=os.environ['GITHUB_REPOSITORY']
assert repo=='huizimememe-droid/kazumi-pocket-releases'
rid=427450751
base='https://api.github.com/repos/'+repo
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Pocket-Release-20349'}
def api(path,data=None,method='GET'):
 request=urllib.request.Request(base+path,data=json.dumps(data).encode()if data is not None else None,headers={**headers,'Content-Type':'application/json'},method=method)
 with urllib.request.urlopen(request,timeout=25)as response:return json.load(response)
expected={
 'KazumiPocket-2.4.2-nba-hd.apk':(33715066,'b6ffe280e3dd25e9d376ea87bb7c2ec170e9b138bda9c77423498fd58f75a1e8'),
 'KazumiPocket-2.4.2-nba-hd-source.zip':(25974010,'b59c9622f293dae4190ce0b78ceaa730ebba67741310ae6e401cc0ce08b7ebd6'),
 'update.json':(1198,'de7e8ec06b6cb1696cf43f05979076c77d90497bcdfb0edbd4262d6db76ad15a')}
release=api('/releases/'+str(rid))
assert release['tag_name']=='pocket-20349' and release['draft']
assets=api('/releases/'+str(rid)+'/assets?per_page=100')
for name in list(expected)[:2]:
 asset=next(a for a in assets if a['name']==name)
 assert asset['state']=='uploaded' and(asset['size'],asset['digest'])==(expected[name][0],'sha256:'+expected[name][1])
payload=open('releases/pocket-20349-update.json','rb').read()
assert(len(payload),hashlib.sha256(payload).hexdigest())==expected['update.json']
existing=[a for a in assets if a['name']=='update.json']
if existing:
 a=existing[0]
 assert a['state']=='uploaded' and(a['size'],a['digest'])==(expected['update.json'][0],'sha256:'+expected['update.json'][1]),'Unexpected existing manifest; no overwrite attempted'
else:
 upload=release['upload_url'].split('{')[0]
 assert upload=='https://uploads.github.com/repos/'+repo+'/releases/'+str(rid)+'/assets'
 request=urllib.request.Request(upload+'?name=update.json',data=payload,headers={**headers,'Content-Type':'application/octet-stream'},method='POST')
 with urllib.request.urlopen(request,timeout=25)as response:created=json.load(response)
 assert created['state']=='uploaded' and created['digest']=='sha256:'+expected['update.json'][1]
assets=api('/releases/'+str(rid)+'/assets?per_page=100')
for name,(size,digest)in expected.items():
 a=next(a for a in assets if a['name']==name)
 assert a['state']=='uploaded'and a['size']==size and a['digest']=='sha256:'+digest
print('ALL_THREE_ASSET_DIGESTS_MATCH',flush=True)
published=api('/releases/'+str(rid),{'draft':False,'make_latest':'true'},'PATCH')
assert not published['draft']and not published['prerelease']
print('PUBLISHED',published['html_url'],flush=True)

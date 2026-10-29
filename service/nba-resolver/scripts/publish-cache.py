"""Publish only validated public playback metadata to this app's own repository."""
import os,json,time,urllib.request,urllib.error,urllib.parse,base64,re
repo=os.environ['GITHUB_REPOSITORY']
assert repo=='huizimememe-droid/kazumi-pocket-releases'
known=set(re.findall(r"'([0-9]{8,20})'",open('service/nba-resolver/lib/verified.mjs').read()))
raw=open('nba-cache.json','rb').read()
assert len(raw)<500000
data=json.loads(raw);now=time.time()*1000
assert data['schema']==1 and abs(data['generatedAt']-now)<600000 and data['videos']
for mid,item in data['videos'].items():
 assert mid in known and item['id']==mid and item['expiresAt']>now+120000 and item['expiresAt']<now+86400000 and item['seconds']>=2400
 assert item['formats']
 for f in item['formats']:
  u=urllib.parse.urlparse(f['url'])
  assert f['height'] in (720,1080) and u.scheme=='https' and not u.username and not u.password and (u.hostname.endswith('.okcdn.ru') or u.hostname.endswith('.mycdn.me'))
endpoint='https://api.github.com/repos/'+repo+'/contents/data/nba-hd.json'
headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'PocketReplay-Cache'}
sha=None
try:
 with urllib.request.urlopen(urllib.request.Request(endpoint,headers=headers),timeout=20) as response: sha=json.load(response)['sha']
except urllib.error.HTTPError as e:
 if e.code!=404:raise
body={'message':'Refresh public NBA HD playback addresses','branch':'main','content':base64.b64encode(raw).decode()}
if sha:body['sha']=sha
request=urllib.request.Request(endpoint,data=json.dumps(body).encode(),headers={**headers,'Content-Type':'application/json'},method='PUT')
with urllib.request.urlopen(request,timeout=20) as response:
 result=json.load(response)
 print('Published public metadata',result['commit']['sha'])

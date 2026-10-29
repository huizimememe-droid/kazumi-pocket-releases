"""Release QA: public TLS, real container bytes, and a decoded game frame."""
import json,urllib.request,urllib.parse,subprocess,os,time
catalog=json.load(open('data/nba-catalog.json'))
cache=json.load(open('data/nba-hd.json'))
os.makedirs('probe-results',exist_ok=True)
report=[]
for game in catalog['games']:
 result={'id':game['id'],'title':game['title'],'expectedHeight':game['qualityHeight']}
 try:
  part=game['parts'][0]
  formats=cache['videos'][part['videoId']]['formats']if game['provider']=='ok'else part['formats']
  stream=max(formats,key=lambda f:f['height']==1080)['url']
  request=urllib.request.Request(stream,headers={'Range':'bytes=0-15','User-Agent':'PocketReplay/20349'})
  with urllib.request.urlopen(request,timeout=10)as response:
   header=response.read(12)
   assert response.status in (200,206)
   assert response.geturl()==stream,'redirect requires native preflight review'
   assert header[:4]==bytes.fromhex('1a45dfa3')or header[4:8]==b'ftyp','unexpected video container'
   result.update(tlsVerified=True,containerHeader=header.hex(),rangeStatus=response.status)
  target='probe-results/'+game['id']+'.jpg'
  position=int(game['seconds']*.85)
  frame=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror','-rw_timeout','10000000','-ss',str(position),'-i',stream,'-frames:v','1','-vf','scale=640:-1','-q:v','6','-y',target],capture_output=True,text=True,timeout=30)
  assert frame.returncode==0 and not frame.stderr.strip(),frame.stderr[-500:]
  result.update(passed=True,proof=target,position=position)
 except Exception as e:result.update(passed=False,error=str(e))
 report.append(result)
open('probe-results/release-qa.json','w').write(json.dumps(report,ensure_ascii=False,indent=2))
print('RELEASE_QA='+json.dumps(report,ensure_ascii=False),flush=True)
assert all(r.get('passed')for r in report),'A release source failed QA'

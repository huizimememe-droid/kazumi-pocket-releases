"""Anonymous public-video checks only; no login, cookies, DRM or CAPTCHA handling."""
import json,re,html,subprocess,urllib.request,urllib.parse,os,time
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'identity','Referer':'https://basketball-video.com/'})
 with urllib.request.urlopen(req,timeout=12)as response:
  return response.read(2500000).decode('utf8',errors='replace')
def links(text):
 return [(urllib.parse.urljoin('https://basketball-video.com/',m[0]),html.unescape(re.sub('<[^>]+>','',m[1])).strip()) for m in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',text,re.I)]
def inspect_ok(url):
 page=get(url);vid=re.search(r'/(\d+)',urllib.parse.urlparse(url).path).group(1)
 if 'Access to this video is restricted' in page:raise ValueError('login required')
 data=None
 for match in re.finditer(r'data-options=(["\'])(.*?)\1',page,re.S):
  if vid not in match[2]:continue
  value=json.loads(html.unescape(match[2]));
  if 'flashvars'in value:data=value['flashvars'];break
 if data is None:raise ValueError('no anonymous player metadata')
 meta=data.get('metadata')
 if isinstance(meta,str):meta=json.loads(meta)
 if not meta:
  endpoint=urllib.parse.unquote(data.get('metadataUrl',''))
  if urllib.parse.urlparse(endpoint).hostname not in ('ok.ru','www.ok.ru'):raise ValueError('unsupported metadata host')
  meta=json.loads(get(endpoint))
 if meta.get('paymentInfo'):raise ValueError('payment metadata present')
 movie=meta.get('movie',{});duration=int(movie.get('duration',0))
 if duration<1800:raise ValueError('not a full game')
 if re.search(r'2K\d|gameplay|simulation',movie.get('title',''),re.I):raise ValueError('simulation')
 qualities={'full':1080,'hd':720,'sd':480,'low':360,'lowest':240,'mobile':144,'quad':1440,'ultra':2160}
 formats=sorted((v for v in meta.get('videos',[])if qualities.get(v.get('name'),0)>=720),key=lambda v:(qualities.get(v.get('name'))==1080,qualities.get(v.get('name'),0)),reverse=True)
 checks=[]
 for fmt in formats[:2]:
  stream=fmt['url']
  if not stream.startswith('https://'):continue
  try:
   probe=subprocess.run(['ffprobe','-v','error','-rw_timeout','10000000','-show_entries','stream=codec_type,width,height,avg_frame_rate:format=duration,bit_rate','-of','json',stream],capture_output=True,text=True,timeout=28)
   if probe.returncode:raise ValueError(probe.stderr[-500:])
   info=json.loads(probe.stdout);video=next(s for s in info['streams']if s.get('codec_type')=='video')
   actual=float(info['format'].get('duration',0))
   if video.get('height',0)<720 or actual<1800 or actual<duration*.9:raise ValueError('low quality or truncated')
   for point in [30,int(actual/2),max(30,int(actual)-120)]:
    result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror','-err_detect','explode','-rw_timeout','10000000','-ss',str(point),'-i',stream,'-t','3','-map','0:v:0','-map','0:a:0?','-fps_mode:v','passthrough','-enc_time_base:v','1:1000000','-f','null','-'],capture_output=True,text=True,timeout=30)
    if result.returncode or result.stderr.strip():raise ValueError('decode/seek failed: '+result.stderr[-500:])
   return {'id':vid,'provider':'ok.ru','page':url,'title':movie.get('title'),'seconds':actual,'width':video['width'],'height':video['height'],'fps':video.get('avg_frame_rate'),'bitrate':info['format'].get('bit_rate'),'stream':stream,'format':fmt.get('name'),'anonymous':True,'strictDecodeAndThreeSeeks':True}
  except Exception as e:checks.append({'format':fmt.get('name'),'error':str(e)})
 raise ValueError(json.dumps(checks) if checks else 'no anonymous HD format')
report={'tested':[],'passed':[],'started':time.time()};queue=['https://ok.ru/videoembed/15464523565624','https://ok.ru/videoembed/15464539884088','https://ok.ru/videoembed/15779847539372']
try:
 q=urllib.parse.urlencode({'q':'title:NBA AND mediatype:movies AND (720p OR 1080p)','output':'json','rows':'12','fl[]':['identifier','title']},doseq=True)
 report['archiveCandidates']=json.loads(get('https://archive.org/advancedsearch.php?'+q)).get('response',{}).get('docs',[])
except Exception as e:report['archiveError']=str(e)
for url in dict.fromkeys(queue):
 try:
  result=inspect_ok(url);report['passed'].append(result);report['tested'].append({'url':url,'passed':True})
 except Exception as e:report['tested'].append({'url':url,'error':str(e)})

def inspect_archive(identifier):
 meta=json.loads(get('https://archive.org/metadata/'+identifier))
 if meta.get('is_dark') or str(meta.get('metadata',{}).get('access-restricted-item','')).lower()=='true':raise ValueError('restricted archive item')
 host=meta.get('d1','')
 if not re.fullmatch(r'ia\d+\.us\.archive\.org',host):raise ValueError('unknown public archive server')
 files=[f for f in meta.get('files',[])if re.search(r'\.(mp4|mkv)os.makedirs('probe-results',exist_ok=True)
open('probe-results/report.json','w').write(json.dumps(report,ensure_ascii=False,indent=2))
print('HD_PROBE_REPORT='+json.dumps(report,ensure_ascii=False),flush=True)
,f.get('name',''),re.I)and not f.get('private')]
 files.sort(key=lambda f:(f.get('source')=='original',int(f.get('size',0))),reverse=True)
 errors=[]
 for f in files[:3]:
  stream='https://'+host+meta['dir']+'/'+urllib.parse.quote(f['name'])
  try:
   result=subprocess.run(['ffprobe','-v','error','-rw_timeout','12000000','-show_entries','stream=codec_type,codec_name,width,height,avg_frame_rate:format=duration,bit_rate','-of','json',stream],capture_output=True,text=True,timeout=35)
   if result.returncode:raise ValueError(result.stderr[-350:])
   info=json.loads(result.stdout);v=next(x for x in info['streams']if x.get('codec_type')=='video');audio=next(x for x in info['streams']if x.get('codec_type')=='audio')
   duration=float(info['format'].get('duration',0))
   if min(v.get('width',0),v.get('height',0))<720 or duration<3600:raise ValueError('not a HD full game')
   if v.get('codec_name')not in ('h264','hevc')or audio.get('codec_name')not in ('aac','mp3'):raise ValueError('not a standard mobile playback codec')
   for point in [30,int(duration/2),int(duration)-120]:
    decoded=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror','-err_detect','explode','-rw_timeout','12000000','-ss',str(point),'-i',stream,'-t','3','-map','0:v:0','-map','0:a:0','-fps_mode:v','passthrough','-enc_time_base:v','1:1000000','-f','null','-'],capture_output=True,text=True,timeout=35)
    if decoded.returncode or decoded.stderr.strip():raise ValueError('decode/seek: '+decoded.stderr[-350:])
   return {'identifier':identifier,'page':'https://archive.org/details/'+identifier,'title':meta.get('metadata',{}).get('title'),'url':stream,'filename':f['name'],'seconds':duration,'width':v['width'],'height':v['height'],'fps':v.get('avg_frame_rate'),'videoCodec':v['codec_name'],'audioCodec':audio['codec_name'],'bitrate':info['format'].get('bit_rate'),'anonymous':True,'strictDecodeAndThreeSeeks':True}
  except Exception as e:errors.append({'file':f['name'],'error':str(e)})
 raise ValueError(json.dumps(errors)if files else 'no public media files')
try:
 report['archivePassed']=[inspect_archive('nba.-2015.06.04.-cavaliers.vs.-warriors.-720p.-hdtv.-30fps.x-264-reborn-4-hd')]
except Exception as e:report['archiveMediaError']=str(e)

report['finished']=time.time();os.makedirs('probe-results',exist_ok=True)
open('probe-results/report.json','w').write(json.dumps(report,ensure_ascii=False,indent=2))
print('HD_PROBE_REPORT='+json.dumps(report,ensure_ascii=False),flush=True)

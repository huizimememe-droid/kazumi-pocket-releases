import {verifiedIds} from '../lib/verified.mjs';
import {resolvePublic} from '../lib/resolve.mjs';
import {readFile,writeFile} from 'node:fs/promises';
const now=Date.now();
let old={videos:{}};
try {old=JSON.parse(await readFile('data/nba-hd.json','utf8'));} catch {}
const videos={};
for (const id of verifiedIds) {
 try {videos[id]=await resolvePublic(id);console.log('Resolved',id,videos[id].formats.map(f=>f.height).join('/'));}
 catch(error) {
  console.error('Unavailable',id,error.name);
  if(old.videos?.[id]?.expiresAt > now+3600000) videos[id]=old.videos[id];
 }
}
if(!Object.keys(videos).length) throw new Error('No usable public HD addresses; retaining previous public cache');
await writeFile('nba-cache.json',JSON.stringify({schema:1,generatedAt:now,videos},null,2));

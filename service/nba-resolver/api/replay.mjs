import {verifiedIds} from '../lib/verified.mjs';
import {resolvePublic} from '../lib/resolve.mjs';

// Public metadata only. No video relay, accounts, cookies, or arbitrary URL proxy.
export async function GET(request) {
  const id = new URL(request.url).searchParams.get('id') ?? '';
  if (!/^\d{8,20}$/.test(id) || !verifiedIds.has(id))
    return Response.json({error:'UNKNOWN_GAME'}, {status:404});
  try {
    const result = await resolvePublic(id);
    return Response.json(result, {headers:{
      'Cache-Control':'public, max-age=60, s-maxage=120',
      'X-Content-Type-Options':'nosniff'
    }});
  } catch (error) {
    // Never log signed media URLs or visitor details.
    console.error('replay_resolve_failed', /^[A-Z_]+$/.test(error.message) ? error.message : error.name);
    return Response.json({error:'HD_SOURCE_TEMPORARILY_UNAVAILABLE'},
      {status:503, headers:{'Cache-Control':'no-store'}});
  }
}

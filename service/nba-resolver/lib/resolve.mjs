const entities = {quot:'"',apos:"'",amp:'&',lt:'<',gt:'>'};
function unescapeHTML(s) {
  return s.replace(/&(quot|apos|amp|lt|gt|#\d+|#x[\da-f]+);/gi, (all, key) => {
    if (key[0] !== '#') return entities[key.toLowerCase()] ?? all;
    const n = key[1].toLowerCase() === 'x' ? parseInt(key.slice(2),16) : +key.slice(1);
    return n > 0 && n <= 0x10ffff ? String.fromCodePoint(n) : all;
  });
}
export function metadataFromHTML(html, id) {
  for (const match of html.matchAll(/data-options=(["'])([\s\S]*?)\1/g)) {
    if (id && !match[2].includes(id)) continue;
    try {
      const options = JSON.parse(unescapeHTML(match[2]));
      let data = options.flashvars?.metadata;
      if (typeof data === 'string') data = JSON.parse(data);
      if (data && typeof data === 'object') return data;
    } catch {}
  }
  throw new Error('NO_PUBLIC_METADATA');
}
export function publicFormats(data, id, now = Date.now()) {
  if (data.paymentInfo || !data.movie || +data.movie.duration < 2400)
    throw new Error('NOT_PUBLIC_FULL_GAME');
  const heights = {full:1080, hd:720};
  const formats = [];
  let expiresAt = now + 20 * 3600000;
  for (const v of data.videos ?? []) {
    const height = heights[v.name];
    if (!height || typeof v.url !== 'string') continue;
    let url;
    try { url = new URL(v.url); } catch { continue; }
    if (url.protocol !== 'https:' || url.username || url.password ||
        !/(^|\.)(okcdn\.ru|mycdn\.me|vkuser\.net)$/.test(url.hostname)) continue;
    const expiration = Number(url.searchParams.get('expires'));
    if (expiration > 0) {
      const ms = expiration < 1e12 ? expiration * 1000 : expiration;
      if (ms < now + 120000) continue;
      expiresAt = Math.min(expiresAt, ms - 60000);
    }
    formats.push({height, label:height+'p', url:url.href});
  }
  formats.sort((a,b) => b.height-a.height);
  if (!formats.length) throw new Error('NO_HD_PUBLIC_STREAM');
  return {schema:1, id, seconds:+data.movie.duration, formats, expiresAt};
}
export async function resolvePublic(id, fetcher = fetch) {
  const response = await fetcher('https://ok.ru/videoembed/'+id, {
    signal:AbortSignal.timeout(9000), redirect:'error',
    headers:{'User-Agent':'Mozilla/5.0 PocketReplay/20349','Accept':'text/html'}
  });
  if (!response.ok) throw new Error('UPSTREAM_UNAVAILABLE');
  const html = await response.text();
  if (html.length > 3000000) throw new Error('RESPONSE_TOO_LARGE');
  return publicFormats(metadataFromHTML(html, id), id);
}

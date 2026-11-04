'use strict';
async function api(path, body) {
  const r = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',

    headers: body === undefined ? {} : {
      'Content-Type': 'application/json'
    },

    body: body === undefined ? undefined : JSON.stringify(body)
  });

  const x = await r.json();

  if (!r.ok)
    throw Error(x.error || 'Request failed');

  return x;
}

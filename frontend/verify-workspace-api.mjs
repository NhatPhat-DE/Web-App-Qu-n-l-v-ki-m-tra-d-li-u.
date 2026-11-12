// Boundary checks for unreadable responses; production always calls the real API.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'

const dataURL = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
const business = dataURL(stripTypeScriptTypes(fs.readFileSync('src/api/business.ts', 'utf8')))
const source = stripTypeScriptTypes(fs.readFileSync('src/workspace/api.ts', 'utf8')).replace("'../api/business'", JSON.stringify(business))
const { request, allPages } = await import(dataURL(source))
const nativeFetch = globalThis.fetch
try {
  for (const body of ['broken json', 'null', '']) {
    globalThis.fetch = async () => new Response(body, { status: 200 })
    await assert.rejects(request('/api/datasets'), /Không đọc được phản hồi/)
  }
  globalThis.fetch = async () => new Response(JSON.stringify({ error: { message: 'Dịch vụ chưa sẵn sàng.' } }), { status: 503 })
  await assert.rejects(request('/api/datasets'), /Dịch vụ chưa sẵn sàng/)
  globalThis.fetch = async () => { throw new TypeError('network unavailable') }
  await assert.rejects(request('/api/datasets'), /Mất kết nối với hệ thống/)
  const calls = []
  globalThis.fetch = async url => {
    const page = Number(new URL(url, 'http://127.0.0.1').searchParams.get('page'))
    calls.push(page)
    return new Response(JSON.stringify({ items: [{ id: page }], total: 2, page, page_size: 100 }))
  }
  assert.deepEqual(await allPages('/api/datasets'), [{ id: 1 }, { id: 2 }])
  assert.deepEqual(calls, [1, 2])
  const controller = new AbortController(); controller.abort()
  await assert.rejects(request('/api/datasets', controller.signal), error => error.name === 'AbortError')
  console.log('PASS: unreadable/empty/null JSON, server error, network translation, complete pagination and request cancellation.')
} finally { globalThis.fetch = nativeFetch }

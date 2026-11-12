#!/usr/bin/env bun
/**
 * The report's back-channel to the agent that built it.
 *
 *   bun -i report-serve.ts <report.html> [--root <project>] [--port <n>]
 *     Serves the report's folder on 127.0.0.1 and mounts the annotation inbox on /__annotations, stored in
 *     <project>/.data/annotations (the store `annotations_list` / `annotations_resolve` read). Prints the URL to open;
 *     its `#k=<token>` is the only key the inbox accepts. The page enables comments and decisions only after
 *     GET /__annotations/access answers {allowed:true} with that token.
 *     One server per folder: every report in it (all versions) is served, and all share the inbox. When a server for the
 *     folder already runs, the call prints the new report's URL on that server and exits. Port and token are kept in
 *     .data/annotations/.report-serve.json, so a restarted server takes them up again and open tabs reconnect.
 *     Comments and decision answers are stored on the report: <stem>.comments.json next to <stem>.html, read and
 *     written through /__comments?page=<path> (same token). Every reader of one report shares them and one inbox session.
 *
 *   bun -i report-serve.ts wait [--root <project>]
 *     Blocks until the inbox holds an open item no watcher has dispatched yet, marks it seen in
 *     .data/annotations/.watch-seen (shared with the omp extension's /annotations watch), prints the items as
 *     markdown and exits. Run it as a background job: its exit wakes the agent.
 *
 * `-i` lets Bun fetch the pinned inbox package when no node_modules provides it.
 */
import { existsSync } from 'node:fs'
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto'
import { appendFile, chmod, mkdir, readFile, realpath, rename, writeFile } from 'node:fs/promises'
import { basename, dirname, join, resolve, sep } from 'node:path'
import { openFileInbox, renderMarkdown } from '@skaile/forge-annotation-inbox@2.2.0/inbox'
import { handleInboxRequest } from '@skaile/forge-annotation-inbox@2.2.0/server'

const BASE = '/__annotations'
const COMMENTS = '/__comments'
const SEEN = join('.data', 'annotations', '.watch-seen')
const STATE = join('.data', 'annotations', '.report-serve.json')

/** Per served folder: its port, token and the pid of the server that last held it. */
type Served = Record<string, { port: number, token: string, pid: number }>

/** One reader comment, as the page's anNew builds it: `src` is the JSON pointer of the commented block. */
interface Comment { id: string, src: string, sec: string, quote: string, before: string, after: string, anchor: string, comment: string, at: string, edited?: string }
/** A decision block's answer: the chosen option id and the optional comment. */
interface Answer { opt: string, text: string, at: number }
/** <stem>.comments.json: everything readers said on one report. */
interface Sidecar { report: string, comments: Comment[], decisions: Record<string, Answer> }

const str = (v: unknown, max: number): v is string => typeof v === 'string' && v.length <= max

function asComment(v: unknown): Comment | null {
  if (!v || typeof v !== 'object') return null
  const c = v as Record<string, unknown>
  if (!str(c.id, 40) || !/^[a-z0-9]{4,40}$/.test(c.id) || !str(c.src, 300) || !c.src.startsWith('sections/')) return null
  if (!str(c.comment, 5000) || !c.comment.trim() || !str(c.at, 40)) return null
  const out: Comment = { id: c.id, src: c.src, sec: '', quote: '', before: '', after: '', anchor: '', comment: c.comment.trim(), at: c.at }
  for (const [k, max] of [['sec', 300], ['quote', 1000], ['before', 400], ['after', 400], ['anchor', 200]] as const) {
    if (c[k] === undefined) continue
    if (!str(c[k], max)) return null
    out[k] = c[k]
  }
  if (str(c.edited, 40)) out.edited = c.edited
  return out
}

function asAnswer(v: unknown): Answer | null {
  if (!v || typeof v !== 'object') return null
  const a = v as Record<string, unknown>
  if (!str(a.opt, 64) || !/^[a-z0-9-]{1,32}$/.test(a.opt) || (a.text !== undefined && !str(a.text, 5000))) return null
  return { opt: a.opt, text: typeof a.text === 'string' ? a.text.trim() : '', at: typeof a.at === 'number' ? a.at : Date.now() }
}

async function readSidecar(file: string, report: string): Promise<Sidecar> {
  const out: Sidecar = { report, comments: [], decisions: {} }
  let v: unknown
  try {
    v = JSON.parse(await readFile(file, 'utf8'))
  }
  catch (e) {
    if (e instanceof Error && 'code' in e && e.code === 'ENOENT') return out
    throw e
  }
  const s = (v && typeof v === 'object' ? v : {}) as Record<string, unknown>
  if (Array.isArray(s.comments)) for (const c of s.comments) { const ok = asComment(c); if (ok) out.comments.push(ok) }
  if (s.decisions && typeof s.decisions === 'object') {
    for (const [id, a] of Object.entries(s.decisions)) { const ok = asAnswer(a); if (ok && /^[a-z0-9-]{1,32}$/.test(id)) out.decisions[id] = ok }
  }
  return out
}

/** Write via a temp file and rename, so a reader (agent or page) never sees half a file. */
async function writeSidecar(file: string, s: Sidecar): Promise<void> {
  const tmp = `${file}.${process.pid}.tmp`
  await writeFile(tmp, JSON.stringify(s, null, 1) + '\n')
  await rename(tmp, file)
}

/** One change to a sidecar at a time: two readers saving at once must not drop each other's comment. */
let sidecarChain: Promise<unknown> = Promise.resolve()
function serial<T>(f: () => Promise<T>): Promise<T> {
  const p = sidecarChain.then(f)
  sidecarChain = p.catch(() => {})
  return p
}

/**
 * GET answers the sidecar plus the inbox session all readers of this report publish into.
 * POST applies one change and answers the same: {comment} adds or replaces by id, {delete: id}, {clear: true},
 * {decision: id, answer: {opt, text}}.
 */
async function comments(req: Request, html: string, rel: string): Promise<Response> {
  const file = html.replace(/\.html?$/i, '') + '.comments.json'
  const session = 'r' + createHash('sha256').update(html).digest('hex').slice(0, 23)
  const json = (s: Sidecar) => Response.json({ session, comments: s.comments, decisions: s.decisions }, { headers: { 'cache-control': 'no-store' } })
  if (req.method === 'GET') return json(await readSidecar(file, rel))
  if (req.method !== 'POST') return new Response('GET or POST', { status: 405 })
  let body: Record<string, unknown>
  try {
    const v: unknown = await req.json()
    if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Error('not an object')
    body = v as Record<string, unknown>
  }
  catch {
    return new Response('expected a JSON object', { status: 400 })
  }
  return serial(async () => {
    const s = await readSidecar(file, rel)
    if ('comment' in body) {
      const c = asComment(body.comment)
      if (!c) return new Response('comment: needs id, src, comment, at', { status: 400 })
      const i = s.comments.findIndex(x => x.id === c.id)
      if (i < 0) s.comments.push(c)
      else s.comments[i] = { ...c, at: s.comments[i]!.at, edited: new Date().toISOString() }
    }
    else if (typeof body.delete === 'string') s.comments = s.comments.filter(x => x.id !== body.delete)
    else if (body.clear === true) s.comments = []
    else if (typeof body.decision === 'string' && /^[a-z0-9-]{1,32}$/.test(body.decision)) {
      const a = asAnswer(body.answer)
      if (!a) return new Response('answer: needs opt', { status: 400 })
      s.decisions[body.decision] = { ...a, at: Date.now() }
    }
    else return new Response('expected comment, delete, clear or decision', { status: 400 })
    await writeSidecar(file, s)
    console.log(`${new Date().toISOString()} ${COMMENTS} ${rel}`)
    return json(s)
  })
}

async function readState(): Promise<Served> {
  let v: unknown
  try {
    v = JSON.parse(await readFile(join(root, STATE), 'utf8'))
  }
  catch {
    return {}
  }
  const out: Served = {}
  if (!v || typeof v !== 'object' || Array.isArray(v)) return out
  for (const [dir, e] of Object.entries(v)) {
    if (e && typeof e === 'object' && 'port' in e && 'token' in e && 'pid' in e
      && typeof e.port === 'number' && typeof e.token === 'string' && typeof e.pid === 'number') {
      out[dir] = { port: e.port, token: e.token, pid: e.pid }
    }
  }
  return out
}

async function writeState(s: Served): Promise<void> {
  await mkdir(dirname(join(root, STATE)), { recursive: true })
  await writeFile(join(root, STATE), JSON.stringify(s, null, 2), { mode: 0o600 })
  await chmod(join(root, STATE), 0o600)
}

/** Does a live report-serve answer on `port` with `token`? */
async function alive(port: number, token: string): Promise<boolean> {
  try {
    const r = await fetch(`http://127.0.0.1:${port}${BASE}/access`, { headers: { authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(1500) })
    return r.ok && (await r.json()).allowed === true
  }
  catch {
    return false
  }
}

function arg(name: string): string | undefined {
  const i = process.argv.indexOf(name)
  return i > 0 ? process.argv[i + 1] : undefined
}

function die(msg: string): never {
  console.error(`report-serve: ${msg}`)
  process.exit(1)
}

const root = resolve(arg('--root') ?? process.cwd())
const inbox = openFileInbox(root)

async function readSeen(): Promise<Set<string>> {
  try {
    return new Set((await readFile(join(root, SEEN), 'utf8')).split('\n').filter(Boolean))
  }
  catch (e) {
    if (e instanceof Error && 'code' in e && e.code === 'ENOENT') return new Set()
    throw e
  }
}

async function wait(): Promise<void> {
  for (;;) {
    const seen = await readSeen()
    let fresh = (await inbox.list({ status: 'open' })).filter(i => !seen.has(i.inboxId))
    if (fresh.length) {
      await Bun.sleep(500) // a publish writes item by item: let it finish
      fresh = (await inbox.list({ status: 'open' })).filter(i => !seen.has(i.inboxId))
      if (fresh.length) {
        await mkdir(dirname(join(root, SEEN)), { recursive: true })
        await appendFile(join(root, SEEN), fresh.map(i => i.inboxId).join('\n') + '\n')
        console.log(`New answers from the report reader (${fresh.length}). Act on each, then call annotations_resolve `
          + `with its inboxId (implemented, or rejected with a resolution); the page shows your resolution.\n`)
        console.log(renderMarkdown(fresh, 'open', { resolveVia: 'tool' }))
        return
      }
    }
    await Bun.sleep(1000)
  }
}

/** A port that stays the same for one project and report folder, so the page's origin (and its localStorage) survives restarts. */
function stablePort(key: string): number {
  let h = 0
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return 47000 + (h % 1000)
}

type Env = 'local' | 'platform' | 'container'

/**
 * Where this process runs; `--env` or REPORT_SERVE_ENV override it. `platform`: a skaile platform session container
 * (SKAILE_SESSION_ID plus a container marker, the workspaces runner's own test) or a sibling preview container
 * (SKAILE_PREVIEW_BASE). `container`: any other container. See .scratch/research/report-serve-workspaces.md.
 */
function detectEnv(): Env {
  const forced = arg('--env') ?? process.env.REPORT_SERVE_ENV
  if (forced === 'local' || forced === 'platform' || forced === 'container') return forced
  if (forced) die(`--env must be local, platform or container, not ${forced}`)
  const e = process.env
  const boxed = existsSync('/.dockerenv') || existsSync('/run/.containerenv') || Boolean(e.KUBERNETES_SERVICE_HOST)
  if (e.SKAILE_PREVIEW_BASE || (e.SKAILE_SESSION_ID && boxed)) return 'platform'
  return boxed || e.REMOTE_CONTAINERS || e.CODESPACES ? 'container' : 'local'
}

async function serve(file: string): Promise<void> {
  const env = detectEnv()
  if (env === 'platform') {
    // The platform's Preview proxy rewrites Host and Origin, strips Authorization and the URL fragment, and cannot reach
    // 127.0.0.1 here: a page served this way would never see the channel. Say so instead of printing a dead URL.
    console.error('report-serve: env platform (skaile workspace container): the reader\'s browser cannot reach this server, so the report has no agent channel here.\n'
      + '  Show the report as a static preview (platform.list_previews / skaile.preview.json); comments and decision forms stay disabled on it.\n'
      + '  Ask each decision with platform.request_decision instead; its outcome arrives as a new turn. Override with --env local if you know better.')
    process.exit(2)
  }
  const page = resolve(file)
  if (!(await Bun.file(page).exists())) die(`no such file ${page}`)
  const dir = await realpath(dirname(page))
  if (env === 'container') {
    console.error('report-serve: env container: 127.0.0.1 here is reachable from the host browser only through a forward of the same port to localhost '
      + '(VS Code / devcontainer port forwarding). A forward to another host or port (Codespaces, docker -p) fails the Host check and the page stays disabled.')
  }
  const rel = page.slice(dir.length + 1).split(sep).map(encodeURIComponent).join('/')
  const state = await readState()
  const prev = state[dir]
  if (prev && !arg('--port') && await alive(prev.port, prev.token)) {
    console.log(`report: http://127.0.0.1:${prev.port}/${rel}#k=${prev.token}`)
    console.log(`inbox: ${join(root, '.data', 'annotations')}`)
    console.log(`served by the running report-serve (pid ${prev.pid}) for ${dir}`)
    return
  }
  const token = prev?.token ?? randomBytes(24).toString('base64url')
  const want = Buffer.from(token)
  const authorised = (h: string | null) => {
    const got = Buffer.from(/^Bearer\s+(.+)$/i.exec(h ?? '')?.[1]?.trim() ?? '')
    return got.length === want.length && timingSafeEqual(got, want)
  }

  /** A URL path (percent-encoded) to a file inside the served folder, or null; `/` and `dir/` mean the report's own name. */
  const inFolder = async (path: string): Promise<string | null> => {
    let rel: string
    try {
      rel = decodeURIComponent(path)
    }
    catch {
      return null
    }
    try {
      const target = await realpath(resolve(dir, '.' + (rel.endsWith('/') ? rel + basename(page) : rel))) // a symlink must not lead out either
      return target.startsWith(dir + sep) ? target : null
    }
    catch {
      return null
    }
  }

  const handler = async (req: Request, port: number): Promise<Response> => {
    const url = new URL(req.url)
    // DNS rebinding: a foreign site resolving its name to 127.0.0.1 still sends its own Host
    const host = req.headers.get('host')
    if (host !== `127.0.0.1:${port}` && host !== `localhost:${port}`) return new Response('bad host', { status: 421 })
    const isInbox = url.pathname === BASE || url.pathname.startsWith(BASE + '/')
    if (isInbox || url.pathname === COMMENTS) {
      const origin = req.headers.get('origin')
      if (origin && origin !== `http://${host}`) return new Response('bad origin', { status: 403 })
    }
    if (isInbox) {
      const res = await handleInboxRequest(inbox, {
        method: req.method,
        url: url.pathname + url.search,
        body: () => req.text(),
        principal: authorised(req.headers.get('authorization')) ? { kind: 'human', id: 'reader', roles: ['reviewer'] } : null,
      })
      if (req.method === 'POST' && res.status < 300) console.log(`${new Date().toISOString()} ${url.pathname} ${res.status}`)
      return new Response(res.body || null, { status: res.status, headers: { ...res.headers, 'cache-control': 'no-store' } })
    }
    if (url.pathname === COMMENTS) {
      if (!authorised(req.headers.get('authorization'))) return new Response('unauthorized', { status: 401 })
      const html = await inFolder(url.searchParams.get('page') ?? '')
      if (!html || !/\.html?$/i.test(html)) return new Response('page: not a report in this folder', { status: 404 })
      return comments(req, html, html.slice(dir.length + 1))
    }
    if (req.method !== 'GET' && req.method !== 'HEAD') return new Response('read only', { status: 405 })
    const target = await inFolder(url.pathname)
    // comments go out only through /__comments, behind the token
    if (!target || target.endsWith('.comments.json')) return new Response('not found', { status: 404 })
    const f = Bun.file(target)
    if (!(await f.exists())) return new Response('not found', { status: 404 })
    return new Response(f, { headers: { 'cache-control': 'no-store' } })
  }

  const fixed = arg('--port')
  const start = (port: number) => {
    const s = Bun.serve({ hostname: '127.0.0.1', port, fetch: req => handler(req, s.port) })
    return s
  }
  let server
  try {
    server = start(fixed ? Number(fixed) : prev?.port ?? stablePort(root + '\0' + dir))
  }
  catch (e) {
    if (fixed) die(`port ${fixed}: ${String(e)}`)
    server = start(0)
  }
  await writeState({ ...(await readState()), [dir]: { port: server.port, token, pid: process.pid } })
  console.log(`report: http://127.0.0.1:${server.port}/${rel}#k=${token}`)
  console.log(`env: ${env}`)
  console.log(`inbox: ${join(root, '.data', 'annotations')}`)
}

const [cmd] = process.argv.slice(2).filter((a, i, all) => !a.startsWith('--') && !all[i - 1]?.startsWith('--'))
if (!cmd) die('usage: report-serve.ts <report.html> [--root <project>] [--port <n>] [--env local|platform|container] | report-serve.ts wait [--root <project>]')
if (cmd === 'wait') await wait()
else await serve(cmd)

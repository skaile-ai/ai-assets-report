(() => {
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])
  /** `svg`: the item's lucide icon, resolved from its `icon` name by build.py. */
  const icon = (it) => (it.svg ? `<svg class="cm-ico" viewBox="0 0 24 24" aria-hidden="true">${it.svg}</svg>` : '')
  const TX = {
    de: { hint: 'Begriff antippen oder überfahren: alle Stellen leuchten auf. Klick hält die Auswahl.', state: 'Stand', toggles: 'Schalter',
      marks: 'Änderungen zeigen', vs: 'gegenüber', n: 'neu', v: 'geändert', r: 'entfällt', views: 'Was sich tut: wo die Begriffe erscheinen',
      graph: 'Wie die Begriffe zusammenhängen', gloss: 'Was jeder Begriff bedeutet', aka: 'früher/auch', where: 'erscheint',
      hidden: 'in diesem Stand nicht sichtbar', absent: 'gibt es in diesem Stand nicht', user: 'Nutzer', aria: 'Begriffsgraph',
      mark: { new: 'neu', moved: 'verschoben', renamed: 'umbenannt', changed: 'geändert', gone: 'entfällt' },
      rel: { has: 'hat / läuft mit', is: 'ist ein (Unterart)', shows: 'erscheint in / als', controls: 'steuert' }, off: 'blass = gilt in diesem Stand nicht' },
    en: { hint: 'Tap or hover a term: every place it appears lights up. A click keeps the selection.', state: 'State', toggles: 'Switches',
      marks: 'Show changes', vs: 'against', n: 'new', v: 'changed', r: 'removed', views: 'What happens: where the terms appear',
      graph: 'How the terms relate', gloss: 'What each term means', aka: 'formerly/also', where: 'appears',
      hidden: 'not visible in this state', absent: 'does not exist in this state', user: 'User', aria: 'Term graph',
      mark: { new: 'new', moved: 'moved', renamed: 'renamed', changed: 'changed', gone: 'removed' },
      rel: { has: 'has / runs with', is: 'is a (kind of)', shows: 'appears in / as', controls: 'controls' }, off: 'faded = does not hold in this state' },
  }
  const L = TX[document.documentElement.lang.slice(0, 2)] || TX.en
  const avatar = (it) => (it.avatar ? `<span class="cm-av${it.sq ? ' sq' : ''}" style="--c:var(--${it.color || 'gray'})">${esc(it.avatar)}</span>` : '')

  /** `when`: absent = always; {any:[...]} = one of them; else every key must match. */
  function holds(when, state) {
    if (!when) return true
    if (when.any) return when.any.some((w) => holds(w, state))
    return Object.entries(when).every(([k, v]) => Boolean(state[k]) === v)
  }

  /**
   * The rows a view draws: the visible ones, marked against the baseline, plus baseline rows that are gone.
   * A row whose `key` the baseline also shows is the same thing: other depth = moved, other label = renamed, else changed.
   */
  function diffItems(view, state, base) {
    const now = view.items.filter((it) => holds(it.when, state))
    const was = view.items.filter((it) => holds(it.when, base))
    const nowIds = new Set(now.map((i) => i.id))
    const wasIds = new Set(was.map((i) => i.id))
    const nowKeys = new Set(now.map((i) => i.key).filter(Boolean))
    const wasByKey = new Map(was.filter((i) => i.key).map((i) => [i.key, i]))
    return view.items
      .map((it) => {
        if (nowIds.has(it.id)) {
          if (wasIds.has(it.id)) return { it, mark: '' }
          const old = it.key && wasByKey.get(it.key)
          if (!old) return { it, mark: 'new' }
          if ((old.depth || 0) !== (it.depth || 0)) return { it, mark: 'moved', old }
          if (old.label !== it.label) return { it, mark: 'renamed', old }
          return { it, mark: 'changed', old }
        }
        if (wasIds.has(it.id) && !(it.key && nowKeys.has(it.key))) return { it, mark: 'gone' }
        return null
      })
      .filter(Boolean)
  }

  const cls = (mark) => (mark ? ` is-${mark === 'renamed' || mark === 'changed' ? 'moved' : mark}` : '')
  const mk = (mark) => (mark ? `<span class="cm-mk">${L.mark[mark]}</span>` : '')
  const was = (mark, old) => (mark === 'renamed' ? `<s class="cm-was">${esc(old.label)}</s>` : '')
  const termAttr = (it) => (it.term ? ` data-term="${esc(it.term)}"` : '')

  function renderTree(rows) {
    return `<ul class="cm-tree">${rows
      .map(({ it, mark, old }) => {
        const lead = avatar(it) || icon(it)
        const tail = it.chip ? `<span class="cm-chip">${esc(it.chip)}</span>` : it.dot ? `<span class="cm-dot" style="--c:var(--${it.dot})"></span>` : ''
        return `<li class="cm-row ${it.kind || ''}${cls(mark)}" style="--d:${it.depth || 0}"${termAttr(it)}>${lead}${was(mark, old)}<span class="lb">${esc(it.label)}</span>${tail}${mk(mark)}</li>`
      })
      .join('')}</ul>`
  }

  function renderTabs(rows) {
    const by = (slot) => rows.filter((r) => (r.it.slot || 'body') === slot)
    const tabs = by('tab')
      .map(({ it, mark }) => `<span class="cm-tab ${it.kind || ''}${it.active ? ' active' : ''}${cls(mark)}"${termAttr(it)}>${avatar(it)}<span class="lb">${esc(it.label)}</span>${it.kind === 'add' ? '' : '<span class="x">×</span>'}</span>`)
      .join('')
    const line = (slot, base) => by(slot).map(({ it, mark }) => `<div class="${base} ${it.kind || ''}${cls(mark)}"${termAttr(it)}>${avatar(it)}<span class="lb">${esc(it.label)}</span>${it.chip ? `<span class="cm-chip">${esc(it.chip)}</span>` : ''} ${mk(mark)}</div>`).join('')
    const head = line('head', 'cm-head')
    const more = line('more', 'cm-more')
    const body = line('body', 'cm-b')
    const composer = line('composer', 'cm-composer')
    const side = by('side').map(({ it }) => `<div>${esc(it.label)}</div>`).join('')
    return `<div class="cm-chat${side ? '' : ' no-side'}"><div class="cm-chatmain">${head}${tabs ? `<div class="cm-tabs">${tabs}</div>` : ''}${more}<div class="cm-body">${body}</div>${composer}</div>${side ? `<div class="cm-side">${side}</div>` : ''}</div>`
  }

  /** Point where the segment from a box centre towards (tx,ty) leaves the box. */
  function edgePoint([x, y], [tx, ty], hw, hh) {
    const dx = tx - x
    const dy = ty - y
    const t = Math.min(dx ? hw / Math.abs(dx) : Infinity, dy ? hh / Math.abs(dy) : Infinity)
    return [x + dx * t, y + dy * t]
  }

  function renderGraph(spec, state) {
    const g = spec.graph
    const W = 150
    const H = 46
    const pos = g.pos
    const terms = Object.fromEntries(spec.terms.map((t) => [t.id, t]))
    const edges = spec.relations
      .filter((r) => pos[r.from] && pos[r.to])
      .map((r) => {
        const a = edgePoint(pos[r.from], pos[r.to], W / 2 + 4, H / 2 + 4)
        const b = edgePoint(pos[r.to], pos[r.from], W / 2 + 6, H / 2 + 6)
        const mx = (a[0] + b[0]) / 2
        const my = (a[1] + b[1]) / 2
        const marker = r.rel === 'is' ? 'url(#cm-is)' : 'url(#cm-to)'
        const on = holds(r.when, state)
        return `<g class="e ${r.rel}${on ? '' : ' off'}" data-from="${r.from}" data-to="${r.to}"><path d="M${a[0]},${a[1]} L${b[0]},${b[1]}" marker-end="${marker}"/><text x="${mx}" y="${my + 4}">${esc(r.label)}</text></g>`
      })
      .join('')
    const nodes = spec.terms
      .filter((t) => pos[t.id])
      .map((t) => {
        const [x, y] = pos[t.id]
        const c = spec.kinds[t.kind]?.color || 'gray'
        return `<g class="n" data-term="${t.id}"><rect x="${x - W / 2}" y="${y - H / 2}" width="${W}" height="${H}" rx="7" fill="var(--${c}-bg)" stroke="var(--${c})"/><text x="${x}" y="${y - 2}">${esc(t.label)}</text><text class="c" x="${x}" y="${y + 14}">${esc(shortCode(t.code))}</text></g>`
      })
      .join('')
    const defs = `<defs><marker id="cm-to" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--gray)"/></marker><marker id="cm-is" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0 L11,6 L0,12 z" fill="var(--paper)" stroke="var(--gray)"/></marker></defs>`
    const triples = spec.relations
      .map((r) => `<li class="${holds(r.when, state) ? '' : 'off'}" data-term="${r.from}"><b>${esc(terms[r.from]?.label)}</b> <em>${esc(r.label)}</em> <b>${esc(terms[r.to]?.label)}</b></li>`)
      .join('')
    const sample = {
      has: '<path d="M0 5h22" stroke="var(--gray)" stroke-width="1.5"/><path d="M20 1l7 4-7 4z" fill="var(--gray)"/>',
      is: '<path d="M0 5h20" stroke="var(--gray)" stroke-width="1.5" stroke-dasharray="5 3"/><path d="M19 1l8 4-8 4z" fill="var(--paper)" stroke="var(--gray)"/>',
      shows: '<path d="M0 5h24" stroke="var(--teal)" stroke-width="1.5" stroke-dasharray="2 3"/>',
      controls: '<path d="M0 5h24" stroke="var(--orange)" stroke-width="1.5" stroke-dasharray="2 3"/>',
    }
    const rels = new Set(spec.relations.map((r) => (r.rel === 'uses' ? 'has' : r.rel)))
    const legend = `<div class="cm-legend">${Object.keys(sample)
      .filter((k) => rels.has(k))
      .map((k) => `<span><svg viewBox="0 0 28 10">${sample[k]}</svg> ${L.rel[k]}</span>`)
      .join('')}<span>${L.off}</span></div>`
    return `<svg viewBox="0 0 ${g.width} ${g.height}" role="img" aria-label="${L.aria}">${defs}${edges}${nodes}</svg>${legend}<ul class="cm-triples">${triples}</ul>`
  }

  const shortCode = (code) => (code && code.length > 24 ? `${code.slice(0, 23)}…` : code || '')

  function renderGlossary(spec, state) {
    const seen = {}
    for (const v of spec.views || []) {
      for (const it of v.items) {
        if (it.term && holds(it.when, state)) {
          seen[it.term] ??= {}
          seen[it.term][v.label] = (seen[it.term][v.label] || 0) + 1
        }
      }
    }
    return spec.terms
      .map((t) => {
        const k = spec.kinds[t.kind] || { label: t.kind, color: 'gray' }
        const aka = t.aka?.length ? `<span class="aka">${L.aka}: ${t.aka.map((a) => `<s>${esc(a)}</s>`).join(', ')}</span>` : ''
        // `where` on a term ([{when, text}]) names places outside the drawn views.
        const listed = (t.where || []).filter((w) => holds(w.when, state)).map((w) => esc(w.text))
        const drawn = seen[t.id] ? Object.entries(seen[t.id]).map(([v, n]) => `${esc(v)} (${n})`) : []
        const all = [...drawn, ...listed]
        const where = all.length ? all.join(' · ') : spec.views?.length ? L.hidden : L.absent
        return `<div class="cm-term" style="--c:var(--${k.color});--cb:var(--${k.color}-bg)" data-term="${t.id}" id="cm-${spec.id}-${t.id}"><div class="t"><b>${esc(t.label)}</b><span class="k">${esc(k.label)}</span>${aka}</div><p>${esc(t.def)}</p><code>${esc(t.code)}</code><div class="where">${L.where}: ${where}</div></div>`
      })
      .join('')
  }

  function summary(spec, state, base, baseLabel) {
    let n = 0
    let r = 0
    let v = 0
    for (const view of spec.views) {
      for (const { mark } of diffItems(view, state, base)) {
        if (mark === 'new') n++
        else if (mark === 'gone') r++
        else if (mark) v++
      }
    }
    if (!n && !r && !v) return ''
    return `<span class="cm-sum">${L.vs} „${esc(baseLabel)}“: <span class="cm-pill n">${n} ${L.n}</span><span class="cm-pill v">${v} ${L.v}</span><span class="cm-pill r">${r} ${L.r}</span></span>`
  }

  function mount(fig) {
    const spec = JSON.parse(fig.querySelector('script[type="application/json"]').textContent)
    const presetOf = (id) => spec.presets.find((p) => p.id === id)
    // A preset compares against its own `vs` (null = against nothing), else against the figure's `baseline`.
    const baseOf = (p) => presetOf(p && 'vs' in p ? p.vs : spec.baseline)
    const comparing = Boolean(spec.baseline) || spec.presets.some((p) => p.vs)
    let state = { ...(spec.initial || presetOf(spec.start || spec.presets[0].id).set) }
    let marks = true
    let pinned = null

    function draw() {
      const active = spec.presets.find((p) => Object.entries(p.set).every(([k, v]) => Boolean(state[k]) === v))
      const presets = spec.presets
        .map((p) => `<button type="button" data-preset="${p.id}" aria-pressed="${active?.id === p.id}">${esc(p.label)}</button>`)
        .join('')
      const switches = (spec.switches || [])
        .map((s) => {
          const disabled = s.requires && !state[s.requires]
          return `<button type="button" class="cm-sw" role="switch" data-switch="${s.id}" aria-checked="${Boolean(state[s.id])}"${disabled ? ' disabled' : ''}><span class="k"></span><span class="${s.mono ? 'm' : ''}">${esc(s.label)}</span>${s.desc ? `<small>${esc(s.desc)}</small>` : ''}</button>`
        })
        .join('')
      const base = baseOf(active)
      const diffing = Boolean(base) && marks && active?.id !== base.id
      const ref = diffing ? base.set : state
      const marksSw = comparing
        ? `<button type="button" class="cm-sw" role="switch" data-marks aria-checked="${marks}"${!base || active?.id === base.id ? ' disabled' : ''}><span class="k"></span><span>${L.marks}</span>${diffing ? summary(spec, state, base.set, base.label) : ''}</button>`
        : ''
      const views = (spec.views || [])
        .map((v) => {
          const rows = diffItems(v, state, ref)
          return `<section class="cm-view"><header>${esc(v.label)}</header>${v.layout === 'tabs' ? renderTabs(rows) : renderTree(rows)}</section>`
        })
        .join('')
      const thoughts = (spec.thoughts || [])
        .filter((th) => holds(th.when, state))
        .map((th) => `<div class="cm-thought ${th.tone || ''}"${termAttr(th)}><b>${esc(th.who || L.user)}</b> „${esc(th.text)}“${th.note ? `<small>${esc(th.note)}</small>` : ''}</div>`)
        .join('')
      const parts = spec.parts || ['views', 'graph', 'gloss']
      const head = (n, text) => (parts.length > 1 ? `<h4 class="cm-h"><i>${n}</i> ${text}</h4>` : '')
      const html = []
      const controls = `<div class="cm-ctl"><div class="cm-seg" role="group" aria-label="${L.state}">${presets}</div>${marksSw}</div>
${active?.desc ? `<p class="cm-desc">${esc(active.desc)}</p>` : ''}
${switches ? `<div class="cm-ctl cm-toggles"><span class="cm-ctl-l">${esc(spec.switchesLabel || L.toggles)}</span>${switches}</div>` : ''}`
      if (parts.includes('views')) {
        html.push(`<div class="cm-part">${head(1, L.views)}${controls}<div class="cm-views">${views}</div>${thoughts ? `<div class="cm-thoughts">${thoughts}</div>` : ''}</div>`)
      } else if (spec.presets.length > 1) {
        html.push(`<div class="cm-part">${controls}</div>`)
      }
      if (parts.includes('graph')) html.push(`<div class="cm-part cm-graph">${head(2, L.graph)}${renderGraph(spec, state)}</div>`)
      if (parts.includes('gloss')) html.push(`<div class="cm-part">${head(3, L.gloss)}<div class="cm-gloss">${renderGlossary(spec, state)}</div></div>`)
      fig.innerHTML = `<div class="cm-cap"><b>${esc(spec.label)}</b><span class="cm-hint">${esc(spec.hint || L.hint)}</span></div>${html.join('')}`
      if (pinned) focus(pinned, true)
    }

    function focus(id, pin) {
      fig.classList.toggle('focus', Boolean(id))
      fig.querySelectorAll('.on,.pinned').forEach((el) => el.classList.remove('on', 'pinned'))
      if (!id) return
      fig.querySelectorAll(`[data-term="${id}"]`).forEach((el) => el.classList.add('on'))
      fig.querySelectorAll('.e').forEach((e) => {
        if (e.dataset.from === id || e.dataset.to === id) {
          e.classList.add('on')
          fig.querySelectorAll(`.n[data-term="${e.dataset.from === id ? e.dataset.to : e.dataset.from}"]`).forEach((n) => n.classList.add('on'))
        }
      })
      if (pin) fig.querySelectorAll(`.cm-term[data-term="${id}"]`).forEach((el) => el.classList.add('pinned'))
    }

    fig.addEventListener('click', (ev) => {
      const p = ev.target.closest('[data-preset]')
      const s = ev.target.closest('[data-switch]')
      const m = ev.target.closest('[data-marks]')
      const t = ev.target.closest('[data-term]')
      if (p) {
        state = { ...state, ...presetOf(p.dataset.preset).set }
        draw()
      } else if (m && !m.disabled) {
        marks = !marks
        draw()
      } else if (s && !s.disabled) {
        state = { ...state, [s.dataset.switch]: !state[s.dataset.switch] }
        draw()
      } else if (t) {
        pinned = pinned === t.dataset.term ? null : t.dataset.term
        focus(pinned, true)
      }
    })
    fig.addEventListener('mouseover', (ev) => {
      if (pinned) return
      const t = ev.target.closest('[data-term]')
      focus(t ? t.dataset.term : null)
    })
    fig.addEventListener('mouseleave', () => {
      if (!pinned) focus(null)
    })
    draw()
  }

  const start = () => document.querySelectorAll('figure[data-concepts]').forEach(mount)
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start)
  else start()
})()

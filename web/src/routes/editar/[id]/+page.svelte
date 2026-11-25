<script lang="ts">
	/**
	 * The lyrics and timing editor (plan v4 §7, phase 7), keyboard first. It edits the song's
	 * current lyrics with the editor operations of v3 and plays the stems in the browser (the
	 * mini player); saving makes a new version of the manifest on the server, where only the
	 * lyrics blob is new. Scope `editor`: its keys win over the global ones while it is open.
	 */
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { AudioEngine } from '#lib/audio/engine.js';
	import type { KaraokeDoc, Lyrics, Manifest } from '#lib/contracts';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api, ApiError } from '#lib/control/api.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import { History } from '#lib/editor/history.svelte.js';
	import { checkDoc, moveWordEdge, retimeLine, setWordText, shiftLine } from '#lib/editor/ops.js';
	import Waveform from '#lib/editor/Waveform.svelte';
	import { i18n } from '#lib/i18n';
	import { DEFAULT_THEME, Lyrics as LyricsView, THEMES, docFromTracks } from '#lib/lyrics';
	import { fail } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';

	const LEAD = 0.6;
	const DOUBTFUL = 0.5;
	const id = $derived(page.params.id ?? '');
	const t = $derived(i18n.t);

	let manifest = $state.raw<Manifest | null>(null);
	let base = $state<string | null>(null);
	let lyrics = $state.raw<Lyrics | null>(null);
	let history = $state.raw<History<KaraokeDoc> | null>(null);
	let saved = $state.raw<KaraokeDoc | null>(null);
	let dragging = $state.raw<KaraokeDoc | null>(null);
	let lineIndex = $state(0);
	let wordIndex = $state(0);
	let mode = $state<'idle' | 'line' | 'loop' | 'tap'>('idle');
	let taps = $state<number[]>([]);
	let editing = $state(false);
	let time = $state(0);
	let playing = $state(false);
	let context: AudioContext | null = null;
	let engine: AudioEngine | null = null;
	let vocals = $state.raw<AudioBuffer | null>(null);

	const doc = $derived(dragging ?? history?.current ?? null);
	const line = $derived(doc?.lines[lineIndex] ?? null);
	const word = $derived(line?.words[wordIndex] ?? null);
	const dirty = $derived(doc !== null && doc !== saved);
	const problems = $derived(doc ? checkDoc(doc) : []);
	const from = $derived(line ? Math.max(0, line.start - LEAD) : 0);
	const to = $derived(line ? line.end + LEAD : 1);
	const theme = THEMES[DEFAULT_THEME];

	async function load() {
		try {
			const [m, l] = await Promise.all([api.manifest(id), api.lyrics(id)]);
			const content = await fetch(`/api/contents/${encodeURIComponent(id)}`).then((r) => r.json());
			manifest = m;
			lyrics = l;
			base = content.manifest;
			const loaded = docFromTracks(m, l);
			history = new History(loaded);
			saved = loaded;
		} catch (error) {
			fail(error);
		}
	}

	async function ensureAudio() {
		if (engine || !manifest) return;
		context = new AudioContext();
		engine = new AudioEngine(context);
		const blob = (kind: string) => manifest?.tracks.find((tr) => tr.kind === kind)?.blob.sha256;
		const instrumental = blob('instrumental');
		const voice = blob('vocals');
		if (!instrumental) return;
		await engine.load({
			instrumental: api.blobUrl(instrumental),
			vocals: voice ? api.blobUrl(voice) : null
		});
		engine.setVocalVolume(1);
		vocals = engine.vocalsBuffer;
	}

	async function playLine(loop = false) {
		await ensureAudio();
		if (!engine || !line) return;
		if (engine.playing && mode !== 'idle') {
			engine.pause();
			mode = 'idle';
			return;
		}
		engine.seek(from);
		mode = loop ? 'loop' : 'line';
		await engine.play();
	}

	async function startTap() {
		await ensureAudio();
		if (!engine || !line) return;
		taps = [];
		engine.seek(from);
		mode = 'tap';
		await engine.play();
	}

	function tap() {
		if (mode !== 'tap' || !engine || !doc || !line) return;
		taps = [...taps, engine.now()];
		if (taps.length >= line.words.length) finishTap();
	}

	function finishTap() {
		if (doc && taps.length) history?.push(retimeLine(doc, lineIndex, taps));
		taps = [];
		mode = 'idle';
		engine?.pause();
	}

	function selectLine(index: number) {
		if (!doc) return;
		lineIndex = Math.max(0, Math.min(doc.lines.length - 1, index));
		wordIndex = 0;
		editing = false;
	}

	function selectWord(step: number) {
		if (!line) return;
		const next = wordIndex + step;
		if (next < 0) {
			if (lineIndex > 0) {
				selectLine(lineIndex - 1);
				wordIndex = (doc?.lines[lineIndex]?.words.length ?? 1) - 1;
			}
		} else if (next >= line.words.length) {
			if (doc && lineIndex < doc.lines.length - 1) selectLine(lineIndex + 1);
		} else wordIndex = next;
	}

	function nextDoubtful() {
		if (!doc) return;
		const all = doc.lines.flatMap((l, i) =>
			l.words.flatMap((w, j) => ((w.confidence ?? 1) < DOUBTFUL ? [{ i, j }] : []))
		);
		const after =
			all.find((d) => d.i > lineIndex || (d.i === lineIndex && d.j > wordIndex)) ?? all[0];
		if (after) {
			lineIndex = after.i;
			wordIndex = after.j;
		}
	}

	const edit = (next: KaraokeDoc) => doc && next !== doc && history?.push(next);

	async function save() {
		if (!doc || !lyrics || !base || !dirty) return;
		const next: Lyrics = { ...lyrics, singers: doc.singers ?? [], lines: doc.lines, edited: true };
		try {
			const content = await api.saveLyrics(id, base, next);
			base = content.manifest;
			lyrics = next;
			saved = doc;
			toasts.show(t.editor.saved);
		} catch (error) {
			if (error instanceof ApiError && error.code === 'version_conflict')
				toasts.show(t.editor.conflict, 'error');
			else fail(error);
		}
	}

	onMount(() => {
		void load();
		commands.scope = 'editor';
		const group = () => t.editor.title;
		const scope = 'editor' as const;
		const unregister = commands.register(
			{
				id: 'editor.play',
				title: () => t.editor.play,
				group,
				scope,
				keys: ['Space'],
				run: () => (mode === 'tap' ? tap() : playLine())
			},
			{
				id: 'editor.loop',
				title: () => `${t.editor.play} ⟳`,
				group,
				scope,
				keys: ['l'],
				run: () => playLine(true)
			},
			{ id: 'editor.tap', title: () => 'Tap', group, scope, keys: ['t'], run: startTap },
			{
				id: 'editor.nextLine',
				title: () => t.cmd.down,
				group,
				scope,
				keys: ['j', 'ArrowDown'],
				run: () => selectLine(lineIndex + 1)
			},
			{
				id: 'editor.prevLine',
				title: () => t.cmd.up,
				group,
				scope,
				keys: ['k', 'ArrowUp'],
				run: () => selectLine(lineIndex - 1)
			},
			{
				id: 'editor.nextWord',
				title: () => '→',
				group,
				scope,
				keys: ['ArrowRight', 'w'],
				run: () => selectWord(1),
				hidden: true
			},
			{
				id: 'editor.prevWord',
				title: () => '←',
				group,
				scope,
				keys: ['ArrowLeft', 'b'],
				run: () => selectWord(-1),
				hidden: true
			},
			{
				id: 'editor.earlier',
				title: () => '−50 ms',
				group,
				scope,
				keys: [','],
				run: () => void (doc && edit(shiftLine(doc, lineIndex, -0.05)))
			},
			{
				id: 'editor.later',
				title: () => '+50 ms',
				group,
				scope,
				keys: ['.'],
				run: () => void (doc && edit(shiftLine(doc, lineIndex, 0.05)))
			},
			{
				id: 'editor.startEarlier',
				title: () => '⇤ −20 ms',
				group,
				scope,
				keys: ['Shift+,'],
				run: () =>
					void (
						doc && edit(moveWordEdge(doc, { line: lineIndex, word: wordIndex }, 'start', -0.02))
					)
			},
			{
				id: 'editor.startLater',
				title: () => '⇤ +20 ms',
				group,
				scope,
				keys: ['Shift+.'],
				run: () =>
					void (doc && edit(moveWordEdge(doc, { line: lineIndex, word: wordIndex }, 'start', 0.02)))
			},
			{
				id: 'editor.endEarlier',
				title: () => '⇥ −20 ms',
				group,
				scope,
				keys: ['Alt+,'],
				run: () =>
					void (doc && edit(moveWordEdge(doc, { line: lineIndex, word: wordIndex }, 'end', -0.02)))
			},
			{
				id: 'editor.endLater',
				title: () => '⇥ +20 ms',
				group,
				scope,
				keys: ['Alt+.'],
				run: () =>
					void (doc && edit(moveWordEdge(doc, { line: lineIndex, word: wordIndex }, 'end', 0.02)))
			},
			{
				id: 'editor.text',
				title: () => t.cmd.edit,
				group,
				scope,
				keys: ['Enter'],
				run: () => void (editing = true)
			},
			{ id: 'editor.doubtful', title: () => '?', group, scope, keys: ['u'], run: nextDoubtful },
			{
				id: 'editor.undo',
				title: () => t.cmd.undo,
				group,
				scope,
				keys: ['Mod+z'],
				run: () => void history?.undo()
			},
			{
				id: 'editor.redo',
				title: () => t.cmd.redo,
				group,
				scope,
				keys: ['Mod+Shift+z', 'Mod+y'],
				run: () => void history?.redo()
			},
			{
				id: 'editor.save',
				title: () => t.editor.save,
				group,
				scope,
				keys: ['Mod+s'],
				whileTyping: true,
				run: save
			}
		);
		let frame = requestAnimationFrame(function loop() {
			if (engine) {
				time = engine.now();
				playing = engine.playing;
				if (line && mode !== 'idle' && engine.playing && time > line.end + LEAD) {
					if (mode === 'loop') engine.seek(from);
					else if (mode === 'tap') finishTap();
					else {
						engine.pause();
						mode = 'idle';
					}
				}
			}
			frame = requestAnimationFrame(loop);
		});
		return () => {
			unregister();
			cancelAnimationFrame(frame);
			engine?.pause();
			void context?.close();
		};
	});
</script>

<svelte:window onbeforeunload={(e) => dirty && e.preventDefault()} />

<div class="page editor">
	<header class="page-header">
		<div>
			<h1>{t.editor.title}</h1>
			<p class="description">{manifest?.title ?? ''}</p>
		</div>
		<div class="actions">
			<button class="btn" onclick={() => window.history.back()}>{t.editor.back}</button>
			<button class="btn primary" onclick={save} disabled={!dirty}>
				{t.editor.save}
				<Kbd keys="Mod+s" />
			</button>
		</div>
	</header>
	{#if !doc}
		<p class="muted">{t.common.loading}</p>
	{:else}
		<div class="layout">
			<ol class="panel lines" aria-label={t.editor.title}>
				{#each doc.lines as l, i (l.id)}
					<li
						class="line"
						class:selected={i === lineIndex}
						onclick={() => selectLine(i)}
						onkeydown={() => {}}
						role="option"
						aria-selected={i === lineIndex}
					>
						<span class="faint mono time">{clock(l.start)}</span>
						<span>{l.words.map((w) => w.text).join(' ')}</span>
					</li>
				{/each}
			</ol>
			<section class="panel panel-body detail">
				{#if line}
					<Waveform
						buffer={vocals}
						{from}
						{to}
						words={line.words.map((w) => ({
							text: w.text,
							start: w.start,
							end: w.end,
							doubtful: (w.confidence ?? 1) < DOUBTFUL
						}))}
						selected={wordIndex}
						{time}
						{playing}
						onseek={(s) => engine?.seek(s)}
						onselect={(i) => (wordIndex = i)}
						ondrag={(i, edge, delta, done) => {
							if (!history) return;
							const next =
								delta === null
									? null
									: moveWordEdge(history.current, { line: lineIndex, word: i }, edge, delta);
							if (done) {
								dragging = null;
								if (next) edit(next);
							} else dragging = next;
						}}
					/>
					<p class="words">
						{#each line.words as w, j (j)}
							<span
								class:selected={j === wordIndex}
								class:doubtful={(w.confidence ?? 1) < DOUBTFUL}
							>
								{#if editing && j === wordIndex}
									<!-- svelte-ignore a11y_autofocus -->
									<input
										class="field"
										autofocus
										value={w.text}
										onkeydown={(e) => {
											e.stopPropagation();
											if (e.key === 'Enter' && doc) {
												edit(setWordText(doc, { line: lineIndex, word: j }, e.currentTarget.value));
												editing = false;
											}
											if (e.key === 'Escape') editing = false;
										}}
									/>
								{:else}{w.text}{/if}
							</span>
						{/each}
					</p>
					{#if word}<p class="muted mono">{clock(word.start)} → {word.end.toFixed(2)} s</p>{/if}
					{#if mode === 'tap'}<p class="badge warn plain">
							Tap {taps.length}/{line.words.length} · <Kbd keys="Space" />
						</p>{/if}
				{/if}
				{#if problems.length}<ul class="problems">
						{#each problems as p (p)}<li>{p}</li>{/each}
					</ul>{/if}
				<div class="preview">
					<LyricsView {doc} {theme} clock={{ now: () => time }} />
				</div>
				<p class="faint keys">
					<Kbd keys="Space" />
					{t.editor.play} · <Kbd keys="l" /> ⟳ · <Kbd keys="t" /> Tap · <Kbd keys="j" />/<Kbd
						keys="k"
					/> · ←/→ ·
					<Kbd keys="," />/<Kbd keys="." /> ±50 ms · <Kbd keys="Shift+," />/<Kbd keys="Alt+." /> · <Kbd
						keys="Enter"
					/>
					{t.cmd.edit} · <Kbd keys="u" /> ?
				</p>
			</section>
		</div>
	{/if}
</div>

<style>
	.layout {
		display: grid;
		grid-template-columns: minmax(16rem, 1fr) minmax(0, 2.2fr);
		gap: 16px;
		height: calc(100dvh - var(--player-height) - 150px);
	}
	.lines {
		overflow: auto;
		margin: 0;
		padding: 4px 0;
		list-style: none;
	}
	.line {
		display: flex;
		gap: 12px;
		align-items: baseline;
		padding: 8px 14px;
		cursor: pointer;
	}
	.line:hover {
		background: var(--surface-2);
	}
	.line.selected {
		background: var(--accent-soft);
	}
	.time {
		width: 3.5rem;
		flex: none;
		font-size: 12px;
	}
	.detail {
		display: flex;
		flex-direction: column;
		gap: 12px;
		overflow: auto;
	}
	.words {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		font-size: 18px;
	}
	.words span {
		padding: 0 4px;
		border-radius: 3px;
	}
	.words .selected {
		outline: 2px solid var(--accent);
	}
	.words .doubtful {
		text-decoration: underline wavy var(--warn);
	}
	.preview {
		position: relative;
		height: 14rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		background: #000;
	}
	.problems {
		color: var(--error);
	}
	.keys {
		font-size: 12px;
	}
	@media (max-width: 900px) {
		.layout {
			grid-template-columns: minmax(0, 1fr);
			height: auto;
		}
		.lines {
			max-height: 40vh;
		}
	}
</style>

<script lang="ts">
	/**
	 * Live: the player's playlist (scope `playlist`), what is on now with its transport, and the
	 * work still being made, side by side in resizable panels.
	 */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { jobProgress, positionNow } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import {
		content,
		fail,
		moveInPlaylist,
		player,
		playlist,
		removeFromPlaylist,
		transport,
		updateItem
	} from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';
	import Panels from '#lib/shell/Panels.svelte';
	import { prefs } from '#lib/shell/prefs.svelte.js';
	import { Selection } from '#lib/shell/selection.svelte.js';

	const t = $derived(i18n.t);
	const target = $derived(player());
	const list = $derived(playlist());
	const items = $derived(list?.items ?? []);
	const selection = new Selection(() => items.map((i) => i.id));
	const cache = $derived(new Map(target?.status.cache.map((c) => [c.content_id, c]) ?? []));
	const current = $derived(items.find((i) => i.id === target?.status.item_id));
	const song = $derived(current ? content(current.content_id) : undefined);
	let now = $state(performance.now());
	const position = $derived(target ? positionNow(live.state, target, now) : null);
	const end = $derived(current?.end ?? song?.duration ?? 0);
	let editing = $state<string | null>(null);

	$effect(() => {
		const timer = setInterval(() => (now = performance.now()), 100);
		return () => clearInterval(timer);
	});
	$effect(() => {
		void items.length;
		selection.clamp();
	});

	async function choosePlaylist(id: string) {
		prefs.set('playlist', id || null);
		if (!target) return;
		try {
			await api.setConfig(target.id, { ...target.config, playlist_id: id || null });
		} catch (error) {
			fail(error);
		}
	}

	async function newPlaylist() {
		try {
			const made = await api.createPlaylist(new Date().toLocaleDateString(i18n.locale), target?.id);
			live.state = {
				...live.state,
				playlists: [...live.state.playlists.filter((p) => p.id !== made.id), made]
			};
			await choosePlaylist(made.id);
		} catch (error) {
			fail(error);
		}
	}

	onMount(() => {
		commands.scope = 'playlist';
		const group = () => t.groups.playlist;
		const scope = 'playlist' as const;
		return commands.register(
			{
				id: 'playlist.down',
				title: () => t.cmd.down,
				group,
				scope,
				keys: ['j', 'ArrowDown'],
				run: () => selection.move(1),
				hidden: true
			},
			{
				id: 'playlist.up',
				title: () => t.cmd.up,
				group,
				scope,
				keys: ['k', 'ArrowUp'],
				run: () => selection.move(-1),
				hidden: true
			},
			{
				id: 'playlist.extendDown',
				title: () => t.cmd.selectDown,
				group,
				scope,
				keys: ['Shift+j', 'Shift+ArrowDown'],
				run: () => selection.extend(1)
			},
			{
				id: 'playlist.extendUp',
				title: () => t.cmd.selectUp,
				group,
				scope,
				keys: ['Shift+k', 'Shift+ArrowUp'],
				run: () => selection.extend(-1)
			},
			{
				id: 'playlist.mark',
				title: () => t.cmd.toggleSelect,
				group,
				scope,
				keys: ['x'],
				run: () => selection.toggle()
			},
			{
				id: 'playlist.moveUp',
				title: () => t.cmd.moveUp,
				group,
				scope,
				keys: ['Alt+ArrowUp', 'Alt+k'],
				run: () => moveInPlaylist(selection.targets, -1).then(() => selection.move(-1))
			},
			{
				id: 'playlist.moveDown',
				title: () => t.cmd.moveDown,
				group,
				scope,
				keys: ['Alt+ArrowDown', 'Alt+j'],
				run: () => moveInPlaylist(selection.targets, 1).then(() => selection.move(1))
			},
			{
				id: 'playlist.remove',
				title: () => t.cmd.remove,
				group,
				scope,
				keys: ['Delete', 'Backspace'],
				run: () => removeFromPlaylist(selection.targets).then(() => selection.clear())
			},
			{
				id: 'playlist.cue',
				title: () => t.cmd.cue,
				group,
				scope,
				keys: ['Enter'],
				run: () => {
					if (selection.current) void transport.cue(selection.current);
				}
			},
			{
				id: 'playlist.playNow',
				title: () => t.cmd.play,
				group,
				scope,
				keys: ['Shift+Enter'],
				run: () => {
					if (selection.current) void transport.playItem(selection.current);
				}
			},
			{
				id: 'playlist.singer',
				title: () => t.live.singer,
				group,
				scope,
				keys: ['s'],
				run: () => void (editing = selection.current ?? null)
			},
			{
				id: 'playlist.entry',
				title: () => t.live.entry,
				group,
				scope,
				keys: ['i'],
				run: () => {
					if (current && position !== null)
						void updateItem(current.id, { start: Math.round(position * 10) / 10 });
				}
			},
			{
				id: 'playlist.exit',
				title: () => t.live.exit,
				group,
				scope,
				keys: ['o'],
				run: () => {
					if (current && position !== null)
						void updateItem(current.id, { end: Math.round(position * 10) / 10 });
				}
			},
			{
				id: 'playlist.new',
				title: () => t.cmd.newPlaylist,
				group,
				keys: ['Mod+Shift+n'],
				run: newPlaylist
			}
		);
	});
</script>

{#snippet listPanel()}
	<div
		class="ctl-box fill"
		role="region"
		aria-label={t.live.playlist}
		onfocusin={() => (commands.scope = 'playlist')}
	>
		<div class="head">
			<h2>{t.live.playlist}</h2>
			<select
				class="ctl-field"
				aria-label={t.live.choosePlaylist}
				value={list?.id ?? ''}
				onchange={(e) => choosePlaylist(e.currentTarget.value)}
			>
				<option value="">—</option>
				{#each live.state.playlists as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
			</select>
			<button class="ctl-btn" onclick={newPlaylist}>+ <Kbd keys="Mod+Shift+n" /></button>
		</div>
		{#if !list}
			<p class="ctl-muted">{t.live.noPlaylist}</p>
		{:else if items.length === 0}
			<p class="ctl-muted">{t.live.empty}</p>
		{:else}
			<ol class="ctl-rows" role="listbox" aria-label={list.name}>
				{#each items as item, i (item.id)}
					{@const c = content(item.content_id)}
					{@const state = cache.get(item.content_id)}
					<li
						class="ctl-row item"
						class:ctl-cursor={i === selection.cursor}
						class:ctl-marked={selection.marked.has(item.id)}
						class:ctl-on={item.id === target?.status.item_id}
						role="option"
						aria-selected={i === selection.cursor}
						onclick={() => (selection.cursor = i)}
						ondblclick={() => transport.cue(item.id)}
						onkeydown={() => {}}
					>
						<span class="n">{i + 1}</span>
						<span class="title"
							>{c?.title ?? item.content_id}<span class="ctl-muted"> {c?.artist ?? ''}</span></span
						>
						{#if editing === item.id}
							<!-- svelte-ignore a11y_autofocus -->
							<input
								class="ctl-field singer"
								autofocus
								value={item.singer ?? ''}
								aria-label={t.live.singer}
								onkeydown={(e) => {
									if (e.key === 'Enter') {
										void updateItem(item.id, { singer: e.currentTarget.value || null });
										editing = null;
									}
									if (e.key === 'Escape') editing = null;
									e.stopPropagation();
								}}
								onblur={() => (editing = null)}
							/>
						{:else}
							<span class="singer">{item.singer ?? ''}</span>
						{/if}
						<span class="ctl-muted"
							>{item.semitones ? `${item.semitones > 0 ? '+' : ''}${item.semitones}` : ''}</span
						>
						<span
							class="ctl-pill {state?.state === 'ready'
								? 'ctl-ok'
								: state?.state === 'failed'
									? 'ctl-bad'
									: 'ctl-warn'}"
						>
							{state ? t.live.cache[state.state] : t.live.cache.absent}
						</span>
					</li>
				{/each}
			</ol>
		{/if}
		<p class="ctl-muted keys">
			<Kbd keys="Enter" />
			{t.cmd.cue} · <Kbd keys="Shift+Enter" />
			{t.cmd.play} · <Kbd keys="Alt+ArrowUp" />/<Kbd keys="Alt+ArrowDown" />
			{t.cmd.moveUp} ·
			<Kbd keys="Delete" />
			{t.cmd.remove} · <Kbd keys="s" />
			{t.live.singer} · <Kbd keys="i" />/<Kbd keys="o" />
			{t.live.entry}/{t.live.exit}
		</p>
	</div>
{/snippet}

{#snippet nowPanel()}
	<div class="ctl-box fill now">
		<div class="head">
			<h2>{t.live.nowPlaying}</h2>
			{#if live.state.players.length > 1}
				<select
					class="ctl-field"
					aria-label={t.live.player}
					value={target?.id}
					onchange={(e) => prefs.set('player', e.currentTarget.value)}
				>
					{#each live.state.players as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
				</select>
			{/if}
		</div>
		{#if song}
			<p class="song">{song.title}</p>
			<p class="ctl-muted">
				{song.artist ?? ''}{#if current?.singer}
					· ♪ {current.singer}{/if}
			</p>
			<div class="progress">
				<span class="mono">{clock(position)}</span>
				<div class="ctl-bar">
					<span style:width={`${end ? Math.min(100, ((position ?? 0) / end) * 100) : 0}%`}></span>
				</div>
				<span class="mono">{clock(end)}</span>
			</div>
		{:else}
			<p class="ctl-muted">{t.status.nothing}</p>
		{/if}
		<div class="transport">
			<button class="ctl-btn" onclick={transport.previous}>⏮ <Kbd keys="p" /></button>
			<button class="ctl-btn" onclick={() => transport.seekBy(-5)}
				>-5 <Kbd keys="ArrowLeft" /></button
			>
			<button class="ctl-btn ctl-primary" onclick={transport.toggle}
				>{target?.status.state === 'playing' ? '⏸' : '▶'} <Kbd keys="Space" /></button
			>
			<button class="ctl-btn" onclick={() => transport.seekBy(5)}
				>+5 <Kbd keys="ArrowRight" /></button
			>
			<button class="ctl-btn" onclick={transport.next}>⏭ <Kbd keys="n" /></button>
		</div>
		<dl class="levels">
			<dt>{t.live.volume}</dt>
			<dd>{Math.round((target?.status.volume ?? 1) * 100)} % <Kbd keys="-" /><Kbd keys="+" /></dd>
			<dt>{t.live.key}</dt>
			<dd>{t.status.key(target?.status.semitones ?? 0)} <Kbd keys="[" /><Kbd keys="]" /></dd>
		</dl>
	</div>
{/snippet}

{#snippet workPanel()}
	<div class="ctl-box fill">
		<h2>{t.queue.title}</h2>
		<ul class="ctl-rows">
			{#each live.state.jobs
				.filter((j) => j.state === 'active' || j.state === 'paused')
				.slice(0, 12) as job (job.id)}
				<li class="ctl-row mini">
					<span class="title">{job.title}</span>
					<div class="ctl-bar">
						<span style:width={`${Math.round(jobProgress(job) * 100)}%`}></span>
					</div>
				</li>
			{:else}
				<li class="ctl-muted">{t.queue.empty}</li>
			{/each}
		</ul>
	</div>
{/snippet}

<Panels
	name="live"
	panels={[listPanel, nowPanel, workPanel]}
	initial={prefs.value.layout === 'live' ? [0.45, 0.35, 0.2] : [0.34, 0.33, 0.33]}
/>

<style>
	.fill {
		height: 100%;
		overflow: auto;
	}
	.head {
		display: flex;
		gap: var(--s-2);
		align-items: center;
		margin-bottom: var(--s-2);
	}
	.head h2 {
		margin: 0 auto 0 0;
	}
	.item {
		grid-template-columns: 2rem minmax(8rem, 1fr) minmax(4rem, 0.5fr) 2.5rem auto;
	}
	.n {
		color: var(--texto-3);
		font-family: var(--font-data);
	}
	.title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-weight: 600;
	}
	.singer {
		color: var(--ouro);
	}
	input.singer {
		width: 100%;
	}
	.now .song {
		font-size: var(--t-2);
		font-weight: 700;
		margin: var(--s-2) 0 0;
	}
	.progress {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: var(--s-3);
		margin: var(--s-4) 0;
	}
	.transport {
		display: flex;
		flex-wrap: wrap;
		gap: var(--s-2);
	}
	.levels {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--s-2) var(--s-4);
		margin-top: var(--s-4);
	}
	.levels dd {
		margin: 0;
	}
	.mini {
		grid-template-columns: 1fr 5rem;
	}
	.mono {
		font-family: var(--font-data);
	}
	.keys {
		margin-top: var(--s-3);
		font-size: var(--t--1);
	}
</style>

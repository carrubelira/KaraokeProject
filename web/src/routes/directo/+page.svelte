<script lang="ts">
	/**
	 * Live: the player's playlist (scope `playlist`) on the left; what is on now, with its
	 * transport, and what comes after on the right.
	 */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { positionNow } from '#lib/control/state.js';
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
	import Icon from '#lib/shell/Icon.svelte';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { prefs } from '#lib/shell/prefs.svelte.js';
	import { Selection } from '#lib/shell/selection.svelte.js';

	const t = $derived(i18n.t);
	const target = $derived(player());
	const list = $derived(playlist());
	const items = $derived(list?.items ?? []);
	const selection = new Selection(() => items.map((i) => i.id));
	const cache = $derived(new Map(target?.status.cache.map((c) => [c.content_id, c]) ?? []));
	const index = $derived(items.findIndex((i) => i.id === target?.status.item_id));
	const current = $derived(index >= 0 ? items[index] : undefined);
	const after = $derived(items.slice(index + 1, index + 6));
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

<div class="ctl-page">
	<header class="ctl-page-head">
		<h1>{t.live.title}</h1>
		<span class="ctl-sub">{target?.name ?? t.status.noPlayer}</span>
		<div class="ctl-actions">
			{#if live.state.players.length > 1}
				<select
					class="ctl-select"
					aria-label={t.live.player}
					value={target?.id}
					onchange={(e) => prefs.set('player', e.currentTarget.value)}
				>
					{#each live.state.players as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
				</select>
			{/if}
		</div>
	</header>

	<div class="ctl-columns">
		<section
			class="ctl-panel"
			aria-label={t.live.playlist}
			onfocusin={() => (commands.scope = 'playlist')}
		>
			<div class="ctl-panel-head">
				<h2>{t.live.playlist}</h2>
				<div class="ctl-actions">
					<select
						class="ctl-select"
						aria-label={t.live.choosePlaylist}
						value={list?.id ?? ''}
						onchange={(e) => choosePlaylist(e.currentTarget.value)}
					>
						<option value="">—</option>
						{#each live.state.playlists as p (p.id)}<option value={p.id}>{p.name}</option>{/each}
					</select>
					<button class="ctl-btn" onclick={newPlaylist}
						>{t.cmd.newPlaylist} <Kbd keys="Mod+Shift+n" /></button
					>
				</div>
			</div>
			{#if !list}
				<p class="ctl-empty">{t.live.noPlaylist}</p>
			{:else if items.length === 0}
				<p class="ctl-empty">{t.live.empty}</p>
			{:else}
				<table class="ctl-table" aria-label={list.name}>
					<thead>
						<tr>
							<th class="ctl-num">{t.live.columns.n}</th>
							<th>{t.live.columns.song}</th>
							<th>{t.live.singer}</th>
							<th class="ctl-num">{t.live.key}</th>
							<th>{t.live.columns.download}</th>
						</tr>
					</thead>
					<tbody>
						{#each items as item, i (item.id)}
							{@const c = content(item.content_id)}
							{@const state = cache.get(item.content_id)?.state ?? 'absent'}
							<tr
								class:ctl-cursor={i === selection.cursor}
								class:ctl-marked={selection.marked.has(item.id)}
								class:ctl-current={item.id === target?.status.item_id}
								aria-selected={i === selection.cursor}
								onclick={() => (selection.cursor = i)}
								ondblclick={() => transport.cue(item.id)}
							>
								<td class="ctl-num ctl-muted ctl-shrink"
									>{#if item.id === target?.status.item_id}<span class="playing"
											><Icon name="play" size={12} /></span
										>{:else}{i + 1}{/if}</td
								>
								<td class="ctl-title"
									>{c?.title ?? item.content_id}{#if c?.artist}<span class="ctl-muted ctl-after">
											· {c.artist}</span
										>{/if}</td
								>
								<td>
									{#if editing === item.id}
										<!-- svelte-ignore a11y_autofocus -->
										<input
											class="ctl-input singer"
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
										{item.singer ?? ''}
									{/if}
								</td>
								<td class="ctl-num"
									>{item.semitones ? `${item.semitones > 0 ? '+' : ''}${item.semitones}` : ''}</td
								>
								<td
									><span
										class="ctl-badge {state === 'ready'
											? 'ctl-ok'
											: state === 'failed'
												? 'ctl-bad'
												: state === 'absent'
													? ''
													: 'ctl-warn'}">{t.live.cache[state]}</span
									></td
								>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</section>

		<div>
			<section class="ctl-panel now">
				<div class="ctl-panel-head"><h2>{t.live.nowPlaying}</h2></div>
				<div class="ctl-panel-body">
					{#if song}
						<p class="song">{song.title}</p>
						<p class="ctl-muted">
							{song.artist ?? ''}{#if current?.singer}
								· {t.live.sungBy(current.singer)}{/if}
						</p>
					{:else}
						<p class="song ctl-muted">{t.status.nothing}</p>
					{/if}
					<div class="time">
						<span class="ctl-mono">{clock(position)}</span>
						<div class="ctl-progress">
							<div
								class="ctl-track"
								role="meter"
								aria-label={t.live.position}
								aria-valuemin={0}
								aria-valuemax={end || 1}
								aria-valuenow={position ?? 0}
							>
								<span style:width={`${end ? Math.min(100, ((position ?? 0) / end) * 100) : 0}%`}
								></span>
							</div>
						</div>
						<span class="ctl-mono">{clock(end || null)}</span>
					</div>
					<div class="transport">
						<button
							class="ctl-btn"
							onclick={transport.previous}
							aria-label={t.cmd.previous}
							title={`${t.cmd.previous} (P)`}><Icon name="previous" size={16} /></button
						>
						<button
							class="ctl-btn"
							onclick={() => transport.seekBy(-5)}
							aria-label={t.cmd.back}
							title={`${t.cmd.back} (←)`}><Icon name="back" size={16} /></button
						>
						<button class="ctl-btn ctl-primary play" onclick={transport.toggle}
							><Icon name={target?.status.state === 'playing' ? 'pause' : 'play'} size={16} />
							{target?.status.state === 'playing' ? t.cmd.pause : t.cmd.play}
							<Kbd keys="Space" /></button
						>
						<button
							class="ctl-btn"
							onclick={() => transport.seekBy(5)}
							aria-label={t.cmd.forward}
							title={`${t.cmd.forward} (→)`}
						>
							<Icon name="forward" size={16} /></button
						>
						<button
							class="ctl-btn"
							onclick={transport.next}
							aria-label={t.cmd.next}
							title={`${t.cmd.next} (N)`}><Icon name="next" size={16} /></button
						>
					</div>
					<dl class="ctl-kv levels">
						<dt>{t.live.volume}</dt>
						<dd>
							<span class="ctl-mono">{Math.round((target?.status.volume ?? 1) * 100)} %</span>
							<span class="keys"><Kbd keys="-" /> <Kbd keys="+" /></span>
						</dd>
						<dt>{t.live.key}</dt>
						<dd>
							<span>{t.status.key(target?.status.semitones ?? 0)}</span>
							<span class="keys"><Kbd keys="[" /> <Kbd keys="]" /></span>
						</dd>
					</dl>
				</div>
			</section>

			<section class="ctl-panel">
				<div class="ctl-panel-head"><h2>{t.live.upNext}</h2></div>
				{#if after.length === 0}
					<p class="ctl-empty">{t.home.nothingNext}</p>
				{:else}
					<table class="ctl-table">
						<tbody>
							{#each after as item, k (item.id)}
								{@const c = content(item.content_id)}
								<tr>
									<td class="ctl-num ctl-muted ctl-shrink">{index + k + 2}</td>
									<td class="ctl-title">{c?.title ?? item.content_id}</td>
									<td class="ctl-muted">{item.singer ?? ''}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}
			</section>
		</div>
	</div>
	<p class="ctl-hint">
		<Kbd keys="Enter" />
		{t.cmd.cue} · <Kbd keys="Shift+Enter" />
		{t.cmd.play} · <Kbd keys="Alt+ArrowUp" />
		<Kbd keys="Alt+ArrowDown" />
		{t.live.move} · <Kbd keys="Delete" />
		{t.cmd.remove} · <Kbd keys="s" />
		{t.live.singer} · <Kbd keys="i" />
		<Kbd keys="o" />
		{t.live.entryExit}
	</p>
</div>

<style>
	.playing {
		display: inline-flex;
		color: var(--accent-text);
	}
	input.singer {
		width: 100%;
		height: 1.75rem;
	}
	.now .song {
		font-size: var(--fs-xl);
		font-weight: 600;
	}
	.time {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: var(--sp-3);
		margin: var(--sp-4) 0;
		color: var(--text-2);
	}
	.transport {
		display: flex;
		gap: var(--sp-2);
	}
	.transport .play {
		flex: 1;
		justify-content: center;
	}
	.levels {
		margin-top: var(--sp-4);
		align-items: center;
	}
	.levels dd {
		display: flex;
		gap: var(--sp-3);
		align-items: center;
	}
	.keys {
		display: inline-flex;
		gap: var(--sp-1);
	}
</style>

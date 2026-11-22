<script lang="ts">
	/**
	 * Playback: what the chosen screen plays now (with a preview of its lyrics) and its queue. A
	 * song is added by searching it above the queue: Enter puts it at the end, Shift+Enter right
	 * after the one playing. Rows drag to reorder; J/K move, Enter cues, Shift+Enter plays now,
	 * Delete removes, Alt+↑/↓ moves.
	 */
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { rank } from '#lib/commands/fuzzy.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Icon from '#lib/console/Icon.svelte';
	import Monitor from '#lib/console/Monitor.svelte';
	import { now } from '#lib/console/now.svelte.js';
	import { onScreen, toneOf } from '#lib/console/screen.js';
	import { live } from '#lib/control/live.svelte.js';
	import { positionNow } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import {
		addToQueue,
		moveInQueue,
		placeInQueue,
		player,
		queueOf,
		removeFromQueue,
		transport,
		updateItem
	} from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import { Selection } from '#lib/shell/selection.svelte.js';
	import Coast from '#lib/ui/Coast.svelte';

	const t = $derived(i18n.t);
	const target = $derived(player());
	const on = $derived(onScreen(live.state, target));
	const queue = $derived(queueOf(target?.id));
	const items = $derived(queue?.items ?? []);
	const currentIndex = $derived(items.findIndex((i) => i.id === target?.status.item_id));
	const selection = new Selection(() => items.map((i) => i.id));
	const position = $derived.by(() => {
		void now.value;
		return target ? positionNow(live.state, target, now.value) : null;
	});
	const cacheOf = (contentId: string) =>
		target?.status.cache.find((c) => c.content_id === contentId);
	const song = (id: string) => live.state.contents.find((c) => c.id === id);
	const errors = $derived(target?.status.errors ?? []);
	const status = $derived(target?.status.state ?? 'idle');

	let search = $state('');
	let pick = $state(0);
	const found = $derived(
		search.trim() ? rank(search, live.state.contents, (c) => `${c.title} ${c.artist ?? ''}`, 8) : []
	);
	let dragging = $state<string | null>(null);
	let over = $state<string | null>(null);

	function add(id: string, next = false) {
		void addToQueue([id], next);
		search = '';
		pick = 0;
	}

	function quickKey(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') {
			pick = Math.min(pick + 1, found.length - 1);
			event.preventDefault();
		} else if (event.key === 'ArrowUp') {
			pick = Math.max(pick - 1, 0);
			event.preventDefault();
		} else if (event.key === 'Enter' && found[pick]) {
			event.preventDefault();
			add(found[pick].id, event.shiftKey);
		}
	}

	function drop(beforeId: string | null) {
		if (dragging) void placeInQueue(dragging, beforeId);
		dragging = null;
		over = null;
	}

	function cacheTone(state: string): string {
		if (state === 'failed') return 'error';
		if (state === 'ready') return 'ok';
		return 'info';
	}

	onMount(() => {
		commands.scope = 'live';
		const stop = now.use();
		const group = () => t.groups.queue;
		const unregister = commands.register(
			{
				id: 'live.down',
				title: () => t.cmd.down,
				group,
				scope: 'live',
				keys: ['j', 'ArrowDown'],
				run: () => selection.move(1),
				hidden: true
			},
			{
				id: 'live.up',
				title: () => t.cmd.up,
				group,
				scope: 'live',
				keys: ['k', 'ArrowUp'],
				run: () => selection.move(-1),
				hidden: true
			},
			{
				id: 'live.cue',
				title: () => t.cmd.cue,
				group,
				scope: 'live',
				keys: ['Enter'],
				run: () => void (selection.current && transport.cue(selection.current))
			},
			{
				id: 'live.playNow',
				title: () => t.cmd.playNow,
				group,
				scope: 'live',
				keys: ['Shift+Enter'],
				run: () => void (selection.current && transport.playItem(selection.current))
			},
			{
				id: 'live.remove',
				title: () => t.cmd.remove,
				group,
				scope: 'live',
				keys: ['Delete', 'Backspace'],
				run: () => removeFromQueue(selection.targets)
			},
			{
				id: 'live.moveUp',
				title: () => t.cmd.moveUp,
				group,
				scope: 'live',
				keys: ['Alt+ArrowUp'],
				run: () => moveInQueue(selection.targets, -1)
			},
			{
				id: 'live.moveDown',
				title: () => t.cmd.moveDown,
				group,
				scope: 'live',
				keys: ['Alt+ArrowDown'],
				run: () => moveInQueue(selection.targets, 1)
			},
			{
				id: 'live.mark',
				title: () => t.cmd.toggleSelect,
				group,
				scope: 'live',
				keys: ['x'],
				run: () => selection.toggle()
			}
		);
		return () => {
			stop();
			unregister();
		};
	});
</script>

<div class="page">
	<header class="page-header">
		<div>
			<h1>{t.playback.title}{target ? ` · ${target.name}` : ''}</h1>
			<p class="description">{t.playback.description}</p>
		</div>
	</header>

	{#if !live.state.players.length}
		<section class="panel">
			<div class="empty">
				<Coast class="empty-coast" />
				<strong>{t.playback.noScreens}</strong>
				<p>{t.playback.noScreensHint}</p>
				<a class="btn" href={resolve('/equipos')}>{t.nav.devices}</a>
			</div>
		</section>
	{:else}
		<section class="panel now">
			<div class="preview"><Monitor song={on.song} {position} /></div>
			<div class="info">
				<span class="badge {toneOf(target)}">
					{target?.online ? t.player.states[status] : t.player.offline}
				</span>
				{#if on.song}
					<h2 class="song-title">{on.song.title}</h2>
					<p class="muted">{on.song.artist ?? ''}</p>
					<dl class="details">
						{#if on.item?.singer}
							<dt>{t.playback.singer}</dt>
							<dd>{on.item.singer}</dd>
						{/if}
						<dt>{t.playback.duration}</dt>
						<dd class="mono">{clock(on.song.duration)}</dd>
						<dt>{t.player.key}</dt>
						<dd class="mono">{t.player.semitones(target?.status.semitones ?? 0)}</dd>
						{#if on.next?.song}
							<dt>{t.player.next}</dt>
							<dd>{on.next.song.title}</dd>
						{/if}
					</dl>
				{:else}
					<p class="muted">{t.player.nothing}</p>
				{/if}
				{#if errors.length}
					<div class="notice warn alerts" role="alert">
						<Icon name="warn" size={18} />
						<div>
							<strong>{t.playback.alerts}</strong>
							<ul>
								{#each errors as error, i (i)}
									<li>
										{t.playerErrors[error.code] ?? error.code}
										{#if error.device}<span class="muted">· {error.device}</span>{/if}
									</li>
								{/each}
							</ul>
						</div>
					</div>
				{/if}
			</div>
		</section>

		<section class="panel">
			<header class="panel-header">
				<h2>{t.playback.queue}</h2>
				<span class="muted small">{t.library.count(items.length)}</span>
			</header>
			<div class="quick">
				<Icon name="search" size={16} />
				<input
					class="field"
					bind:value={search}
					onkeydown={quickKey}
					oninput={() => (pick = 0)}
					placeholder={t.playback.addPlaceholder}
					aria-label={t.playback.addPlaceholder}
					data-search
				/>
				{#if found.length}
					<ul class="found" role="listbox">
						{#each found as c, i (c.id)}
							<li role="option" aria-selected={i === pick}>
								<button class:active={i === pick} onclick={() => add(c.id)}>
									<span>{c.title}</span>
									<span class="muted">{c.artist ?? ''}</span>
									<span class="mono muted">{clock(c.duration)}</span>
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
			{#if items.length}
				<table class="table queue">
					<thead>
						<tr>
							<th class="num">{t.playback.number}</th>
							<th>{t.playback.song}</th>
							<th>{t.playback.singer}</th>
							<th class="num">{t.playback.duration}</th>
							<th>{t.playback.status}</th>
							<th><span class="sr-only">{t.common.more}</span></th>
						</tr>
					</thead>
					<tbody>
						{#each items as item, i (item.id)}
							{@const c = song(item.content_id)}
							{@const cache = cacheOf(item.content_id)}
							{@const isOn = item.id === target?.status.item_id}
							<tr
								aria-selected={selection.cursor === i}
								class:selected={selection.cursor === i || selection.marked.has(item.id)}
								class:on={isOn}
								class:played={currentIndex >= 0 && i < currentIndex}
								class:over={over === item.id}
								draggable="true"
								ondragstart={() => (dragging = item.id)}
								ondragover={(e) => {
									e.preventDefault();
									over = item.id;
								}}
								ondragend={() => ((dragging = null), (over = null))}
								ondrop={(e) => {
									e.preventDefault();
									drop(item.id);
								}}
								onclick={() => (selection.cursor = i)}
							>
								<td class="num faint">{i + 1}</td>
								<td>
									<div class="song-cell">
										<strong class="truncate">{c?.title ?? item.content_id}</strong>
										<span class="muted small truncate">{c?.artist ?? ''}</span>
									</div>
								</td>
								<td>
									<input
										class="singer"
										value={item.singer ?? ''}
										placeholder="—"
										aria-label={t.playback.singer}
										onchange={(e) =>
											void updateItem(item.id, { singer: e.currentTarget.value || null })}
										onclick={(e) => e.stopPropagation()}
									/>
								</td>
								<td class="num muted">{clock(c?.duration)}</td>
								<td>
									{#if isOn}
										<span class="badge ok">{t.playback.onNow}</span>
									{:else if currentIndex >= 0 && i < currentIndex}
										<span class="faint small">{t.playback.played}</span>
									{:else if cache}
										<span class="badge {cacheTone(cache.state)}">
											{t.playback.cache[cache.state]}{cache.state === 'downloading'
												? ` ${Math.round(cache.fraction * 100)} %`
												: ''}
										</span>
									{/if}
								</td>
								<td class="row-actions">
									<button
										class="btn subtle icon"
										title={t.cmd.playNow}
										aria-label={t.cmd.playNow}
										onclick={() => transport.playItem(item.id)}
									>
										<Icon name="play" size={16} />
									</button>
									<button
										class="btn subtle icon"
										title={t.cmd.edit}
										aria-label={t.cmd.edit}
										onclick={() => goto(resolve('/editar/[id]', { id: item.content_id }))}
									>
										<Icon name="edit" size={16} />
									</button>
									<button
										class="btn subtle icon"
										title={t.cmd.remove}
										aria-label={t.cmd.remove}
										onclick={() => removeFromQueue([item.id])}
									>
										<Icon name="close" size={16} />
									</button>
								</td>
							</tr>
						{/each}
						<tr
							class="tail"
							class:over={over === '$end'}
							ondragover={(e) => {
								e.preventDefault();
								over = '$end';
							}}
							ondrop={(e) => {
								e.preventDefault();
								drop(null);
							}}
						>
							<td colspan="6" class="faint small">{t.playback.dragHint}</td>
						</tr>
					</tbody>
				</table>
			{:else}
				<div class="empty">
					<p>{t.playback.queueEmpty}</p>
					<a class="btn" href={resolve('/biblioteca')}>{t.nav.library}</a>
				</div>
			{/if}
		</section>
	{/if}
</div>

<style>
	.empty :global(.empty-coast) {
		height: 140px;
		color: var(--accent);
		opacity: 0.25;
		margin-bottom: 8px;
	}
	.now {
		display: grid;
		grid-template-columns: minmax(280px, 460px) minmax(0, 1fr);
		gap: 20px;
		padding: 16px;
	}
	.info {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 8px;
		min-width: 0;
	}
	.song-title {
		font-size: 18px;
	}
	.info .details {
		margin-top: 8px;
	}
	.alerts {
		margin-top: 8px;
		align-self: stretch;
		color: var(--text);
	}
	.alerts :global(svg) {
		flex: none;
		color: var(--warn);
	}
	.alerts ul {
		margin: 4px 0 0;
		padding-left: 18px;
	}
	.quick {
		position: relative;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
		color: var(--muted);
	}
	.found {
		position: absolute;
		z-index: 10;
		top: calc(100% - 6px);
		left: 42px;
		right: 16px;
		margin: 0;
		padding: 4px;
		list-style: none;
		background: var(--surface-2);
		border: 1px solid var(--border-strong);
		border-radius: var(--radius);
		box-shadow: 0 16px 40px -12px rgb(0 0 0 / 0.6);
	}
	.found button {
		display: grid;
		grid-template-columns: 1fr auto auto;
		gap: 12px;
		width: 100%;
		padding: 7px 10px;
		border: 0;
		border-radius: 4px;
		background: none;
		text-align: left;
		cursor: pointer;
	}
	.found button.active,
	.found button:hover {
		background: var(--accent-soft);
	}
	.queue th:first-child,
	.queue td:first-child {
		width: 48px;
	}
	.queue tbody tr {
		cursor: default;
	}
	.queue tr.on td:first-child {
		box-shadow: inset 3px 0 0 var(--ok);
	}
	.queue tr.played {
		opacity: 0.5;
	}
	.queue tr.over td,
	.queue tr.tail.over td {
		box-shadow: inset 0 2px 0 var(--accent);
	}
	.queue tr.tail:hover {
		background: none;
	}
	.song-cell {
		display: flex;
		flex-direction: column;
		min-width: 0;
		max-width: 420px;
	}
	.singer {
		width: 140px;
		height: 28px;
		padding: 0 8px;
		border: 1px solid transparent;
		border-radius: 4px;
		background: transparent;
	}
	.singer:hover,
	.singer:focus {
		border-color: var(--border-strong);
		background: var(--bg);
		outline: none;
	}
	.row-actions {
		width: 120px;
	}
	.row-actions .btn {
		opacity: 0;
	}
	tr:hover .row-actions .btn,
	tr.selected .row-actions .btn,
	.row-actions .btn:focus-visible {
		opacity: 1;
	}

	@media (max-width: 1000px) {
		.now {
			grid-template-columns: minmax(0, 1fr);
		}
		.row-actions .btn {
			opacity: 1;
		}
	}
	@media (max-width: 640px) {
		.queue th:nth-child(3),
		.queue td:nth-child(3),
		.queue th:nth-child(4),
		.queue td:nth-child(4) {
			display: none;
		}
	}
</style>

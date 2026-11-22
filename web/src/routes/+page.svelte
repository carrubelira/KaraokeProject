<script lang="ts">
	/**
	 * Live: the chosen screen's program monitor (its lyrics filling in sync), its alerts, and its
	 * queue, which is always there to add to: search a song and Enter puts it at the end (Shift+
	 * Enter right after the song on air). Rows drag to reorder; J/K move, Enter cues, Shift+Enter
	 * plays now, Delete removes, Alt+↑/↓ moves.
	 */
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { rank } from '#lib/commands/fuzzy.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Icon from '#lib/console/Icon.svelte';
	import Monitor from '#lib/console/Monitor.svelte';
	import { now } from '#lib/console/now.svelte.js';
	import { onAir } from '#lib/console/on-air.js';
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

	const t = $derived(i18n.t);
	const target = $derived(player());
	const air = $derived(onAir(live.state, target));
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

	let search = $state('');
	let pick = $state(0);
	const found = $derived(
		search.trim() ? rank(search, live.state.contents, (c) => `${c.title} ${c.artist ?? ''}`, 8) : []
	);
	let dragging = $state<string | null>(null);
	let over = $state<string | null>(null);

	function quickKey(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') {
			pick = Math.min(pick + 1, found.length - 1);
			event.preventDefault();
		} else if (event.key === 'ArrowUp') {
			pick = Math.max(pick - 1, 0);
			event.preventDefault();
		} else if (event.key === 'Enter' && found[pick]) {
			event.preventDefault();
			void addToQueue([found[pick].id], event.shiftKey);
			search = '';
			pick = 0;
		}
	}

	function drop(beforeId: string | null) {
		if (dragging) void placeInQueue(dragging, beforeId);
		dragging = null;
		over = null;
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

<div class="c-page live">
	{#if !live.state.players.length}
		<section class="c-panel empty-state">
			<div class="c-empty">
				<strong>{t.live.noPlayer}</strong>
				<p>{t.live.noPlayerHint}</p>
				<a class="c-btn" href={resolve('/nodos')}><Icon name="nodes" /> {t.nav.nodes}</a>
			</div>
		</section>
	{:else}
		<div class="grid">
			<section class="c-panel program" class:is-onair={air.tally === 'onair'}>
				<header class="c-panel-head">
					<h2>{t.live.program}</h2>
					<span class="c-tag">{target?.name}</span>
					<span class="spacer"></span>
					{#if air.song}
						{@const cache = cacheOf(air.song.id)}
						{#if cache && cache.state !== 'ready'}
							<span class="c-tag {cache.state === 'failed' ? 'onair' : 'info'}"
								>{t.live.cache[cache.state]}
								{cache.state === 'downloading' ? `${Math.round(cache.fraction * 100)} %` : ''}</span
							>
						{/if}
					{/if}
				</header>
				<div class="c-panel-body">
					<Monitor song={air.song} {position} tally={air.tally} singer={air.item?.singer ?? null} />
				</div>
				{#if errors.length}
					<div class="alerts" role="alert">
						<span class="label">{t.live.alerts}</span>
						{#each errors as error, i (i)}
							<div class="alert">
								<Icon name="warn" size={16} />
								<span>{t.playerErrors[error.code] ?? error.code}</span>
								<span class="dim mono small">{error.device ?? ''}</span>
							</div>
						{/each}
					</div>
				{/if}
			</section>

			<section class="c-panel queue">
				<header class="c-panel-head">
					<h2>{t.live.queue(target?.name ?? '')}</h2>
					<span class="spacer"></span>
					<span class="label">{items.length}</span>
				</header>
				<div class="quick">
					<Icon name="search" />
					<input
						class="c-field"
						bind:value={search}
						onkeydown={quickKey}
						oninput={() => (pick = 0)}
						placeholder={t.live.quickAdd}
						aria-label={t.live.quickAdd}
						data-search
					/>
					{#if found.length}
						<ul class="found" role="listbox">
							{#each found as c, i (c.id)}
								<li role="option" aria-selected={i === pick}>
									<button
										class:active={i === pick}
										onclick={() => {
											void addToQueue([c.id]);
											search = '';
										}}
									>
										<span>{c.title}</span>
										<span class="dim">{c.artist ?? ''}</span>
										<span class="mono dim small">{clock(c.duration)}</span>
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
				{#if items.length}
					<ol class="c-rows list" role="listbox" aria-label={t.live.queue(target?.name ?? '')}>
						{#each items as item, i (item.id)}
							{@const c = song(item.content_id)}
							{@const cache = cacheOf(item.content_id)}
							{@const isOn = item.id === target?.status.item_id}
							<li
								class="c-row row"
								role="option"
								aria-selected={selection.cursor === i}
								class:is-cursor={selection.cursor === i}
								class:is-marked={selection.marked.has(item.id)}
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
								onkeydown={() => {}}
							>
								<span class="grip faint" title={t.live.dragHint}
									><Icon name="grip" size={16} /></span
								>
								<span class="index mono">{String(i + 1).padStart(2, '0')}</span>
								<span class="what">
									<span class="name">
										{#if isOn}<span class="c-tally {air.tally}"></span>{/if}
										{c?.title ?? item.content_id}
									</span>
									<span class="dim small"
										>{c?.artist ?? ''} · <span class="mono">{clock(c?.duration)}</span></span
									>
								</span>
								<input
									class="singer"
									value={item.singer ?? ''}
									placeholder={t.live.singer}
									aria-label={t.live.singer}
									onchange={(e) =>
										void updateItem(item.id, { singer: e.currentTarget.value || null })}
									onclick={(e) => e.stopPropagation()}
								/>
								{#if cache && cache.state !== 'ready'}
									<span class="c-tag {cache.state === 'failed' ? 'onair' : 'info'}"
										>{t.live.cache[cache.state]}</span
									>
								{/if}
								<span class="actions">
									<button
										class="c-btn icon ghost"
										title={t.cmd.playNow}
										aria-label={t.cmd.playNow}
										onclick={() => transport.playItem(item.id)}
									>
										<Icon name="play" size={16} />
									</button>
									<button
										class="c-btn icon ghost"
										title={t.cmd.edit}
										aria-label={t.cmd.edit}
										onclick={() => goto(resolve('/editar/[id]', { id: item.content_id }))}
									>
										<Icon name="edit" size={16} />
									</button>
									<button
										class="c-btn icon ghost"
										title={t.cmd.remove}
										aria-label={t.cmd.remove}
										onclick={() => removeFromQueue([item.id])}
									>
										<Icon name="close" size={16} />
									</button>
								</span>
							</li>
						{/each}
						<li
							class="tail"
							role="presentation"
							class:over={over === '$end'}
							ondragover={(e) => {
								e.preventDefault();
								over = '$end';
							}}
							ondrop={(e) => {
								e.preventDefault();
								drop(null);
							}}
						></li>
					</ol>
				{:else}
					<div class="c-empty">
						<p>{t.live.queueEmpty}</p>
						<a class="c-btn" href={resolve('/biblioteca')}
							><Icon name="library" /> {t.nav.library}</a
						>
					</div>
				{/if}
			</section>
		</div>
	{/if}
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: minmax(0, 1.35fr) minmax(360px, 1fr);
		gap: var(--gap);
		align-items: start;
	}
	.program {
		position: sticky;
		top: 0;
	}
	.alerts {
		display: grid;
		gap: 6px;
		padding: 12px;
		border-top: 1px solid rgb(255 176 32 / 0.3);
		background: rgb(255 176 32 / 0.05);
	}
	.alert {
		display: flex;
		align-items: center;
		gap: 10px;
		color: var(--warn);
		font-size: 13.5px;
	}
	.quick {
		position: relative;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 12px;
		border-bottom: 1px solid var(--line);
		color: var(--dim);
	}
	.found {
		position: absolute;
		z-index: 10;
		top: 100%;
		left: 12px;
		right: 12px;
		margin: 0;
		padding: 4px;
		list-style: none;
		background: var(--panel-solid);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius);
		box-shadow: 0 20px 50px -10px rgb(0 0 0 / 0.8);
	}
	.found button {
		display: grid;
		grid-template-columns: 1fr auto auto;
		gap: 12px;
		width: 100%;
		padding: 8px 10px;
		border: 0;
		background: none;
		text-align: left;
		cursor: pointer;
		border-radius: 2px;
	}
	.found button.active,
	.found button:hover {
		background: rgb(60 200 255 / 0.1);
	}
	.list {
		max-height: calc(100dvh - var(--strip) - var(--deck) - 160px);
		overflow-y: auto;
	}
	.row {
		cursor: default;
	}
	.row.on {
		background: rgb(255 58 70 / 0.06);
		box-shadow: inset 2px 0 0 var(--onair);
	}
	.row.played {
		opacity: 0.45;
	}
	.row.over,
	.tail.over {
		box-shadow: inset 0 2px 0 var(--info);
	}
	.tail {
		height: 24px;
	}
	.grip {
		cursor: grab;
		display: flex;
	}
	.index {
		color: var(--faint);
		font-size: 12px;
		width: 20px;
	}
	.what {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1;
		min-width: 0;
	}
	.name {
		display: flex;
		align-items: center;
		gap: 8px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-weight: 600;
	}
	.small {
		font-size: 12px;
	}
	.singer {
		width: 110px;
		padding: 5px 8px;
		border: 1px solid transparent;
		border-radius: 2px;
		background: transparent;
		color: var(--info);
		font: 500 12px var(--font-mono);
	}
	.singer:hover,
	.singer:focus {
		border-color: var(--line-strong);
		background: rgb(0 0 0 / 0.4);
		outline: none;
	}
	.actions {
		display: flex;
		opacity: 0;
		transition: opacity 0.12s;
	}
	.row:hover .actions,
	.row.is-cursor .actions {
		opacity: 1;
	}

	@media (max-width: 640px) {
		.grip,
		.index,
		.singer {
			display: none;
		}
	}
	@media (max-width: 1100px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.program {
			position: static;
		}
		.list {
			max-height: none;
		}
		.actions {
			opacity: 1;
		}
	}
</style>

<script lang="ts">
	/**
	 * The library: every song, searchable, driven from the keyboard (scope `library`). One key
	 * puts the marked songs in the chosen screen's queue (A at the end, Shift+A right after the
	 * song on air); a song already queued there carries its mark.
	 */
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { rank } from '#lib/commands/fuzzy.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Icon from '#lib/console/Icon.svelte';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { addToQueue, library } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { Selection } from '#lib/shell/selection.svelte.js';

	let query = $state('');
	const t = $derived(i18n.t);
	const songs = $derived(
		rank(query, live.state.contents, (c) => `${c.title} ${c.artist ?? ''} ${c.language}`, 5000)
	);
	const selection = new Selection(() => songs.map((s) => s.id));
	const queued = $derived(new Set(live.state.queue.items.map((i) => i.content_id)));

	$effect(() => {
		void songs.length;
		selection.clamp();
	});

	$effect(() => {
		const id = selection.current;
		if (id) document.getElementById(`song-${id}`)?.scrollIntoView({ block: 'nearest' });
	});

	onMount(() => {
		commands.scope = 'library';
		const group = () => t.groups.library;
		const scope = 'library' as const;
		return commands.register(
			{
				id: 'library.down',
				title: () => t.cmd.down,
				group,
				scope,
				keys: ['j', 'ArrowDown'],
				run: () => selection.move(1),
				hidden: true
			},
			{
				id: 'library.up',
				title: () => t.cmd.up,
				group,
				scope,
				keys: ['k', 'ArrowUp'],
				run: () => selection.move(-1),
				hidden: true
			},
			{
				id: 'library.extendDown',
				title: () => t.cmd.selectDown,
				group,
				scope,
				keys: ['Shift+j', 'Shift+ArrowDown'],
				run: () => selection.extend(1)
			},
			{
				id: 'library.extendUp',
				title: () => t.cmd.selectUp,
				group,
				scope,
				keys: ['Shift+k', 'Shift+ArrowUp'],
				run: () => selection.extend(-1)
			},
			{
				id: 'library.mark',
				title: () => t.cmd.toggleSelect,
				group,
				scope,
				keys: ['x'],
				run: () => selection.toggle()
			},
			{
				id: 'library.all',
				title: () => t.cmd.selectAll,
				group,
				scope,
				keys: ['Mod+a'],
				run: () => selection.all()
			},
			{
				id: 'library.add',
				title: () => t.cmd.addToQueue,
				group,
				scope,
				keys: ['a', 'Enter'],
				run: () => addToQueue(selection.targets).then(() => selection.clear())
			},
			{
				id: 'library.addNext',
				title: () => t.cmd.addNext,
				group,
				scope,
				keys: ['Shift+a'],
				run: () => addToQueue(selection.targets, true).then(() => selection.clear())
			},
			{
				id: 'library.edit',
				title: () => t.cmd.edit,
				group,
				scope,
				keys: ['e'],
				run: () => {
					if (selection.current) void goto(resolve('/editar/[id]', { id: selection.current }));
				}
			},
			{
				id: 'library.export',
				title: () => t.cmd.export,
				group,
				scope,
				keys: ['m'],
				run: () => library.exportMp4(selection.targets)
			},
			{
				id: 'library.trash',
				title: () => t.cmd.trash,
				group,
				scope,
				keys: ['Delete', 'Backspace'],
				run: () => library.trash(selection.targets).then(() => selection.clear())
			}
		);
	});
</script>

<div class="page">
	<header class="page-header">
		<div>
			<h1>{t.library.title}</h1>
			<p class="description">{t.library.count(live.state.contents.length)}</p>
		</div>
		<div class="actions">
			<label class="search">
				<Icon name="search" size={16} />
				<input
					class="field"
					data-search
					bind:value={query}
					placeholder={t.library.search}
					aria-label={t.library.search}
					onkeydown={(e) => {
						if (e.key === 'Enter' || e.key === 'ArrowDown') {
							e.currentTarget.blur();
							e.preventDefault();
						}
					}}
				/>
			</label>
			<a class="btn primary" href={resolve('/engadir')}>
				<Icon name="add" size={16} />
				{t.nav.add}
			</a>
		</div>
	</header>

	<section class="panel">
		{#if songs.length === 0}
			<div class="empty">
				<p>{t.library.empty}</p>
			</div>
		{:else}
			<table class="table songs">
				<thead>
					<tr>
						<th>{t.library.songTitle}</th>
						<th>{t.library.artist}</th>
						<th>{t.library.language}</th>
						<th class="num">{t.library.duration}</th>
						<th class="num">{t.library.version}</th>
						<th><span class="sr-only">{t.common.more}</span></th>
					</tr>
				</thead>
				<tbody>
					{#each songs as song, i (song.id)}
						<tr
							id={`song-${song.id}`}
							class:selected={i === selection.cursor || selection.marked.has(song.id)}
							aria-selected={i === selection.cursor}
							onclick={() => (selection.cursor = i)}
							ondblclick={() => addToQueue([song.id])}
						>
							<td>
								<span class="title">
									<strong class="truncate">{song.title}</strong>
									{#if queued.has(song.id)}
										<span class="badge ok plain">{t.library.inQueue}</span>
									{/if}
								</span>
							</td>
							<td class="muted">{song.artist ?? ''}</td>
							<td class="muted">{t.languages[song.language] ?? song.language}</td>
							<td class="num muted">{clock(song.duration)}</td>
							<td class="num faint">{song.version}</td>
							<td class="row-actions">
								<button
									class="btn"
									onclick={(e) => (e.stopPropagation(), void addToQueue([song.id]))}
								>
									{t.cmd.addToQueue}
								</button>
								<button
									class="btn subtle icon"
									title={t.cmd.edit}
									aria-label={t.cmd.edit}
									onclick={() => goto(resolve('/editar/[id]', { id: song.id }))}
								>
									<Icon name="edit" size={16} />
								</button>
								<button
									class="btn subtle icon"
									title={t.cmd.export}
									aria-label={t.cmd.export}
									onclick={() => library.exportMp4([song.id])}
								>
									<Icon name="export" size={16} />
								</button>
								<button
									class="btn subtle icon"
									title={t.cmd.trash}
									aria-label={t.cmd.trash}
									onclick={() => library.trash([song.id])}
								>
									<Icon name="trash" size={16} />
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
	<p class="keys faint small">
		<Kbd keys="a" />
		{t.cmd.addToQueue} · <Kbd keys="Shift+a" />
		{t.cmd.addNext} · <Kbd keys="x" />
		{t.cmd.toggleSelect} · <Kbd keys="e" />
		{t.cmd.edit} · <Kbd keys="m" />
		{t.cmd.export} · <Kbd keys="Delete" />
		{t.cmd.trash}
	</p>
</div>

<style>
	.search {
		position: relative;
		display: flex;
		align-items: center;
		width: min(22rem, 100%);
		color: var(--faint);
	}
	.search :global(svg) {
		position: absolute;
		left: 10px;
	}
	.search .field {
		height: 32px;
		padding-left: 32px;
	}
	.songs tbody tr {
		cursor: default;
	}
	.title {
		display: flex;
		align-items: center;
		gap: 8px;
		max-width: 380px;
		min-width: 0;
	}
	.row-actions .btn {
		opacity: 0;
	}
	tr:hover .row-actions .btn,
	tr.selected .row-actions .btn,
	.row-actions .btn:focus-visible {
		opacity: 1;
	}
	@media (max-width: 760px) {
		.songs th:nth-child(n + 3):nth-child(-n + 5),
		.songs td:nth-child(n + 3):nth-child(-n + 5) {
			display: none;
		}
		.row-actions .btn {
			opacity: 1;
		}
	}
</style>

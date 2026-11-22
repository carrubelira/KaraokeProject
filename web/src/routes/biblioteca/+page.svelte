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
	import { addToQueue, library, player, queueOf } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { Selection } from '#lib/shell/selection.svelte.js';

	let query = $state('');
	const t = $derived(i18n.t);
	const target = $derived(player());
	const songs = $derived(
		rank(query, live.state.contents, (c) => `${c.title} ${c.artist ?? ''} ${c.language}`, 5000)
	);
	const selection = new Selection(() => songs.map((s) => s.id));
	const queued = $derived(new Set(queueOf(target?.id)?.items.map((i) => i.content_id) ?? []));

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

<div class="c-page">
	<div class="c-page-head">
		<h1>{t.library.title}</h1>
		<span class="label">{t.library.count(live.state.contents.length)}</span>
		<span class="spacer"></span>
		<label class="search">
			<Icon name="search" size={16} />
			<input
				class="c-field"
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
			<Kbd keys="/" />
		</label>
	</div>

	<section class="c-panel">
		{#if songs.length === 0}
			<div class="c-empty">
				<p>{t.library.empty}</p>
				<a class="c-btn" href={resolve('/engadir')}><Icon name="add" size={16} /> {t.nav.add}</a>
			</div>
		{:else}
			<ul class="c-rows" role="listbox" aria-label={t.library.title} aria-multiselectable="true">
				{#each songs as song, i (song.id)}
					<li
						id={`song-${song.id}`}
						class="c-row song"
						class:is-cursor={i === selection.cursor}
						class:is-marked={selection.marked.has(song.id)}
						role="option"
						aria-selected={i === selection.cursor}
						onclick={() => (selection.cursor = i)}
						ondblclick={() => addToQueue([song.id])}
						onkeydown={() => {}}
					>
						<span class="what">
							<span class="title">{song.title}</span>
							<span class="dim small">{song.artist ?? ''}</span>
						</span>
						<span class="c-tag">{song.language}</span>
						<span class="mono dim small">{clock(song.duration)}</span>
						<span class="mono faint small">{t.library.version(song.version)}</span>
						<span class="mark"
							>{#if queued.has(song.id)}<span class="c-tally cue" title={target?.name}
								></span>{/if}</span
						>
						<span class="actions">
							<button
								class="c-btn"
								onclick={(e) => (e.stopPropagation(), void addToQueue([song.id]))}
							>
								<Icon name="add" size={14} />
								{t.cmd.addToQueue}
							</button>
							<button
								class="c-btn icon ghost"
								title={t.cmd.edit}
								aria-label={t.cmd.edit}
								onclick={() => goto(resolve('/editar/[id]', { id: song.id }))}
							>
								<Icon name="edit" size={16} />
							</button>
							<button
								class="c-btn icon ghost"
								title={t.cmd.export}
								aria-label={t.cmd.export}
								onclick={() => library.exportMp4([song.id])}
							>
								<Icon name="export" size={16} />
							</button>
							<button
								class="c-btn icon ghost"
								title={t.cmd.trash}
								aria-label={t.cmd.trash}
								onclick={() => library.trash([song.id])}
							>
								<Icon name="trash" size={16} />
							</button>
						</span>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
	<p class="keys faint">
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
		display: flex;
		align-items: center;
		gap: 10px;
		width: min(30rem, 100%);
		color: var(--dim);
	}
	.song {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto 3.5rem 2.5rem 1rem auto;
	}
	.what {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.title {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.small {
		font-size: 12px;
	}
	.actions {
		display: flex;
		gap: 4px;
		opacity: 0;
		transition: opacity 0.12s;
	}
	.song:hover .actions,
	.song.is-cursor .actions {
		opacity: 1;
	}
	.keys {
		font-size: 12px;
		margin: 0 4px;
	}
	@media (max-width: 760px) {
		.song {
			grid-template-columns: minmax(0, 1fr) auto;
		}
		.song > :nth-child(n + 3):not(.actions) {
			display: none;
		}
		.actions {
			opacity: 1;
			grid-column: 1 / -1;
		}
	}
</style>

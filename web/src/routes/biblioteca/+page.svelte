<script lang="ts">
	/** The library: every song, searchable, driven from the keyboard (scope `library`). */
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { rank } from '#lib/commands/fuzzy.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { addToPlaylist, library, playlist } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { Selection } from '#lib/shell/selection.svelte.js';

	let query = $state('');
	const t = $derived(i18n.t);
	const songs = $derived(
		rank(query, live.state.contents, (c) => `${c.title} ${c.artist ?? ''} ${c.language}`, 5000)
	);
	const selection = new Selection(() => songs.map((s) => s.id));
	const inList = $derived(new Set(playlist()?.items.map((i) => i.content_id) ?? []));

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
		return commands.register(
			{
				id: 'library.down',
				title: () => t.cmd.down,
				group,
				scope: 'library',
				keys: ['j', 'ArrowDown'],
				run: () => selection.move(1),
				hidden: true
			},
			{
				id: 'library.up',
				title: () => t.cmd.up,
				group,
				scope: 'library',
				keys: ['k', 'ArrowUp'],
				run: () => selection.move(-1),
				hidden: true
			},
			{
				id: 'library.extendDown',
				title: () => t.cmd.selectDown,
				group,
				scope: 'library',
				keys: ['Shift+j', 'Shift+ArrowDown'],
				run: () => selection.extend(1)
			},
			{
				id: 'library.extendUp',
				title: () => t.cmd.selectUp,
				group,
				scope: 'library',
				keys: ['Shift+k', 'Shift+ArrowUp'],
				run: () => selection.extend(-1)
			},
			{
				id: 'library.mark',
				title: () => t.cmd.toggleSelect,
				group,
				scope: 'library',
				keys: ['x'],
				run: () => selection.toggle()
			},
			{
				id: 'library.all',
				title: () => t.cmd.selectAll,
				group,
				scope: 'library',
				keys: ['Mod+a'],
				run: () => selection.all()
			},
			{
				id: 'library.add',
				title: () => t.cmd.addToPlaylist,
				group,
				scope: 'library',
				keys: ['a', 'Enter'],
				run: () => addToPlaylist(selection.targets).then(() => selection.clear())
			},
			{
				id: 'library.addNext',
				title: () => t.cmd.addNext,
				group,
				scope: 'library',
				keys: ['Shift+a'],
				run: () => addToPlaylist(selection.targets, true).then(() => selection.clear())
			},
			{
				id: 'library.edit',
				title: () => t.cmd.edit,
				group,
				scope: 'library',
				keys: ['e'],
				run: () => {
					if (selection.current) void goto(resolve('/editar/[id]', { id: selection.current }));
				}
			},
			{
				id: 'library.export',
				title: () => t.cmd.export,
				group,
				scope: 'library',
				keys: ['m'],
				run: () => library.exportMp4(selection.targets)
			},
			{
				id: 'library.trash',
				title: () => t.cmd.trash,
				group,
				scope: 'library',
				keys: ['Delete', 'Backspace'],
				run: () => library.trash(selection.targets).then(() => selection.clear())
			}
		);
	});
</script>

<div class="ctl-page">
	<div class="ctl-page-head">
		<h1>{t.library.title}</h1>
		<span class="ctl-muted">{t.library.count(live.state.contents.length)}</span>
		<input
			class="ctl-field search"
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
		<span class="ctl-muted"><Kbd keys="/" /></span>
	</div>
	{#if songs.length === 0}
		<p class="ctl-muted">{t.library.empty}</p>
	{:else}
		<ul class="ctl-rows" role="listbox" aria-label={t.library.title} aria-multiselectable="true">
			{#each songs as song, i (song.id)}
				<li
					id={`song-${song.id}`}
					class="ctl-row song"
					class:ctl-cursor={i === selection.cursor}
					class:ctl-marked={selection.marked.has(song.id)}
					role="option"
					aria-selected={i === selection.cursor}
					onclick={() => (selection.cursor = i)}
					ondblclick={() => addToPlaylist([song.id])}
					onkeydown={() => {}}
				>
					<span class="title">{song.title}</span>
					<span class="ctl-muted">{song.artist ?? ''}</span>
					<span class="ctl-pill">{song.language}</span>
					<span class="ctl-muted mono">{clock(song.duration)}</span>
					<span class="ctl-muted">{t.library.version(song.version)}</span>
					<span
						>{#if inList.has(song.id)}<span class="ctl-pill ctl-warn">●</span>{/if}</span
					>
				</li>
			{/each}
		</ul>
	{/if}
	<p class="ctl-muted keys">
		<Kbd keys="a" />
		{t.cmd.addToPlaylist} · <Kbd keys="Shift+a" />
		{t.cmd.addNext} · <Kbd keys="x" />
		{t.cmd.toggleSelect} ·
		<Kbd keys="e" />
		{t.cmd.edit} · <Kbd keys="m" />
		{t.cmd.export} · <Kbd keys="Delete" />
		{t.cmd.trash}
	</p>
</div>

<style>
	.search {
		margin-left: auto;
		width: min(28rem, 50vw);
	}
	.song {
		grid-template-columns: minmax(10rem, 2fr) minmax(6rem, 1.2fr) auto 4rem 3rem 1.5rem;
	}
	.title {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.mono {
		font-family: var(--font-data);
	}
	.keys {
		margin-top: var(--s-4);
		font-size: var(--t--1);
	}
</style>

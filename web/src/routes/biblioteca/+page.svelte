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
	<header class="ctl-page-head">
		<h1>{t.library.title}</h1>
		<span class="ctl-sub">{t.library.count(live.state.contents.length)}</span>
		<div class="ctl-actions">
			<button
				class="ctl-btn"
				onclick={() => addToPlaylist(selection.targets)}
				disabled={!selection.targets.length}>{t.cmd.addToPlaylist} <Kbd keys="a" /></button
			>
			<a class="ctl-btn ctl-primary" href={resolve('/crear')}>{t.library.new}</a>
		</div>
	</header>
	<section class="ctl-panel">
		<div class="ctl-toolbar">
			<input
				class="ctl-input"
				type="search"
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
			<span class="ctl-end"
				>{#if selection.marked.size}{t.library.marked(selection.marked.size)}{/if}</span
			>
		</div>
		{#if songs.length === 0}
			<p class="ctl-empty">{query ? t.library.noMatch : t.library.empty}</p>
		{:else}
			<table class="ctl-table" aria-label={t.library.title}>
				<thead>
					<tr>
						<th>{t.library.columns.title}</th>
						<th>{t.library.columns.artist}</th>
						<th>{t.library.columns.language}</th>
						<th class="ctl-num">{t.library.columns.duration}</th>
						<th class="ctl-num">{t.library.columns.version}</th>
						<th>{t.library.columns.inList}</th>
					</tr>
				</thead>
				<tbody>
					{#each songs as song, i (song.id)}
						<tr
							id={`song-${song.id}`}
							class:ctl-cursor={i === selection.cursor}
							class:ctl-marked={selection.marked.has(song.id)}
							aria-selected={i === selection.cursor}
							onclick={() => (selection.cursor = i)}
							ondblclick={() => addToPlaylist([song.id])}
						>
							<td class="ctl-title">{song.title}</td>
							<td class="ctl-muted">{song.artist ?? ''}</td>
							<td class="lang">{song.language}</td>
							<td class="ctl-num">{clock(song.duration)}</td>
							<td class="ctl-num ctl-muted">{song.version}</td>
							<td
								>{#if inList.has(song.id)}<span class="ctl-badge ctl-active">{t.library.yes}</span
									>{/if}</td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
	<p class="ctl-hint">
		<Kbd keys="a" />
		{t.cmd.addToPlaylist} · <Kbd keys="Shift+a" />
		{t.cmd.addNext} · <Kbd keys="x" />
		{t.cmd.toggleSelect} · <Kbd keys="e" />
		{t.cmd.edit} · <Kbd keys="m" />
		{t.cmd.export} · <Kbd keys="Delete" />
		{t.cmd.trash}
	</p>
</div>

<style>
	.lang {
		text-transform: uppercase;
		font-family: var(--font-mono);
		font-size: var(--fs-s);
		color: var(--text-2);
	}
</style>

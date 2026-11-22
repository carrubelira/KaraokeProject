<script lang="ts">
	/**
	 * The command palette (Mod+K): fuzzy search over every command and every song and node, with each command's shortcut shown so it is learnt.
	 */
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { rank } from '#lib/commands/fuzzy.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { addToQueue } from './actions.svelte';
	import Kbd from './Kbd.svelte';

	interface Entry {
		id: string;
		title: string;
		detail: string;
		keys?: string[];
		run: () => unknown;
	}

	let query = $state('');
	let index = $state(0);
	let input: HTMLInputElement | undefined = $state();
	const t = $derived(i18n.t);

	const entries = $derived.by<Entry[]>(() => {
		const list: Entry[] = commands.commands
			.filter((c) => !c.hidden && commands.isActive(c))
			.map((c) => ({
				id: c.id,
				title: c.title(),
				detail: c.group(),
				keys: commands.keysOf(c),
				run: () => commands.run(c)
			}));
		for (const c of live.state.contents) {
			list.push({
				id: `song:${c.id}`,
				title: `${c.title}${c.artist ? ` · ${c.artist}` : ''}`,
				detail: `${t.palette.song} · ${t.cmd.addToQueue}`,
				run: () => addToQueue([c.id])
			});
		}
		for (const n of live.state.nodes) {
			list.push({
				id: `node:${n.id}`,
				title: n.name,
				detail: n.kind === 'worker' ? t.palette.worker : t.palette.player,
				run: () => goto(resolve('/equipos'))
			});
		}
		return list;
	});
	const results = $derived(rank(query, entries, (e) => `${e.title} ${e.detail}`, 40));

	$effect(() => {
		if (commands.paletteOpen) {
			query = '';
			index = 0;
			queueMicrotask(() => input?.focus());
		}
	});

	function choose(entry: Entry | undefined) {
		if (!entry) return;
		commands.paletteOpen = false;
		void entry.run();
	}

	function keydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown' || (event.ctrlKey && event.key === 'n')) {
			index = Math.min(index + 1, results.length - 1);
			event.preventDefault();
		} else if (event.key === 'ArrowUp' || (event.ctrlKey && event.key === 'p')) {
			index = Math.max(index - 1, 0);
			event.preventDefault();
		} else if (event.key === 'Enter') {
			choose(results[index]);
			event.preventDefault();
		} else if (event.key === 'Escape') {
			commands.paletteOpen = false;
			event.preventDefault();
			event.stopPropagation();
		}
	}
</script>

{#if commands.paletteOpen}
	<div class="backdrop" role="presentation" onclick={() => (commands.paletteOpen = false)}></div>
	<div class="dialog palette" role="dialog" aria-modal="true" aria-label={t.palette.label}>
		<input
			bind:this={input}
			bind:value={query}
			oninput={() => (index = 0)}
			onkeydown={keydown}
			placeholder={t.palette.placeholder}
			role="combobox"
			aria-expanded="true"
			aria-controls="palette-results"
			aria-activedescendant={results[index] ? `palette-${index}` : undefined}
		/>
		<ul id="palette-results" role="listbox">
			{#each results as entry, i (entry.id)}
				<li
					id={`palette-${i}`}
					role="option"
					aria-selected={i === index}
					class:active={i === index}
					onmousemove={() => (index = i)}
					onclick={() => choose(entry)}
					onkeydown={() => {}}
				>
					<span class="title">{entry.title}</span>
					<span class="detail">{entry.detail}</span>
					<Kbd keys={entry.keys} />
				</li>
			{:else}
				<li class="empty">{t.palette.empty}</li>
			{/each}
		</ul>
		<p class="hint">{t.palette.hint}</p>
	</div>
{/if}

<style>
	.palette {
		overflow: hidden;
	}
	input {
		width: 100%;
		height: 48px;
		padding: 0 16px;
		border: 0;
		border-bottom: 1px solid var(--border);
		background: transparent;
		font-size: 15px;
		outline: none;
	}
	ul {
		max-height: 55vh;
		overflow-y: auto;
		margin: 0;
		padding: 6px;
		list-style: none;
	}
	li {
		display: grid;
		grid-template-columns: 1fr auto auto;
		gap: 12px;
		align-items: center;
		padding: 7px 10px;
		border-radius: 4px;
		cursor: pointer;
	}
	li.active {
		background: var(--accent-soft);
	}
	.detail {
		color: var(--muted);
		font-size: 12.5px;
	}
	.empty {
		color: var(--muted);
		cursor: default;
	}
	.hint {
		padding: 8px 16px;
		border-top: 1px solid var(--border);
		color: var(--faint);
		font-size: 12px;
	}
</style>

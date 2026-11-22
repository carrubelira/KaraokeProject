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
				run: () => goto(resolve('/nodos'))
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
	<div class="palette" role="dialog" aria-modal="true" aria-label={t.palette.label}>
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
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 70;
		background: rgb(2 3 5 / 0.6);
		backdrop-filter: blur(3px);
	}
	.palette {
		position: fixed;
		z-index: 71;
		top: 12vh;
		left: 50%;
		transform: translateX(-50%);
		width: min(44rem, calc(100vw - 2rem));
		background: var(--panel-solid);
		border: 1px solid var(--line-strong);
		border-top: 2px solid var(--info);
		border-radius: var(--radius);
		box-shadow: 0 30px 80px -20px rgb(0 0 0 / 0.9);
		overflow: hidden;
	}
	input {
		width: 100%;
		padding: 16px 18px;
		border: 0;
		border-bottom: 1px solid var(--line);
		background: transparent;
		color: var(--text);
		font: 500 17px var(--font-text);
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
		padding: 8px 12px;
		border-radius: 2px;
		cursor: pointer;
	}
	li.active {
		background: rgb(60 200 255 / 0.1);
		box-shadow: inset 2px 0 0 var(--info);
	}
	.detail {
		color: var(--dim);
		font: 500 10.5px var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}
	.empty {
		color: var(--dim);
		cursor: default;
	}
	.hint {
		margin: 0;
		padding: 8px 18px;
		border-top: 1px solid var(--line);
		color: var(--faint);
		font: 500 10.5px var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}
</style>

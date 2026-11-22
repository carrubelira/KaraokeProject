<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	/** Every shortcut that works here, grouped (?). */
	import { commands } from '#lib/commands/registry.svelte.js';
	import { i18n } from '#lib/i18n';
	import Kbd from './Kbd.svelte';

	const groups = $derived.by(() => {
		const map = new SvelteMap<string, { title: string; keys: string[] }[]>();
		for (const command of commands.commands) {
			const keys = commands.keysOf(command);
			if (!keys.length || !commands.isActive(command)) continue;
			const group = command.group();
			map.set(group, [...(map.get(group) ?? []), { title: command.title(), keys }]);
		}
		return [...map];
	});
</script>

<svelte:window
	onkeydown={(e) =>
		commands.cheatsheetOpen && e.key === 'Escape' && (commands.cheatsheetOpen = false)}
/>

{#if commands.cheatsheetOpen}
	<div class="backdrop" role="presentation" onclick={() => (commands.cheatsheetOpen = false)}></div>
	<div class="sheet" role="dialog" aria-modal="true" aria-label={i18n.t.cheatsheet.title}>
		<header>
			<h2>{i18n.t.cheatsheet.title}</h2>
			<p>{i18n.t.cheatsheet.rebind}</p>
		</header>
		<div class="grid">
			{#each groups as [group, list] (group)}
				<div>
					<h3>{group}</h3>
					<dl>
						{#each list as item (item.title)}
							<dt>{item.title}</dt>
							<dd>
								{#each item.keys as key (key)}<Kbd keys={key} />{/each}
							</dd>
						{/each}
					</dl>
				</div>
			{/each}
		</div>
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
	.sheet {
		position: fixed;
		z-index: 71;
		inset: 6vh 50% auto auto;
		transform: translateX(50%);
		width: min(64rem, calc(100vw - 2rem));
		max-height: 86vh;
		overflow: auto;
		padding: 22px 26px;
		background: var(--panel-solid);
		border: 1px solid var(--line-strong);
		border-radius: var(--radius);
	}
	h2 {
		margin: 0;
		font: 600 18px var(--font-display);
		text-transform: uppercase;
	}
	header p {
		color: var(--dim);
		margin: 4px 0 0;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
		gap: 22px;
		margin-top: 18px;
	}
	h3 {
		font: 500 11px var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.14em;
		color: var(--info);
		margin: 0 0 10px;
	}
	dl {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 6px 12px;
		margin: 0;
		font-size: 13.5px;
	}
	dt {
		color: var(--text);
	}
	dd {
		margin: 0;
		display: flex;
		gap: 4px;
		justify-content: end;
	}
</style>

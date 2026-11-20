<script lang="ts">
	/**
	 * Side-by-side panels with draggable splitters (also by keyboard: focus a splitter and use the
	 * arrows). Sizes are fractions, kept per layout in the operator's preferences.
	 */
	import type { Snippet } from 'svelte';
	import { prefs } from './prefs.svelte';

	interface Props {
		name: string;
		panels: Snippet[];
		initial: number[];
		min?: number;
	}
	let { name, panels, initial, min = 0.15 }: Props = $props();
	const key = $derived(`${name}:${prefs.value.layout}`);
	const sizes = $derived(
		prefs.value.sizes[key]?.length === panels.length ? prefs.value.sizes[key] : initial
	);
	let box: HTMLDivElement | undefined = $state();

	function resize(index: number, delta: number) {
		const next = sizes.slice();
		const moved = Math.max(min - next[index], Math.min(delta, next[index + 1] - min));
		next[index] += moved;
		next[index + 1] -= moved;
		prefs.set('sizes', { ...prefs.value.sizes, [key]: next });
	}

	function drag(index: number, event: PointerEvent) {
		const target = event.currentTarget as HTMLElement;
		target.setPointerCapture(event.pointerId);
		let last = event.clientX;
		const width = box?.clientWidth ?? 1;
		const move = (e: PointerEvent) => {
			resize(index, (e.clientX - last) / width);
			last = e.clientX;
		};
		const up = () => {
			target.removeEventListener('pointermove', move);
			target.removeEventListener('pointerup', up);
		};
		target.addEventListener('pointermove', move);
		target.addEventListener('pointerup', up);
	}

	function key_(index: number, event: KeyboardEvent) {
		if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
			resize(index, event.key === 'ArrowLeft' ? -0.03 : 0.03);
			event.preventDefault();
			event.stopPropagation();
		}
	}
</script>

<div
	class="panels"
	bind:this={box}
	style:grid-template-columns={sizes.map((s) => `minmax(0, ${s}fr)`).join(' 6px ')}
>
	{#each panels as panel, i (i)}
		<section class="panel-slot">{@render panel()}</section>
		{#if i < panels.length - 1}
			<!-- A window splitter: a focusable separator the arrows move (WAI-ARIA). -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
			<div
				class="splitter"
				role="separator"
				aria-orientation="vertical"
				aria-valuenow={Math.round(sizes[i] * 100)}
				tabindex="0"
				onpointerdown={(e) => drag(i, e)}
				onkeydown={(e) => key_(i, e)}
			></div>
		{/if}
	{/each}
</div>

<style>
	.panels {
		display: grid;
		height: calc(100vh - 3.2rem - 2.4rem);
		padding: var(--s-3);
		gap: 0;
	}
	.panel-slot {
		min-height: 0;
		overflow: auto;
	}
	.splitter {
		cursor: col-resize;
		border-radius: 3px;
	}
	.splitter:hover,
	.splitter:focus-visible {
		background: var(--ceo);
		outline: none;
	}
	@media (max-width: 60em) {
		.panels {
			grid-template-columns: 1fr !important;
			height: auto;
		}
		.splitter {
			display: none;
		}
	}
</style>

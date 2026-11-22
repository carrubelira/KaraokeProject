<script lang="ts">
	/**
	 * A task's log: the lines its process writes, live, while it runs; its whole log (a blob the
	 * worker uploaded) once it has ended. It follows the end unless the operator scrolls up.
	 */
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import type { Job, TaskView } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';

	let { job, task }: { job: Job; task: TaskView } = $props();
	let fetched = $state<string[] | null>(null);
	let box: HTMLPreElement | undefined = $state();
	let follow = $state(true);

	const key = $derived(task.id.split(':')[1]);
	const running = $derived(task.state === 'running' || task.state === 'leased');

	$effect(() => {
		// The whole log once it exists, or the lines the server kept for a task already running.
		void task.log;
		void running;
		let current = true;
		api
			.taskLog(job.id, key)
			.then((text) => {
				if (current) fetched = text ? text.split('\n') : [];
			})
			.catch(() => {
				if (current) fetched = [];
			});
		return () => {
			current = false;
		};
	});

	const lines = $derived.by(() => {
		const streamed = live.state.logs[task.id] ?? [];
		if (task.log || !running) return fetched ?? [];
		// While it runs: what was there when the view opened, then what streams in.
		const before = fetched ?? [];
		const tail = before.at(-1);
		const from = tail === undefined ? 0 : streamed.lastIndexOf(tail) + 1;
		return [...before, ...streamed.slice(from)];
	});

	$effect(() => {
		void lines.length;
		if (follow && box) box.scrollTop = box.scrollHeight;
	});
</script>

<pre
	class="log"
	bind:this={box}
	onscroll={() => box && (follow = box.scrollHeight - box.scrollTop - box.clientHeight < 24)}
	aria-label={i18n.t.jobs.log}>{#if lines.length}{#each lines as line, i (i)}<span
				class="line"
				class:stage={line.startsWith('──')}
				class:error={line.startsWith('✖') || /error|traceback/i.test(line)}>{line}</span
			>{/each}{:else}<span class="faint">{i18n.t.jobs.logEmpty}</span>{/if}</pre>

<style>
	.log {
		margin: 0;
		max-height: 320px;
		overflow: auto;
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--bg);
		color: var(--muted);
		font: 12px/1.55 var(--mono);
	}
	.line {
		display: block;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.stage {
		margin-top: 4px;
		color: var(--text);
	}
	.error {
		color: var(--error);
	}
</style>

<script lang="ts">
	import { api, ApiError } from '#lib/control/api.js';
	import type { Session } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';

	let { onsession }: { onsession: (session: Session) => void } = $props();
	let token = $state('');
	let error = $state<string | null>(null);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		try {
			onsession(await api.signIn(token.trim()));
		} catch (e) {
			error = e instanceof ApiError && e.status === 401 ? i18n.t.app.badToken : String(e);
		}
	}
</script>

<main class="login">
	<form onsubmit={submit} class="panel">
		<h1>{i18n.t.app.signInTitle}</h1>
		<label>
			{i18n.t.app.tokenLabel}
			<!-- svelte-ignore a11y_autofocus -->
			<input
				type="password"
				bind:value={token}
				autocomplete="current-password"
				autofocus
				required
			/>
		</label>
		<p class="hint">{i18n.t.app.tokenHint}</p>
		{#if error}<p class="error" role="alert">{error}</p>{/if}
		<button type="submit">{i18n.t.app.signIn}</button>
	</form>
</main>

<style>
	.login {
		display: grid;
		place-items: center;
		min-height: 100vh;
	}
	form {
		display: grid;
		gap: var(--s-3);
		width: min(26rem, calc(100vw - 2rem));
		padding: var(--s-6);
	}
	input {
		width: 100%;
		margin-top: var(--s-2);
		padding: var(--s-3);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-control);
		background: var(--fondo);
		color: var(--texto);
		font: inherit;
	}
	.hint {
		color: var(--texto-3);
		font-size: var(--t--1);
	}
	.error {
		color: var(--erro);
	}
	button {
		padding: var(--s-3);
		border: 0;
		border-radius: var(--radius-pill);
		background: var(--accion);
		color: var(--accion-texto);
		font: inherit;
		font-weight: 700;
		cursor: pointer;
	}
</style>

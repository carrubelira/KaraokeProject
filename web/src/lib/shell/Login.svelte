<script lang="ts">
	import { api, ApiError } from '#lib/control/api.js';
	import type { OperatorSession } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import Coast from '#lib/ui/Coast.svelte';

	let { onsession }: { onsession: (session: OperatorSession) => void } = $props();
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
	<Coast class="login-coast" />
	<form onsubmit={submit} class="panel">
		<div class="panel-body body">
			<div>
				<h1>{i18n.t.app.signInTitle}</h1>
				<p class="muted">{i18n.t.app.signInLead}</p>
			</div>
			<label class="form-row">
				<span>{i18n.t.app.tokenLabel}</span>
				<!-- svelte-ignore a11y_autofocus -->
				<input
					class="field mono"
					type="password"
					bind:value={token}
					autocomplete="current-password"
					autofocus
					required
				/>
			</label>
			<p class="muted small">{i18n.t.app.tokenHint}</p>
			{#if error}<p class="notice error" role="alert">{error}</p>{/if}
			<button class="btn primary large" type="submit">{i18n.t.app.signIn}</button>
		</div>
	</form>
</main>

<style>
	.login {
		position: relative;
		display: grid;
		place-items: center;
		min-height: 100vh;
		padding: 16px;
		overflow: hidden;
	}
	.login :global(.login-coast) {
		position: absolute;
		right: 6vw;
		top: 50%;
		height: 80vh;
		transform: translateY(-50%);
		color: var(--accent);
		opacity: 0.1;
	}
	form {
		position: relative;
		width: min(26rem, 100%);
	}
	.body {
		display: grid;
		gap: 16px;
		padding: 24px;
	}
</style>

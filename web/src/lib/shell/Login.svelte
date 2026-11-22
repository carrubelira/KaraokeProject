<script lang="ts">
	import { api, ApiError } from '#lib/control/api.js';
	import type { Session } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import Coast from './Coast.svelte';

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
	<div class="coast"><Coast opacity={0.08} /></div>
	<form onsubmit={submit} class="ctl-panel">
		<div class="ctl-panel-head"><h1>{i18n.t.app.signInTitle}</h1></div>
		<div class="ctl-panel-body ctl-form">
			<label class="ctl-field">
				<span>{i18n.t.app.tokenLabel}</span>
				<!-- svelte-ignore a11y_autofocus -->
				<input
					class="ctl-input"
					type="password"
					bind:value={token}
					autocomplete="current-password"
					autofocus
					required
				/>
				<span class="ctl-help">{i18n.t.app.tokenHint} <code>{i18n.t.app.tokenCommand}</code></span>
			</label>
			{#if error}<p class="error" role="alert">{error}</p>{/if}
			<button class="ctl-btn ctl-primary" type="submit">{i18n.t.app.signIn}</button>
		</div>
	</form>
</main>

<style>
	.login {
		position: relative;
		display: grid;
		place-items: center;
		min-height: 100dvh;
		overflow: hidden;
	}
	.coast {
		position: absolute;
		inset: 8vh auto 8vh 50%;
		width: 84vh;
		transform: translateX(-50%);
	}
	form {
		position: relative;
		width: min(26rem, calc(100vw - 2rem));
	}
	h1 {
		font-size: var(--fs-l);
	}
	.error {
		color: #f1a5a3;
	}
	button {
		justify-content: center;
	}
	code {
		font-family: var(--font-mono);
		color: var(--text-2);
	}
</style>

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
	<form onsubmit={submit} class="c-panel">
		<div class="c-panel-head">
			<span class="c-tally warn">{i18n.t.strip.standby}</span>
		</div>
		<div class="c-panel-body body">
			<h1>{i18n.t.app.signInTitle}</h1>
			<label class="c-labelled">
				<span class="label">{i18n.t.app.tokenLabel}</span>
				<!-- svelte-ignore a11y_autofocus -->
				<input
					class="c-field mono"
					type="password"
					bind:value={token}
					autocomplete="current-password"
					autofocus
					required
				/>
			</label>
			<p class="dim hint">{i18n.t.app.tokenHint}</p>
			{#if error}<p class="error" role="alert">{error}</p>{/if}
			<button class="c-btn primary big" type="submit">{i18n.t.app.signIn}</button>
		</div>
	</form>
</main>

<style>
	.login {
		position: relative;
		z-index: 1;
		display: grid;
		place-items: center;
		min-height: 100vh;
		padding: 16px;
	}
	form {
		width: min(28rem, 100%);
	}
	.body {
		display: grid;
		gap: 16px;
		padding: 24px;
	}
	h1 {
		margin: 0;
		font: 600 22px/1.1 var(--font-display);
		text-transform: uppercase;
	}
	.hint {
		margin: 0;
		font-size: 13px;
	}
	.error {
		margin: 0;
		color: var(--onair);
	}
</style>

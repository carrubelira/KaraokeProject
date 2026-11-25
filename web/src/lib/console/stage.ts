/** What the stage has on, from the live state, and the colour each state is shown in. */
import type { QueueItem } from '#lib/contracts';
import type { LiveState } from '#lib/control/state.js';
import type { Content, ScreenView } from '#lib/control/types.js';

export type Tone = 'ok' | 'warn' | 'info' | 'error' | 'plain';

export interface OnStage {
	item: QueueItem | null;
	song: Content | null;
	next: { item: QueueItem; song: Content | null } | null;
}

export function onStage(state: LiveState): OnStage {
	const song = (id: string | undefined) => state.contents.find((c) => c.id === id) ?? null;
	const item = state.session.current?.item ?? null;
	const following = state.session.upcoming[0]?.item ?? (item ? null : state.queue.items[0]);
	return {
		item,
		song: song(item?.content_id),
		next: following ? { item: following, song: song(following.content_id) } : null
	};
}

/** Green playing, blue getting ready, amber paused or waiting for the operator, red at fault. */
export function sessionTone(state: LiveState): Tone {
	if (state.audio.required && !state.audio.online) return 'error';
	switch (state.session.state) {
		case 'playing':
			return 'ok';
		case 'cueing':
			return 'info';
		case 'cued':
		case 'paused':
			return 'warn';
		case 'fault':
			return 'error';
		default:
			return 'plain';
	}
}

export function screenTone(screen: ScreenView): Tone {
	const status = screen.status;
	if (!screen.online || !status) return 'plain';
	if (status.state === 'error') return 'error';
	if (status.flags.includes('degraded') || status.flags.includes('hidden')) return 'warn';
	if (status.state === 'playing' || status.ready) return 'ok';
	return 'info';
}

/** The name a screen is shown by: the operator's, else its id. */
export const screenName = (screen: ScreenView): string => screen.config.name ?? screen.id;

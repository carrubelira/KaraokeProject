/** What a screen is playing: its queue item, the song, and what comes after, from the live state. */
import type { QueueItem } from '#lib/contracts';
import type { LiveState } from '#lib/control/state.js';
import type { Content, PlayerView } from '#lib/control/types.js';

export type Tone = 'ok' | 'warn' | 'info' | 'error' | 'plain';

export interface OnScreen {
	item: QueueItem | null;
	song: Content | null;
	next: { item: QueueItem; song: Content | null } | null;
}

/** The colour a screen's state is shown in: green playing, amber paused or with alerts. */
export function toneOf(player: PlayerView | undefined): Tone {
	if (!player?.online) return 'plain';
	if ((player.status.errors ?? []).length) return 'warn';
	switch (player.status.state) {
		case 'playing':
			return 'ok';
		case 'loading':
		case 'waiting':
			return 'info';
		case 'paused':
			return 'warn';
		default:
			return 'plain';
	}
}

export function onScreen(state: LiveState, player: PlayerView | undefined): OnScreen {
	const queue = state.queues.find((q) => q.player_id === player?.id);
	const items = queue?.items ?? [];
	const itemId = player?.status.item_id ?? player?.item_id ?? null;
	const index = items.findIndex((i) => i.id === itemId);
	const item = index >= 0 ? items[index] : null;
	const song = (id: string | undefined) => state.contents.find((c) => c.id === id) ?? null;
	const following = index >= 0 ? items[index + 1] : items[0];
	return {
		item,
		song: song(item?.content_id),
		next: following ? { item: following, song: song(following.content_id) } : null
	};
}

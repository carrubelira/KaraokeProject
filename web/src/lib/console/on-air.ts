/** What is on air on a screen: its queue item, the song, and its tally, from the live state. */
import type { QueueItem } from '#lib/contracts';
import type { LiveState } from '#lib/control/state.js';
import type { Content, PlayerView } from '#lib/control/types.js';

export type Tally = 'onair' | 'cue' | 'warn' | 'info' | 'off';

export interface OnAir {
	item: QueueItem | null;
	song: Content | null;
	next: { item: QueueItem; song: Content | null } | null;
	tally: Tally;
}

export function tallyOf(player: PlayerView | undefined): Tally {
	if (!player?.online) return 'off';
	if ((player.status.errors ?? []).length) return 'warn';
	switch (player.status.state) {
		case 'playing':
			return 'onair';
		case 'loading':
		case 'waiting':
			return 'info';
		case 'paused':
			return 'cue';
		default:
			return 'off';
	}
}

export function onAir(state: LiveState, player: PlayerView | undefined): OnAir {
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
		next: following ? { item: following, song: song(following.content_id) } : null,
		tally: tallyOf(player)
	};
}

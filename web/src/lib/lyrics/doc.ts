/** A song's v2 tracks as the document the lyrics component and the editor work on. */
import type { KaraokeDoc, Lyrics, Manifest } from '#lib/contracts';
import { normalizeDoc } from './layout';

export function docFromTracks(manifest: Manifest, lyrics: Lyrics): KaraokeDoc {
	const audio = manifest.tracks.find((track) => track.kind === 'instrumental')?.audio;
	return normalizeDoc({
		schema_version: '1.3.0',
		id: manifest.content_id,
		title: manifest.title,
		artist: manifest.artist ?? null,
		language: manifest.language,
		duration: manifest.duration,
		audio: {
			instrumental: 'instrumental.opus',
			vocals: 'vocals.opus',
			loudness_lufs: audio?.loudness_lufs ?? null,
			gain_db: audio?.gain_db ?? null
		},
		video: null,
		cover: null,
		singers: lyrics.singers,
		lines: lyrics.lines,
		provenance: lyrics.provenance,
		edited: lyrics.edited
	});
}

/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

export interface Manifest {
	schema_version: string;
	content_id: string;
	version: number;
	/**
	 * Hash of the previous version.
	 */
	parent: string | null;
	created_at: string;
	title: string;
	artist: string | null;
	language: string;
	duration: number;
	/**
	 * @minItems 1
	 */
	tracks: Track[];
}
export interface Track {
	kind: 'vocals' | 'instrumental' | 'video' | 'lyrics' | 'cover';
	blob: Blob;
	/**
	 * Song time of the track's first sample.
	 */
	offset: number;
	duration: number | null;
	audio: AudioInfo | null;
	video: VideoInfo | null;
}
export interface Blob {
	sha256: string;
	size: number;
	media_type: string;
}
export interface AudioInfo {
	codec: 'opus';
	container: 'ogg';
	sample_rate: 48000;
	channels: number;
	/**
	 * Opus pre-skip, in 48 kHz samples.
	 */
	preskip: number;
	/**
	 * Gain the player applies to bring the song to -14 LUFS without clipping; the same for every audio track, so guide vocals and music keep their balance.
	 */
	gain_db: number;
	/**
	 * Integrated loudness of the mix once `gain_db` is applied.
	 */
	loudness_lufs: number | null;
}
export interface VideoInfo {
	codec: 'h264' | 'hevc' | 'av1';
	width: number;
	height: number;
	fps: number;
}

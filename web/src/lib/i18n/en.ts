import type { Messages } from './gl';
import { plural } from './plural';

export const en: Messages = {
	app: {
		name: 'Karaoke',
		signIn: 'Sign in',
		signInTitle: 'Karaoke en Galego',
		signInLead: 'Control panel',
		tokenLabel: 'Operator token',
		tokenHint: 'Create one on the server with `karaoke-server operator add "your name"`.',
		badToken: 'That token does not belong to an operator.',
		signOut: 'Sign out',
		reconnecting: 'Lost the connection to the server. Reconnecting…',
		dropHere: 'Drop the file to add the song',
		pasted: 'Link pasted: analysing the song',
		failed: (what: string) => `Could not complete: ${what}`,
		undone: (what: string) => `Undone: ${what}`,
		redone: (what: string) => `Redone: ${what}`,
		nothingToUndo: 'Nothing to undo'
	},
	nav: {
		label: 'Main menu',
		playback: 'Playback',
		library: 'Library',
		add: 'Add song',
		jobs: 'Processing',
		devices: 'Devices',
		outputs: 'Outputs',
		settings: 'Settings'
	},
	groups: {
		navigation: 'Go to',
		playback: 'Playback',
		queue: 'Queue',
		jobs: 'Processing',
		library: 'Library',
		general: 'General',
		outputs: 'Outputs',
		devices: 'Devices'
	},
	cmd: {
		palette: 'Search commands',
		cheatsheet: 'Keyboard shortcuts',
		undo: 'Undo',
		redo: 'Redo',
		toggle: 'Play or pause',
		start: 'Start',
		play: 'Play',
		pause: 'Pause',
		next: 'Next song',
		previous: 'Previous song',
		back: 'Back 5 s',
		forward: 'Forward 5 s',
		restart: 'From the start',
		volumeUp: 'Volume up',
		volumeDown: 'Volume down',
		pitchUp: 'Key up',
		pitchDown: 'Key down',
		pitchReset: 'Original key',
		stop: 'Stop',
		search: 'Search',
		add: 'Add a song',
		down: 'Down',
		up: 'Up',
		toggleSelect: 'Mark',
		selectDown: 'Extend selection down',
		selectUp: 'Extend selection up',
		selectAll: 'Mark all',
		addToQueue: 'Add to queue',
		addNext: 'Play next',
		remove: 'Remove from queue',
		moveUp: 'Move up',
		moveDown: 'Move down',
		cue: 'Cue',
		playNow: 'Play now',
		retry: 'Retry',
		retryElsewhere: 'Retry on another computer',
		cancel: 'Cancel',
		pauseJob: 'Pause',
		resumeJob: 'Resume',
		retryFailed: 'Retry the failed ones',
		export: 'Export video',
		edit: 'Fix the lyrics',
		trash: 'Move to trash',
		enrolWorker: 'Add a processing computer'
	},
	palette: {
		label: 'Search commands',
		placeholder: 'Type a command, a song or a device',
		empty: 'No results',
		song: 'Song',
		worker: 'Processing computer',
		hint: '↑ ↓ to move · Enter to choose · Esc to close'
	},
	cheatsheet: {
		title: 'Keyboard shortcuts',
		rebind: 'They can be changed in Settings.'
	},
	server: {
		connected: 'Server connected',
		reconnecting: 'Reconnecting…'
	},
	screen: {
		connecting: 'Connecting to the server…',
		nothing: 'No song is cued yet',
		upNow: 'Now singing',
		next: 'Next',
		downloading: 'Downloading the song',
		preparing: 'Getting ready…',
		ready: 'Ready to start',
		paused: 'Paused',
		offline: 'No connection to the server',
		fullscreen: 'Full screen',
		error: 'This screen cannot show the song',
		reload: 'Reload'
	},
	player: {
		nothing: 'Nothing is playing',
		states: {
			idle: 'Stopped',
			cueing: 'Getting ready',
			cued: 'Ready to start',
			playing: 'Playing',
			paused: 'Paused',
			ended: 'Ended',
			fault: 'No sound'
		},
		audioDown: 'No audio engine',
		screensReady: (ready: number, total: number) => `${ready}/${total} screens ready`,
		next: 'Next',
		key: 'Key',
		semitones: (n: number) => `${n > 0 ? '+' : ''}${n}`,
		volume: 'Volume'
	},
	playback: {
		title: 'Playback',
		description: 'What is on now, the screens and the queue.',
		queue: 'Queue',
		queueEmpty: 'The queue is empty. Search for a song above or add it from the Library.',
		addPlaceholder: 'Search for a song to add it to the queue',
		number: 'No.',
		song: 'Song',
		singer: 'Singer',
		duration: 'Length',
		status: 'Status',
		played: 'Played',
		onNow: 'Playing',
		dragHint: 'Drag the rows to change the order',
		noScreens: 'No screen is open. Open /pantalla in a browser on the network.',
		onScreens: (ready: number, total: number) => `${ready}/${total} screens`,
		alerts: 'Sound alerts',
		lyrics: 'Lyrics',
		cache: {
			absent: 'Not downloaded',
			downloading: 'Downloading',
			verifying: 'Checking',
			ready: 'Ready',
			failed: 'Download failed'
		}
	},
	add: {
		title: 'Add song',
		lead: 'Paste the song’s link. The program identifies it and finds its lyrics; then you review the details before the karaoke is made.',
		link: 'Link',
		placeholder: 'https://www.youtube.com/watch?v=…',
		analyse: 'Analyse',
		orFile: 'You can also upload an audio or video file.',
		chooseFile: 'Upload file',
		uploading: (name: string, pct: number) => `Uploading ${name} (${pct} %)`,
		autoConfirm: 'Make the karaoke without review when the identification is sure',
		inProgress: 'Being analysed',
		toReview: 'Waiting for review',
		nothing: 'No song is being analysed.',
		steps: {
			download: 'Download',
			metadata: 'Page details',
			fingerprint: 'Sound fingerprint',
			acoustid: 'AcoustID',
			musicbrainz: 'MusicBrainz',
			lyrics: 'Lyrics'
		},
		sources: {
			youtube: 'YouTube Music',
			title: 'Video title',
			tags: 'File tags',
			acoustid: 'Sound fingerprint',
			operator: 'Typed by you'
		},
		confidence: (pct: number) => `${pct} %`,
		fingerprint: {
			ok: 'Identified by its sound fingerprint.',
			no_match: 'The sound fingerprint matches no known recording.',
			no_key: 'No AcoustID key: the song was not identified by its sound.',
			failed: 'The sound fingerprint could not be taken.',
			skipped: 'No sound fingerprint was taken.'
		},
		reviewTitle: 'Review the song’s details',
		reviewLead: 'Check or correct the details. The karaoke will be made with them.',
		candidates: 'Other matches',
		songTitle: 'Title',
		artist: 'Artist',
		language: 'Language of the lyrics',
		lyrics: 'Lyrics',
		lyricsFound: (n: number) => plural(n, 'en', { one: '# lyrics found', other: '# lyrics found' }),
		lyricsNone: 'No lyrics (transcribe the audio)',
		lyricsOwn: 'Paste the lyrics by hand',
		lyricsSearch: 'Search',
		synced: 'Timed',
		gap: (s: string) => `${s} s apart`,
		show: 'View',
		process: 'Make the karaoke',
		processToQueue: 'Make it and queue it',
		discard: 'Discard',
		queued: (title: string) => `Making the karaoke of “${title}”`
	},
	jobs: {
		title: 'Processing',
		description: 'Every song goes through download, analysis and making the karaoke.',
		empty: 'Nothing is being processed.',
		filters: {
			all: 'All',
			active: 'In progress',
			review: 'To review',
			failed: 'Failed',
			done: 'Finished'
		},
		song: 'Song',
		status: 'Status',
		step: 'Current step',
		device: 'Computer',
		time: 'Time',
		states: {
			active: 'In progress',
			review: 'Waiting for review',
			paused: 'Paused',
			done: 'Finished',
			failed: 'Failed',
			cancelled: 'Cancelled'
		},
		tasks: {
			waiting: 'Waiting',
			held: 'Waiting for your review',
			ready: 'Queued',
			leased: 'Starting',
			running: 'In progress',
			done: 'Done',
			failed: 'Failed',
			cancelled: 'Cancelled',
			paused: 'Paused'
		},
		kinds: {
			fetch: 'Download',
			analyze: 'Analysis',
			make: 'Making the karaoke',
			package: 'Packaging',
			render: 'MP4 video'
		},
		stages: {
			download: 'Downloading',
			analyze: 'Analysing',
			decode: 'Reading the audio',
			separate: 'Separating the voice',
			transcribe: 'Transcribing',
			align: 'Syncing the lyrics',
			encode: 'Encoding',
			render: 'Rendering the video',
			upload: 'Saving'
		},
		eta: (time: string) => `${time} left`,
		on: (worker: string) => worker,
		attempt: (n: number) => `attempt ${n}`,
		steps: 'Steps',
		log: 'Log',
		showLog: 'Show log',
		hideLog: 'Hide log',
		logEmpty: 'The log is empty.',
		review: 'Review',
		openSong: 'Open in the library'
	},
	errors: {
		too_big: { title: 'The file is too big', hint: 'Use a shorter or lower-quality version.' },
		too_long: { title: 'The song is too long', hint: 'The limit is 20 minutes.' },
		no_audio: { title: 'There is no sound', hint: 'Check that the file or video has audio.' },
		unreadable: { title: 'The sound cannot be read', hint: 'Try another file or link.' },
		bad_url: {
			title: 'The link is not valid',
			hint: 'It must be one song, not a playlist nor a live stream.'
		},
		download_failed: {
			title: 'The download failed',
			hint: 'The site may be blocking it. Retry or use another link.'
		},
		disk_full: {
			title: 'The computer’s disk is full',
			hint: 'Free some space on that computer and retry.'
		},
		bad_lyrics: {
			title: 'The lyrics do not fit',
			hint: 'Change the lyrics or let them be transcribed.'
		},
		gpu_memory: {
			title: 'Out of graphics card memory',
			hint: 'Close the programs using it, or retry on another computer.'
		},
		out_of_memory: {
			title: 'Out of memory',
			hint: 'The process went over its memory limit. Retry.'
		},
		engine_failed: {
			title: 'Making the karaoke failed',
			hint: 'Read the log; retry, or try another computer.'
		},
		interrupted: { title: 'Interrupted', hint: 'Retry.' },
		server_lost: { title: 'The computer lost the server', hint: 'Retry once the network is back.' },
		worker_lost: {
			title: 'The computer stopped answering',
			hint: 'If it does not come back, retry on another computer.'
		},
		unknown: { title: 'Error', hint: 'Read the log.' }
	},
	devices: {
		title: 'Devices',
		description: 'The computers that make the karaokes and the screens that show them.',
		workers: 'Processing computers',
		screens: 'Screens',
		emptyWorkers: 'There is no processing computer. Add one to make karaokes.',
		emptyScreens: 'No screen has been opened yet.',
		name: 'Name',
		status: 'Status',
		disconnected: 'Disconnected',
		free: 'Free',
		working: 'Processing',
		gpu: 'GPU',
		vram: 'GPU memory',
		cpu: 'CPU',
		ram: 'Memory',
		temp: (c: number) => `${Math.round(c)} °C`,
		of: (used: string, total: string) => `${used} of ${total}`,
		current: 'Current work',
		song: 'Song',
		outputs: 'Outputs',
		busyPlaying: 'Takes no work while a song plays on this computer.',
		token: 'Enrolment key (valid once for 24 h)',
		howWorker: 'Run this on the processing computer:',
		howScreen: 'Any browser on the network is a screen: open this in it (or in the kiosk).',
		sync: 'Sync',
		maxHeight: 'Largest video',
		preview: 'preview',
		forget: 'Forget',
		revoke: 'Remove',
		revoked: (name: string) => `${name} removed`,
		lastSeen: (time: string) => `seen ${time} ago`
	},
	screenStates: {
		connecting: 'Connecting',
		idle: 'No song',
		provisioning: 'Downloading',
		syncing: 'Syncing',
		waiting: 'Ready',
		playing: 'Playing',
		paused: 'Paused',
		error: 'Error'
	},
	screenFlags: {
		offline: 'No connection',
		hidden: 'The tab is hidden',
		degraded: 'The video cannot keep up',
		fullscreen: 'Full screen'
	},
	stage: {
		startAnyway: (names: string) =>
			`These screens are not ready yet: ${names}. Start anyway? They will join as soon as they can.`,
		stillCueing: 'The sound is still getting the song ready'
	},
	audioErrors: {
		output_failed: 'A sound output could not be opened',
		output_lost: 'A sound output was disconnected',
		load_failed: 'The song could not be loaded',
		master_lost: 'The main output was disconnected; playback is paused'
	},
	library: {
		title: 'Library',
		search: 'Search by title, artist or language',
		empty: 'There are no songs yet.',
		count: (n: number) => plural(n, 'en', { one: '# song', other: '# songs' }),
		songTitle: 'Title',
		artist: 'Artist',
		language: 'Language',
		duration: 'Length',
		version: 'Version',
		inQueue: 'In the queue',
		added: (title: string) => `“${title}” added to the queue`,
		exporting: (title: string) => `Exporting the video of “${title}”`,
		trashed: (n: number) =>
			plural(n, 'en', { one: '# song moved to trash', other: '# songs moved to trash' })
	},
	outputs: {
		title: 'Outputs',
		description: 'Where the stage’s sound goes: the sound cards and DACs of this computer.',
		engineOffline: 'The audio engine (kp-audio) is not running.',
		screensElsewhere: 'What each screen shows is set in',
		audio: 'Sound outputs',
		master: 'Main',
		matrix: 'Sound',
		vocals: 'Guide vocals',
		instrumental: 'Music',
		gain: 'Gain (dB)',
		delay: 'Delay (ms)',
		calibration: 'Adjustment (ms)',
		policy: 'If it disconnects',
		pause: 'Pause',
		continue: 'Carry on',
		layout: {
			'video-lyrics': 'Video and lyrics',
			lyrics: 'Lyrics only',
			video: 'Video only',
			off: 'Off'
		},
		shows: 'Shows',
		theme: 'Lyrics style',
		save: 'Save',
		saved: 'Changes saved',
		unsaved: 'There are unsaved changes',
		bluetooth: 'Bluetooth: its delay may vary'
	},
	settings: {
		title: 'Settings',
		language: 'Language',
		shortcuts: 'Keyboard shortcuts',
		press: 'Press the new shortcut…',
		change: 'Change',
		reset: 'Reset',
		conflict: 'Clashes with another shortcut',
		account: 'Session',
		server: 'Server',
		version: 'Version',
		identify: 'Song identification',
		identifyHelp:
			'The sound fingerprint uses AcoustID. Each processing computer needs a free key (acoustid.org/new-application): keep it with “karaoke-worker acoustid-key KEY”.'
	},
	editor: {
		title: 'Fix the lyrics',
		save: 'Save a new version',
		saved: 'A new version was saved',
		conflict: 'Someone changed the song meanwhile',
		play: 'Listen',
		back: 'Back'
	},
	languages: {
		gl: 'Galician',
		es: 'Spanish',
		pt: 'Portuguese',
		en: 'English',
		ca: 'Catalan',
		eu: 'Basque',
		fr: 'French',
		it: 'Italian',
		de: 'German'
	},
	common: {
		close: 'Close',
		loading: 'Loading…',
		copy: 'Copy',
		copied: 'Copied',
		more: 'More'
	}
};

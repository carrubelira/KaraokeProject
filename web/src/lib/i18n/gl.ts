import { plural } from './plural';

/** Galician: the reference dictionary. English must have exactly the same keys. */
export const gl = {
	app: {
		name: 'Consola',
		signIn: 'Entrar',
		signInTitle: 'Consola do karaoke',
		tokenLabel: 'Token de operador',
		tokenHint: 'Dácheo `karaoke-server operator add «o teu nome»` no servidor.',
		badToken: 'Ese token non é dun operador.',
		signOut: 'Saír',
		reconnecting: 'Sen conexión co servidor; volvendo conectar…',
		dropHere: 'Solta para analizar e facer o karaoke',
		pasted: 'Ligazón pegada: analizando',
		failed: (what: string) => `Non se puido: ${what}`,
		undone: (what: string) => `Desfeito: ${what}`,
		redone: (what: string) => `Refeito: ${what}`,
		nothingToUndo: 'Non hai nada que desfacer'
	},
	nav: {
		label: 'Seccións',
		live: 'Directo',
		add: 'Engadir',
		jobs: 'Traballos',
		library: 'Biblioteca',
		nodes: 'Nodos',
		outputs: 'Saídas',
		settings: 'Axustes'
	},
	groups: {
		navigation: 'Ir a',
		transport: 'Antena',
		queue: 'Cola',
		jobs: 'Traballos',
		library: 'Biblioteca',
		general: 'Xeral',
		outputs: 'Saídas',
		nodes: 'Nodos'
	},
	cmd: {
		palette: 'Paleta de ordes',
		cheatsheet: 'Atallos de teclado',
		undo: 'Desfacer',
		redo: 'Refacer',
		toggle: 'Reproducir ou pausar',
		play: 'Reproducir',
		pause: 'Pausar',
		next: 'Seguinte canción',
		previous: 'Canción anterior',
		back: 'Atrás 5 s',
		forward: 'Adiante 5 s',
		restart: 'Desde a entrada',
		volumeUp: 'Subir o volume',
		volumeDown: 'Baixar o volume',
		pitchUp: 'Subir o ton',
		pitchDown: 'Baixar o ton',
		pitchReset: 'Ton orixinal',
		stop: 'Parar',
		search: 'Buscar',
		nextScreen: 'Seguinte pantalla',
		add: 'Engadir unha canción',
		down: 'Abaixo',
		up: 'Arriba',
		open: 'Abrir',
		toggleSelect: 'Marcar',
		selectDown: 'Estender a selección abaixo',
		selectUp: 'Estender a selección arriba',
		selectAll: 'Marcar todo',
		addToQueue: 'Á cola',
		addNext: 'A continuación',
		remove: 'Quitar da cola',
		moveUp: 'Subir na cola',
		moveDown: 'Baixar na cola',
		cue: 'Preparar',
		playNow: 'Poñer xa',
		retry: 'Reintentar',
		retryElsewhere: 'Reintentar noutro worker',
		cancel: 'Cancelar',
		pauseJob: 'Pausar o traballo',
		resumeJob: 'Continuar o traballo',
		prioritise: 'Darlle prioridade',
		deprioritise: 'Quitarlle prioridade',
		retryFailed: 'Reintentar os fallidos',
		export: 'Exportar MP4',
		edit: 'Corrixir a letra',
		trash: 'Mandar á papeleira',
		enrolWorker: 'Enrolar un worker',
		enrolPlayer: 'Enrolar unha pantalla'
	},
	palette: {
		label: 'Paleta de ordes',
		placeholder: 'Unha orde, unha canción, un nodo…',
		empty: 'Nada coincide',
		song: 'Canción',
		worker: 'Worker',
		player: 'Pantalla',
		hint: '↑↓ moverse · ↵ facer · Esc pechar'
	},
	cheatsheet: {
		title: 'Atallos de teclado',
		rebind: 'Cambiar en Axustes',
		pending: (key: string) => `${key}…`
	},
	strip: {
		onAir: 'No ar',
		standby: 'En espera',
		loading: 'Cargando',
		noSignal: 'Sen sinal',
		server: 'Servidor',
		online: 'En liña',
		reconnecting: 'Reconectando',
		latency: (ms: number) => `${ms} ms`,
		workers: (on: number, all: number) => `${on}/${all} workers`,
		running: (n: number) => plural(n, 'gl', { one: '# en curso', other: '# en curso' }),
		review: (n: number) => plural(n, 'gl', { one: '# por revisar', other: '# por revisar' }),
		alerts: (n: number) => plural(n, 'gl', { one: '# aviso', other: '# avisos' }),
		screen: 'Pantalla',
		noScreen: 'Sen pantallas'
	},
	deck: {
		nothing: 'Nada no ar',
		cued: 'Preparada',
		upNext: 'A seguir',
		key: 'Ton',
		volume: 'Volume',
		original: 'orixinal',
		semitones: (n: number) => `${n > 0 ? '+' : ''}${n} st`,
		remaining: (time: string) => `−${time}`,
		emptyQueue: 'Cola baleira',
		offline: 'A pantalla non está conectada'
	},
	live: {
		title: 'Directo',
		program: 'Programa',
		queue: (screen: string) => `Cola · ${screen}`,
		queueEmpty: 'A cola está baleira. Engade cancións desde a Biblioteca ou busca aquí.',
		quickAdd: 'Engadir á cola: busca unha canción',
		played: 'Xa soou',
		singer: 'Quen canta',
		noSinger: 'sen nome',
		dragHint: 'Arrastra para ordenar',
		noPlayer: 'Aínda non hai ningunha pantalla.',
		noPlayerHint: 'Enrola un reprodutor en Nodos e aparecerá aquí.',
		alerts: 'Avisos da pantalla',
		lyricsPreview: 'Letra',
		cache: {
			absent: 'sen descargar',
			downloading: 'descargando',
			verifying: 'comprobando',
			ready: 'lista',
			failed: 'fallou'
		}
	},
	add: {
		title: 'Engadir',
		lead: 'Pega a ligazón dunha canción. O sistema descobre cal é, busca a letra e ti confirmas antes de procesar.',
		link: 'Ligazón',
		placeholder: 'https://www.youtube.com/watch?v=…',
		analyse: 'Analizar',
		orFile: 'ou solta un ficheiro de audio ou vídeo',
		chooseFile: 'Escoller ficheiro',
		uploading: (name: string, pct: number) => `Subindo ${name} · ${pct} %`,
		autoConfirm: 'Seguir sen revisar cando a análise está segura',
		inProgress: 'En análise',
		toReview: 'Por revisar',
		nothing: 'Nada en análise. Pega unha ligazón para comezar.',
		steps: {
			download: 'Descarga',
			metadata: 'Metadatos',
			fingerprint: 'Pegada sonora',
			acoustid: 'AcoustID',
			musicbrainz: 'MusicBrainz',
			lyrics: 'Letra'
		},
		sources: {
			youtube: 'YouTube Music',
			title: 'Título do vídeo',
			tags: 'Etiquetas do ficheiro',
			acoustid: 'Pegada (AcoustID)',
			operator: 'Ti'
		},
		confidence: (pct: number) => `${pct} % segura`,
		fingerprint: {
			ok: 'Recoñecida pola pegada sonora',
			no_match: 'A pegada non coincide con ningunha gravación coñecida',
			no_key: 'Sen clave de AcoustID: non se escoitou a canción (configúraa no worker)',
			failed: 'Non se puido tomar a pegada sonora',
			skipped: 'Sen pegada sonora'
		},
		reviewTitle: 'Que canción é?',
		reviewLead: 'Revisa ou corrixe antes de procesar. O que confirmes é o que se usa.',
		candidates: 'Outras posibilidades',
		useThis: 'Usar esta',
		songTitle: 'Título',
		artist: 'Artista',
		language: 'Idioma da letra',
		lyrics: 'Letra',
		lyricsFound: (n: number) =>
			plural(n, 'gl', { one: '# letra atopada', other: '# letras atopadas' }),
		lyricsNone: 'Sen letra: transcribir do audio',
		lyricsOwn: 'Pegar a miña',
		lyricsSearch: 'Buscar noutra letra',
		synced: 'con tempos',
		gap: (s: string) => `${s} s de diferenza`,
		process: 'Procesar',
		processTo: (screen: string) => `Procesar e pór na cola de ${screen}`,
		discard: 'Descartar',
		queued: (title: string) => `«${title}» procesándose`,
		cover: 'Portada'
	},
	jobs: {
		title: 'Traballos',
		empty: 'Non hai traballos.',
		filters: {
			all: 'Todos',
			active: 'En curso',
			review: 'Por revisar',
			failed: 'Fallidos',
			done: 'Feitos'
		},
		states: {
			active: 'En curso',
			review: 'Por revisar',
			paused: 'En pausa',
			done: 'Feito',
			failed: 'Fallou',
			cancelled: 'Cancelado'
		},
		tasks: {
			waiting: 'agarda',
			held: 'agarda por ti',
			ready: 'na cola',
			leased: 'asignada',
			running: 'traballando',
			done: 'feita',
			failed: 'fallou',
			cancelled: 'cancelada',
			paused: 'en pausa'
		},
		kinds: {
			fetch: 'Descarga',
			analyze: 'Análise',
			make: 'Karaoke',
			package: 'Paquete',
			render: 'Vídeo'
		},
		stages: {
			download: 'descargando',
			analyze: 'analizando',
			decode: 'decodificando',
			separate: 'separando a voz',
			transcribe: 'transcribindo',
			align: 'aliñando a letra',
			encode: 'codificando',
			render: 'renderizando',
			upload: 'subindo'
		} as Record<string, string>,
		eta: (time: string) => `${time} restantes`,
		elapsed: (time: string) => `${time}`,
		on: (worker: string) => `en ${worker}`,
		attempt: (n: number) => `intento ${n}`,
		log: 'Rexistro',
		logEmpty: 'Sen liñas aínda.',
		logWhole: 'Rexistro completo',
		review: 'Revisar',
		openSong: 'Abrir na biblioteca'
	},
	errors: {
		too_big: {
			title: 'O ficheiro é grande de máis',
			hint: 'Usa unha versión máis curta ou de menos calidade.'
		},
		too_long: { title: 'A canción é longa de máis', hint: 'O límite son 20 minutos.' },
		no_audio: { title: 'Non hai son', hint: 'Comproba que o ficheiro ou o vídeo teña audio.' },
		unreadable: {
			title: 'Non se pode ler o son',
			hint: 'Proba con outro ficheiro ou outra ligazón.'
		},
		bad_url: {
			title: 'A ligazón non serve',
			hint: 'Ten que ser dunha soa canción (non unha lista nin un directo).'
		},
		download_failed: {
			title: 'A descarga fallou',
			hint: 'O sitio pode estar a bloquear: reinténtao ou usa outra ligazón.'
		},
		disk_full: {
			title: 'O disco do worker está cheo',
			hint: 'Libera espazo no worker e reinténtao.'
		},
		bad_lyrics: {
			title: 'A letra non encaixa',
			hint: 'Cambia a letra ou deixa que se transcriba.'
		},
		gpu_memory: {
			title: 'Sen memoria na GPU',
			hint: 'Pecha o que use a GPU nese equipo ou reinténtao noutro worker.'
		},
		out_of_memory: { title: 'Sen memoria', hint: 'O proceso pasou do límite de RAM: reinténtao.' },
		engine_failed: {
			title: 'O motor fallou',
			hint: 'Mira o rexistro; reinténtao ou próbao noutro worker.'
		},
		interrupted: { title: 'Interrompido', hint: 'Reinténtao.' },
		server_lost: {
			title: 'O worker perdeu o servidor',
			hint: 'Reinténtao cando a rede estea ben.'
		},
		worker_lost: {
			title: 'O worker deixou de responder',
			hint: 'Se segue sen volver, reinténtao noutro worker.'
		},
		unknown: { title: 'Fallou', hint: 'Mira o rexistro.' }
	} as Record<string, { title: string; hint: string }>,
	nodes: {
		title: 'Nodos',
		workers: 'Workers',
		players: 'Pantallas',
		emptyWorkers: 'Ningún worker. Enrola un para facer karaokes.',
		emptyPlayers: 'Ningunha pantalla. Enrola un reprodutor.',
		online: 'En liña',
		offline: 'Sen conexión',
		idle: 'Libre',
		gpu: 'GPU',
		vram: 'VRAM',
		cpu: 'CPU',
		ram: 'RAM',
		temp: (c: number) => `${Math.round(c)} °C`,
		of: (used: string, total: string) => `${used} / ${total}`,
		running: (n: number) => plural(n, 'gl', { one: '# tarefa', other: '# tarefas' }),
		busyPlaying: 'A pantalla deste equipo está soando: non colle traballo de GPU',
		takes: 'Fai',
		token: 'Token de enrolado · válido unha vez, 24 h',
		howWorker: 'No worker:',
		howPlayer: 'No reprodutor:',
		fingerprint: 'Pegada do certificado',
		revoke: 'Revogar',
		revoked: (name: string) => `${name} revogado`,
		lastSeen: (time: string) => `visto hai ${time}`,
		displays: (n: number) => plural(n, 'gl', { one: '# pantalla', other: '# pantallas' }),
		outputs: (n: number) => plural(n, 'gl', { one: '# saída de son', other: '# saídas de son' })
	},
	playerErrors: {
		output_failed: 'Non se puido abrir unha saída de son',
		output_lost: 'Desapareceu unha saída de son',
		display_failed: 'Non se puido abrir unha pantalla',
		load_failed: 'Non se puido cargar a canción',
		master_lost: 'Perdeuse a saída mestra: pausado'
	} as Record<string, string>,
	library: {
		title: 'Biblioteca',
		search: 'Buscar por título, artista ou idioma',
		empty: 'Aínda non hai cancións. Engade unha.',
		count: (n: number) => plural(n, 'gl', { one: '# canción', other: '# cancións' }),
		version: (v: number) => `v${v}`,
		added: (title: string, screen: string) => `«${title}» na cola de ${screen}`,
		exporting: (title: string) => `Exportando «${title}»`,
		trashed: (n: number) =>
			plural(n, 'gl', { one: '# canción na papeleira', other: '# cancións na papeleira' })
	},
	outputs: {
		title: 'Saídas',
		noPlayer: 'Escolle unha pantalla arriba.',
		displays: 'Pantallas',
		audio: 'Son',
		master: 'Mestra',
		matrix: 'Enrutado',
		vocals: 'Voz guía',
		instrumental: 'Música',
		gain: 'Ganancia (dB)',
		delay: 'Retardo (ms)',
		calibration: 'Calibración (ms)',
		policy: 'Se desaparece',
		pause: 'Pausar',
		continue: 'Seguir',
		layout: {
			'video-lyrics': 'Vídeo e letra',
			lyrics: 'Só letra',
			video: 'Só vídeo',
			off: 'Apagada'
		} as Record<string, string>,
		primary: 'principal',
		shows: 'Mostra',
		theme: 'Tema',
		save: 'Gardar',
		saved: 'Saídas gardadas',
		unsaved: 'Cambios sen gardar',
		bluetooth: 'Bluetooth: a latencia varía',
		disconnected: 'desconectada'
	},
	settings: {
		title: 'Axustes',
		language: 'Idioma',
		effects: 'Efectos',
		effectsFull: 'Completos',
		effectsCalm: 'Tranquilos',
		effectsOff: 'Apagados',
		shortcuts: 'Atallos',
		press: 'Preme o novo atallo…',
		reset: 'Restaurar',
		conflict: 'Choca con outro atallo',
		account: 'Conta',
		server: 'Servidor',
		version: 'Versión',
		identify: 'Identificación de cancións',
		identifyHelp:
			'A pegada sonora usa AcoustID. Cada worker precisa unha clave gratuíta (acoustid.org/new-application): gárdaa con «karaoke-worker acoustid-key CLAVE».'
	},
	editor: {
		title: 'Corrixir a letra',
		save: 'Gardar unha versión nova',
		saved: 'Versión nova gardada',
		conflict: 'Alguén cambiou a canción mentres tanto',
		play: 'Escoitar',
		back: 'Volver'
	},
	languages: {
		gl: 'Galego',
		es: 'Castelán',
		pt: 'Portugués',
		en: 'Inglés',
		ca: 'Catalán',
		eu: 'Éuscaro',
		fr: 'Francés',
		it: 'Italiano',
		de: 'Alemán'
	} as Record<string, string>,
	common: {
		close: 'Pechar',
		cancel: 'Cancelar',
		save: 'Gardar',
		delete: 'Borrar',
		loading: 'Cargando…',
		none: '—',
		copy: 'Copiar',
		copied: 'Copiado',
		more: 'Máis',
		update: 'Actualizar',
		updateReady: 'Hai unha versión nova'
	}
};

export type Messages = typeof gl;

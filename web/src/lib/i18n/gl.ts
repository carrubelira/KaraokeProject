import { plural } from './plural';

/** Galician: the reference dictionary. English must have exactly the same keys. */
export const gl = {
	app: {
		name: 'Karaoke',
		signIn: 'Entrar',
		signInTitle: 'Karaoke en Galego',
		signInLead: 'Panel de control',
		tokenLabel: 'Token de operador',
		tokenHint: 'Xérao no servidor con `karaoke-server operator add «o teu nome»`.',
		badToken: 'Ese token non é dun operador.',
		signOut: 'Saír',
		reconnecting: 'Perdeuse a conexión co servidor. Volvendo conectar…',
		dropHere: 'Solta o ficheiro para engadir a canción',
		pasted: 'Ligazón pegada: analizando a canción',
		failed: (what: string) => `Non se puido completar: ${what}`,
		undone: (what: string) => `Desfeito: ${what}`,
		redone: (what: string) => `Refeito: ${what}`,
		nothingToUndo: 'Non hai nada que desfacer'
	},
	nav: {
		label: 'Menú principal',
		playback: 'Reprodución',
		library: 'Biblioteca',
		add: 'Engadir canción',
		jobs: 'Procesamento',
		devices: 'Equipos',
		outputs: 'Saídas',
		settings: 'Axustes'
	},
	groups: {
		navigation: 'Ir a',
		playback: 'Reprodución',
		queue: 'Cola',
		jobs: 'Procesamento',
		library: 'Biblioteca',
		general: 'Xeral',
		outputs: 'Saídas',
		devices: 'Equipos'
	},
	cmd: {
		palette: 'Buscar ordes',
		cheatsheet: 'Atallos de teclado',
		undo: 'Desfacer',
		redo: 'Refacer',
		toggle: 'Reproducir ou pausar',
		start: 'Comezar',
		play: 'Reproducir',
		pause: 'Pausar',
		next: 'Seguinte canción',
		previous: 'Canción anterior',
		back: 'Atrás 5 s',
		forward: 'Adiante 5 s',
		restart: 'Desde o principio',
		volumeUp: 'Subir o volume',
		volumeDown: 'Baixar o volume',
		pitchUp: 'Subir o ton',
		pitchDown: 'Baixar o ton',
		pitchReset: 'Ton orixinal',
		stop: 'Parar',
		search: 'Buscar',
		add: 'Engadir unha canción',
		down: 'Abaixo',
		up: 'Arriba',
		toggleSelect: 'Marcar',
		selectDown: 'Estender a selección abaixo',
		selectUp: 'Estender a selección arriba',
		selectAll: 'Marcar todo',
		addToQueue: 'Engadir á cola',
		addNext: 'Poñer a continuación',
		remove: 'Quitar da cola',
		moveUp: 'Subir na cola',
		moveDown: 'Baixar na cola',
		cue: 'Preparar',
		playNow: 'Reproducir agora',
		retry: 'Reintentar',
		retryElsewhere: 'Reintentar noutro equipo',
		cancel: 'Cancelar',
		pauseJob: 'Pausar',
		resumeJob: 'Continuar',
		retryFailed: 'Reintentar os que fallaron',
		export: 'Exportar vídeo',
		edit: 'Corrixir a letra',
		trash: 'Mandar á papeleira',
		enrolWorker: 'Engadir un equipo de procesado'
	},
	palette: {
		label: 'Buscar ordes',
		placeholder: 'Escribe unha orde, unha canción ou un equipo',
		empty: 'Non hai resultados',
		song: 'Canción',
		worker: 'Equipo de procesado',
		hint: '↑ ↓ para moverte · Intro para escoller · Esc para pechar'
	},
	cheatsheet: {
		title: 'Atallos de teclado',
		rebind: 'Pódense cambiar en Axustes.'
	},
	server: {
		connected: 'Servidor conectado',
		reconnecting: 'Reconectando…'
	},
	screen: {
		connecting: 'Conectando co servidor…',
		nothing: 'Aínda non hai ningunha canción preparada',
		upNow: 'Agora canta',
		next: 'Despois',
		downloading: 'Descargando a canción',
		preparing: 'Preparando…',
		ready: 'Lista para comezar',
		paused: 'En pausa',
		offline: 'Sen conexión co servidor',
		fullscreen: 'Pantalla completa',
		error: 'Esta pantalla non pode mostrar a canción',
		reload: 'Volver cargar'
	},
	player: {
		nothing: 'Non se está a reproducir nada',
		states: {
			idle: 'Parado',
			cueing: 'Preparando',
			cued: 'Listo para comezar',
			playing: 'Reproducindo',
			paused: 'En pausa',
			ended: 'Rematou',
			fault: 'Sen son'
		} as Record<string, string>,
		audioDown: 'Sen motor de son',
		screensReady: (ready: number, total: number) => `${ready}/${total} pantallas listas`,
		next: 'Despois',
		key: 'Ton',
		semitones: (n: number) => `${n > 0 ? '+' : ''}${n}`,
		volume: 'Volume'
	},
	playback: {
		title: 'Reprodución',
		description: 'O que soa agora, as pantallas e a cola.',
		queue: 'Cola',
		queueEmpty:
			'A cola está baleira. Busca unha canción aquí enriba ou engádea dende a Biblioteca.',
		addPlaceholder: 'Buscar unha canción para engadila á cola',
		number: 'N.º',
		song: 'Canción',
		singer: 'Quen canta',
		duration: 'Duración',
		status: 'Estado',
		played: 'Xa soou',
		onNow: 'Soando',
		dragHint: 'Arrastra as filas para cambiar a orde',
		noScreens: 'Ningunha pantalla aberta. Abre /pantalla nun navegador da rede.',
		onScreens: (ready: number, total: number) => `${ready}/${total} pantallas`,
		alerts: 'Avisos do son',
		lyrics: 'Letra',
		cache: {
			absent: 'Sen descargar',
			downloading: 'Descargando',
			verifying: 'Comprobando',
			ready: 'Lista',
			failed: 'Erro na descarga'
		}
	},
	add: {
		title: 'Engadir canción',
		lead: 'Pega a ligazón da canción. O programa identifícaa e busca a letra; despois revisas os datos antes de crear o karaoke.',
		link: 'Ligazón',
		placeholder: 'https://www.youtube.com/watch?v=…',
		analyse: 'Analizar',
		orFile: 'Tamén podes subir un ficheiro de audio ou vídeo.',
		chooseFile: 'Subir ficheiro',
		uploading: (name: string, pct: number) => `Subindo ${name} (${pct} %)`,
		autoConfirm: 'Crear o karaoke sen revisar cando a identificación é segura',
		inProgress: 'En análise',
		toReview: 'Pendentes de revisión',
		nothing: 'Non hai ningunha canción en análise.',
		steps: {
			download: 'Descarga',
			metadata: 'Datos da páxina',
			fingerprint: 'Pegada sonora',
			acoustid: 'AcoustID',
			musicbrainz: 'MusicBrainz',
			lyrics: 'Letra'
		},
		sources: {
			youtube: 'YouTube Music',
			title: 'Título do vídeo',
			tags: 'Etiquetas do ficheiro',
			acoustid: 'Pegada sonora',
			operator: 'Escrito por ti'
		},
		confidence: (pct: number) => `${pct} %`,
		fingerprint: {
			ok: 'Identificada pola pegada sonora.',
			no_match: 'A pegada sonora non coincide con ningunha gravación coñecida.',
			no_key: 'Sen clave de AcoustID: a canción non se identificou polo son.',
			failed: 'Non se puido tomar a pegada sonora.',
			skipped: 'Non se tomou a pegada sonora.'
		},
		reviewTitle: 'Revisar os datos da canción',
		reviewLead: 'Comproba ou corrixe os datos. O karaoke crearase con estes datos.',
		candidates: 'Outras coincidencias',
		songTitle: 'Título',
		artist: 'Artista',
		language: 'Idioma da letra',
		lyrics: 'Letra',
		lyricsFound: (n: number) =>
			plural(n, 'gl', { one: '# letra atopada', other: '# letras atopadas' }),
		lyricsNone: 'Sen letra (transcribir do audio)',
		lyricsOwn: 'Pegar a letra a man',
		lyricsSearch: 'Buscar',
		synced: 'Con tempos',
		gap: (s: string) => `${s} s de diferenza`,
		show: 'Ver',
		process: 'Crear o karaoke',
		processToQueue: 'Crear e engadir á cola',
		discard: 'Descartar',
		queued: (title: string) => `Creando o karaoke de «${title}»`
	},
	jobs: {
		title: 'Procesamento',
		description: 'Cada canción pasa por descarga, análise e creación do karaoke.',
		empty: 'Non hai nada en procesamento.',
		filters: {
			all: 'Todo',
			active: 'En curso',
			review: 'Por revisar',
			failed: 'Con erro',
			done: 'Rematado'
		},
		song: 'Canción',
		status: 'Estado',
		step: 'Paso actual',
		device: 'Equipo',
		time: 'Tempo',
		states: {
			active: 'En curso',
			review: 'Agarda revisión',
			paused: 'En pausa',
			done: 'Rematado',
			failed: 'Erro',
			cancelled: 'Cancelado'
		},
		tasks: {
			waiting: 'Agardando',
			held: 'Agarda a túa revisión',
			ready: 'Na cola',
			leased: 'Comezando',
			running: 'En curso',
			done: 'Feito',
			failed: 'Erro',
			cancelled: 'Cancelado',
			paused: 'En pausa'
		},
		kinds: {
			fetch: 'Descarga',
			analyze: 'Análise',
			make: 'Creación do karaoke',
			package: 'Empaquetado',
			render: 'Vídeo MP4'
		},
		stages: {
			download: 'Descargando',
			analyze: 'Analizando',
			decode: 'Lendo o audio',
			separate: 'Separando a voz',
			transcribe: 'Transcribindo',
			align: 'Sincronizando a letra',
			encode: 'Codificando',
			render: 'Xerando o vídeo',
			upload: 'Gardando'
		} as Record<string, string>,
		eta: (time: string) => `quedan ${time}`,
		on: (worker: string) => worker,
		attempt: (n: number) => `intento ${n}`,
		steps: 'Pasos',
		log: 'Rexistro',
		showLog: 'Ver rexistro',
		hideLog: 'Ocultar rexistro',
		logEmpty: 'O rexistro está baleiro.',
		review: 'Revisar',
		openSong: 'Ver na biblioteca'
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
			title: 'A ligazón non é válida',
			hint: 'Ten que ser dunha soa canción, non dunha lista nin dunha emisión en directo.'
		},
		download_failed: {
			title: 'Fallou a descarga',
			hint: 'Pode que a páxina estea a bloquear a descarga. Reinténtao ou usa outra ligazón.'
		},
		disk_full: {
			title: 'O disco do equipo está cheo',
			hint: 'Libera espazo nese equipo e reinténtao.'
		},
		bad_lyrics: {
			title: 'A letra non encaixa',
			hint: 'Cambia a letra ou deixa que se transcriba.'
		},
		gpu_memory: {
			title: 'Sen memoria na tarxeta gráfica',
			hint: 'Pecha os programas que a usen ou reinténtao noutro equipo.'
		},
		out_of_memory: {
			title: 'Sen memoria',
			hint: 'O proceso superou o límite de memoria. Reinténtao.'
		},
		engine_failed: {
			title: 'Fallou a creación do karaoke',
			hint: 'Mira o rexistro; reinténtao ou próbao noutro equipo.'
		},
		interrupted: { title: 'Interrompido', hint: 'Reinténtao.' },
		server_lost: { title: 'O equipo perdeu o servidor', hint: 'Reinténtao cando volva a rede.' },
		worker_lost: {
			title: 'O equipo deixou de responder',
			hint: 'Se non volve, reinténtao noutro equipo.'
		},
		unknown: { title: 'Erro', hint: 'Mira o rexistro.' }
	} as Record<string, { title: string; hint: string }>,
	devices: {
		title: 'Equipos',
		description: 'Os ordenadores que crean os karaokes e as pantallas que os mostran.',
		workers: 'Equipos de procesado',
		screens: 'Pantallas',
		emptyWorkers: 'Non hai ningún equipo de procesado. Engade un para crear karaokes.',
		emptyScreens: 'Aínda non se abriu ningunha pantalla.',
		name: 'Nome',
		status: 'Estado',
		disconnected: 'Desconectado',
		free: 'Libre',
		working: 'Procesando',
		gpu: 'GPU',
		vram: 'Memoria GPU',
		cpu: 'CPU',
		ram: 'Memoria',
		temp: (c: number) => `${Math.round(c)} °C`,
		of: (used: string, total: string) => `${used} de ${total}`,
		current: 'Traballo actual',
		song: 'Canción',
		outputs: 'Saídas',
		busyPlaying: 'Non colle traballo mentres soa unha canción neste ordenador.',
		token: 'Clave de alta (vale unha vez durante 24 h)',
		howWorker: 'Executa isto no equipo de procesado:',
		howScreen: 'Calquera navegador da rede é unha pantalla: abre isto nel (ou no quiosco).',
		sync: 'Sincronía',
		maxHeight: 'Vídeo máximo',
		preview: 'vista previa',
		forget: 'Esquecer',
		revoke: 'Retirar',
		revoked: (name: string) => `${name} retirado`,
		lastSeen: (time: string) => `visto hai ${time}`
	},
	screenStates: {
		connecting: 'Conectando',
		idle: 'Sen canción',
		provisioning: 'Descargando',
		syncing: 'Sincronizando',
		waiting: 'Lista',
		playing: 'Reproducindo',
		paused: 'En pausa',
		error: 'Erro'
	} as Record<string, string>,
	screenFlags: {
		offline: 'Sen conexión',
		hidden: 'A pestana está oculta',
		degraded: 'O vídeo non dá seguido o ritmo',
		fullscreen: 'Pantalla completa'
	} as Record<string, string>,
	stage: {
		startAnyway: (names: string) =>
			`Estas pantallas aínda non están listas: ${names}. Comezar igual? Incorporaranse en canto poidan.`,
		stillCueing: 'O son aínda está preparando a canción'
	},
	audioErrors: {
		output_failed: 'Non se puido abrir unha saída de son',
		output_lost: 'Desconectouse unha saída de son',
		load_failed: 'Non se puido cargar a canción',
		master_lost: 'Desconectouse a saída principal; a reprodución está en pausa'
	} as Record<string, string>,
	library: {
		title: 'Biblioteca',
		search: 'Buscar por título, artista ou idioma',
		empty: 'Aínda non hai cancións.',
		count: (n: number) => plural(n, 'gl', { one: '# canción', other: '# cancións' }),
		songTitle: 'Título',
		artist: 'Artista',
		language: 'Idioma',
		duration: 'Duración',
		version: 'Versión',
		inQueue: 'Na cola',
		added: (title: string) => `«${title}» engadida á cola`,
		exporting: (title: string) => `Exportando o vídeo de «${title}»`,
		trashed: (n: number) =>
			plural(n, 'gl', { one: '# canción na papeleira', other: '# cancións na papeleira' })
	},
	outputs: {
		title: 'Saídas',
		description: 'Por onde sae o son do escenario: as tarxetas de son e DAC deste ordenador.',
		engineOffline: 'O motor de son (kp-audio) non está en marcha.',
		screensElsewhere: 'O que mostra cada pantalla axústase en',
		audio: 'Saídas de son',
		master: 'Principal',
		matrix: 'Son',
		vocals: 'Voz guía',
		instrumental: 'Música',
		gain: 'Ganancia (dB)',
		delay: 'Retardo (ms)',
		calibration: 'Axuste (ms)',
		policy: 'Se se desconecta',
		pause: 'Pausar',
		continue: 'Seguir',
		layout: {
			'video-lyrics': 'Vídeo e letra',
			lyrics: 'Só a letra',
			video: 'Só o vídeo',
			off: 'Apagado'
		} as Record<string, string>,
		shows: 'Mostra',
		theme: 'Estilo da letra',
		save: 'Gardar',
		saved: 'Cambios gardados',
		unsaved: 'Hai cambios sen gardar',
		bluetooth: 'Bluetooth: o atraso pode variar'
	},
	settings: {
		title: 'Axustes',
		language: 'Idioma',
		shortcuts: 'Atallos de teclado',
		press: 'Preme o novo atallo…',
		change: 'Cambiar',
		reset: 'Restaurar',
		conflict: 'Coincide con outro atallo',
		account: 'Sesión',
		server: 'Servidor',
		version: 'Versión',
		identify: 'Identificación de cancións',
		identifyHelp:
			'A pegada sonora usa AcoustID. Cada equipo de procesado precisa unha clave gratuíta (acoustid.org/new-application): gárdaa con «karaoke-worker acoustid-key CLAVE».'
	},
	editor: {
		title: 'Corrixir a letra',
		save: 'Gardar unha versión nova',
		saved: 'Gardouse unha versión nova',
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
		loading: 'Cargando…',
		copy: 'Copiar',
		copied: 'Copiado',
		more: 'Máis'
	}
};

export type Messages = typeof gl;

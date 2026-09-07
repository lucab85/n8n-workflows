# n8n-workflows

Dump completo di tutto ciò che gira sull'istanza n8n di Luca
(`n8n.openempower.com`), pensato per essere eseguito in autonomia su
qualunque macchina con Docker — non dipende dal resto dello stack su cui
gira in produzione.

## Cosa c'è dentro

| File | Cosa fa | Trigger |
|---|---|---|
| `workflows/ai-prospect-scout.json` | Legge prospect da Google Sheets, scarica il contenuto del sito con Apify, li qualifica con OpenAI (score 1-10 + DM proposto) e riscrive il foglio | ogni 15 min / manuale |
| `workflows/japow-1-powder-watch.json` | Controlla le previsioni neve di Niseko; se scattano le condizioni (40cm overnight, 3 giorni sotto -10°C, cielo sereno il 4° giorno) propone volo + chalet e apre un sondaggio Telegram | ogni 6 ore / manuale |
| `workflows/japow-2-lock-it-in.json` | Riceve il voto del sondaggio Telegram e conferma la prenotazione (`status: proposed -> locked`) | webhook Telegram |
| `workflows/japow-3-arrival-sequence.json` | Traccia il volo in arrivo, prenota il taxi 30 min prima dell'atterraggio e ordina la birra 10 min prima di arrivare allo chalet (via chiamate vocali) | ogni 15 min + webhook posizione |
| `workflows/swell-event.json` | Controlla le previsioni surf di Uluwatu (Surfline); se il mare "spara" 3+ giorni con vento offshore propone volo + villa su Telegram | ogni 6 ore |
| `workflows/surfboard-sniper.json` | Cerca tavole da surf su Facebook Marketplace dentro un "buy box" (marca/misura/prezzo/raggio) e avvisa su Telegram quando trova un match nuovo | ogni 30 min |
| `workflows/garmin-claude-coach.json` | Legge i dati di recovery (sonno, HRV) da Supabase e chiede a Claude un piano di allenamento del giorno | ogni mattina alle 6:00 |
| `garmin-claude-coach/garmin_daily_pull.py` | Script Python che fa login su Garmin Connect e scrive i dati (attività, sonno, HRV, peso) su Supabase — è il pezzo che alimenta il workflow qui sopra | eseguito da n8n (`executeCommand`) o da cron esterno |
| `workflows/blog-to-convertkit.json` | Legge `lucaberton.com/rss.xml`, e per ogni post nuovo crea un **draft** (non invia) di broadcast su ConvertKit | ogni 6 ore / manuale |
| `workflows/advisory-lead-qualification.json` | Riceve un lead dal form del sito via webhook, lo fa valutare da Claude (fit per consulenza enterprise AI, score 1-10 + bozza di risposta) e lo scrive su Google Sheets | webhook |
| `workflows/speaking-intake.json` | Riceve un invito/CFP via webhook e lo logga su Google Sheets (`status: NEW`) | webhook |
| `workflows/speaking-reminders.json` | Ogni giorno controlla il foglio Speaking e manda un'email di promemoria per le scadenze CFP entro 7 giorni ancora non gestite | ogni 24 ore |
| `workflows/ansible-release-watch.json` | Controlla `ansible/ansible` (GitHub Releases) e il pacchetto `ansible` su PyPI; se una versione è cambiata, Claude scrive una bozza di post nello stile di quelli già su `ansiblebyexample.com` e apre una PR nel repo del blog | ogni 24 ore / manuale |
| `workflows/gmail-action-triage.json` | Legge le thread Gmail recenti, le fa classificare da Claude in 4 code operative (Oggi/Rispondere/In attesa/Follow-up) e applica la label corrispondente — mai invio/archiviazione/cancellazione automatica | 3x al giorno (08/13/18) / manuale |
| `workflows/podcast-claude-producer.json` | Da un transcript + URL sorgente, Claude genera un intero production pack per l'episodio: cold open, note di montaggio, capitoli, 3-5 short, titoli/descrizione YouTube, concept thumbnail, copy social/newsletter | webhook |

`gmail-action-triage.json` e `podcast-claude-producer.json` sono aggiunte
tue, non mie — le ho trovate già commesse nel repo (con i relativi
GitHub Actions di deploy in `.github/workflows/`) mentre lavoravo su
`ansible-release-watch.json` in parallelo. Non le ho toccate, a parte
far passare anche la loro chiamata a Claude dal bridge (vedi sotto).

Questi ultimi quattro li ho scritti da zero per il tuo business
(lucaberton.com — Production AI advisory, non le automazioni hobby dei
repo `aaronparton2-sketch`), sulla base delle opportunità di automazione
più ovvie per un consulente/formatore: distribuzione contenuti,
qualifica lead, pipeline conferenze. Ho verificato `lucaberton.com/rss.xml`
esiste davvero (RSS 2.0 standard) e testato il parsing contro il feed
reale prima di scriverlo nel workflow — non è un endpoint indovinato.
Non ho automatizzato il tracking iscrizioni/recensioni sui corsi
(Coursera/Udemy/Pluralsight/Educative): nessuna di queste piattaforme
espone un'API pubblica affidabile per un singolo instructor senza
accordi di partnership, quindi costruire un polling automatico lì
avrebbe significato inventarsi un endpoint che non esiste davvero.

Le fonti originali:
[japow-event](https://github.com/aaronparton2-sketch/japow-event),
[swell-event](https://github.com/aaronparton2-sketch/swell-event),
[surfboard-sniper](https://github.com/aaronparton2-sketch/surfboard-sniper),
[garmin-claude-coach](https://github.com/aaronparton2-sketch/garmin-claude-coach)
— li ho controllati nodo per nodo prima di importarli (nessun codice
offuscato, nessun endpoint di exfiltrazione, i segreti passano tutti dal
sistema di credenziali di n8n o da variabili d'ambiente) e integrati qui
insieme a quello che già girava sull'istanza.

**Nessun segreto è incluso in questo repo.** Ogni file `workflows/*.json`
è stato ripulito da `id` interni, project id, timestamp e riferimenti a
credenziali specifiche dell'istanza — è un export pulito, riutilizzabile
su qualunque installazione n8n.

### Un file era rotto alla fonte

`swell-event.json`, così come pubblicato nel repo originale, non si
importava: le sue `connections` puntavano a due nodi ("Book flights
(browser agent)" e "Check inbox: flight confirmed") che non esistono nel
file — probabilmente pezzi rimossi durante la stesura del template. Ho
verificato che quel ramo non avesse nessun collegamento in ingresso (un
vicolo cieco, mai raggiungibile in esecuzione) e che il resto del flusso
raggiunga comunque il tracking del volo tramite un altro nodo
("Confirmed?"), quindi ho rimosso il collegamento pendente invece di
inventarmi un'implementazione. **Il workflow importato quindi si ferma
dopo l'invio dei voli via email — prenotazione volo e controllo casella
di posta restano da implementare a mano** (serve un agente
browser/automazione email che qui non è incluso).

## Farlo girare da solo

```bash
git clone git@github.com:lucab85/n8n-workflows.git
cd n8n-workflows
cp .env.example .env
# genera una chiave: openssl rand -hex 32
# mettila in N8N_ENCRYPTION_KEY dentro .env
docker compose up -d
```

n8n sarà su `http://localhost:5678` (o sull'host che hai messo in
`N8N_HOST`/`N8N_PROTOCOL` dentro `.env`). Al primo accesso ti chiede di
creare l'account owner.

### Importare i workflow

```bash
docker cp workflows/. $(docker compose ps -q n8n):/tmp/import
docker compose exec n8n n8n import:workflow --separate --input=/tmp/import
```

**Nota su un bug della CLI:** con `n8n` 2.37.x il comando
`import:workflow` a volte fallisce con
`null value in column "id" of relation "workflow_entity"` perché non
genera da solo l'UUID del workflow. I file in questo repo hanno già un
`id` valido incluso proprio per evitare il problema — se in futuro lo
re-incontri (es. dopo un aggiornamento di n8n, o editando questi file),
la soluzione è aggiungere manualmente un `"id": "<uuid>"` al JSON prima
di importarlo.

I workflow vengono importati **disattivati** — vanno attivati a mano
dalla UI una volta configurate le credenziali.

## Credenziali da configurare

Quello che segue va nel file `.env` (vedi `.env.example`): letti
direttamente dall'ambiente del container, non da credenziali n8n.

| Variabile | Usata da |
|---|---|
| `APIFY_TOKEN` | AI Prospect Scout (`{{ $env.APIFY_TOKEN }}` nei nodi HTTP Request) |
| `OPENAI_API_KEY` | AI Prospect Scout |

Tutto il resto è una **credenziale n8n** da creare dalla UI
(*Credentials → New*) e selezionare nei nodi che la usano, oppure un
token già inserito come placeholder direttamente nell'URL/header del
nodo HTTP Request (cercalo con `grep -rn YOUR_ workflows/`):

| Servizio | Usato da | Dove ottenerla |
|---|---|---|
| Google Sheets | AI Prospect Scout, blog-to-convertkit, advisory-lead-qualification, speaking-* | OAuth2 o service account, Google Cloud Console |
| Telegram (bot) | japow-*, swell-event, surfboard-sniper | [@BotFather](https://t.me/BotFather) su Telegram |
| Supabase | japow-*, surfboard-sniper, garmin-claude-coach | Project Settings → API, sul tuo progetto Supabase |
| RapidAPI (AeroDataBox) | japow-3-arrival-sequence, swell-event | rapidapi.com, sottoscrivi AeroDataBox |
| Bland.ai | japow-3-arrival-sequence, swell-event | dashboard Bland.ai → API keys |
| Apify | swell-event, surfboard-sniper | apify.com → Settings → Integrations |
| Gmail | gmail-action-triage | OAuth2, Google Cloud Console |
| Garmin Connect | garmin-claude-coach (script Python, non il workflow) | il tuo login Garmin normale |
| SMTP | speaking-reminders | il tuo provider email (es. Gmail App Password) |

### claude-bridge — perché non c'è più una riga "Anthropic (Claude)" qui sopra

Tutti i workflow che usano Claude (garmin-claude-coach,
advisory-lead-qualification, ansible-release-watch,
podcast-claude-producer, gmail-action-triage) passano da
**[claude-bridge](https://github.com/lucab85/claude-bridge)** invece di
chiamare `api.anthropic.com` direttamente con una API key a pagamento.
Gira come container nello stesso stack VPS (vedi
`lucab85/ansible-vps-bootstrap`, `compose/claude-bridge/`), espone
`http://claude-bridge:8000/v1/chat/completions` in formato
OpenAI-compatibile, e dentro fa girare la CLI di Claude Code già
autenticata sull'host — usa la stessa sessione/quota, non una API key
separata.

Ogni nodo HTTP Request verso Claude in questi 5 workflow ha:
- `url`: `http://claude-bridge:8000/v1/chat/completions`
- header `Authorization: Bearer {{ $env.CLAUDE_BRIDGE_KEY }}`
- body in formato OpenAI (`messages: [{role, content}]`), non più la
  forma nativa di Anthropic (`system` + `messages` separati,
  `max_tokens`)
- i nodi Parse a valle leggono `resp.choices[0].message.content`
  invece di `resp.content[...].text`

**Compromesso reale, non teorico — verificato con test veri contro il
bridge prima di riscrivere questi workflow:** la CLI di Claude Code è
uno strumento agentico, non un endpoint di completions puro. Anche con
un system prompt che dice esplicitamente "rispondi SOLO con JSON,
nessuna domanda" può occasionalmente rispondere in modo conversazionale
invece di produrre JSON (mi è capitato durante i test, risolto solo
rinforzando ulteriormente il prompt). Ogni nodo Parse a valle ha già un
fallback `status: ERROR` / `success: false` per quando succede — vale
la pena controllarli nelle prime esecuzioni reali, specialmente per
`podcast-claude-producer.json` che chiede uno schema JSON molto più
grande (quindi più superficie per una deviazione).

Se preferisci l'affidabilità della vera API Anthropic per uno di questi
workflow, è un cambio localizzato: riporta il nodo HTTP a
`https://api.anthropic.com/v1/messages` con gli header/body nativi
(vedi la cronologia git di questi file per la forma esatta) e il nodo
Parse a leggere `resp.content`.

**Bug reale trovato provando `ansible-release-watch.json` per davvero
(non solo con dati sintetici):** Claude, nonostante l'istruzione "niente
blocchi markdown", a volte avvolge comunque il JSON in un blocco
` ```json ... ``` `. Il parsing originale faceva `text.indexOf('{')` e
poi prendeva tutto fino alla fine della stringa — le backtick di
chiusura finivano dentro `JSON.parse()` e lo rompevano
(`Unexpected non-whitespace character after JSON`), facendo fallire
l'intera esecuzione (il nodo non aveva un `onError`). Riprodotto con
una vera chiamata al bridge prima di scrivere il fix, non solo ipotizzato.
Il fix, applicato a tutti e 4 i nodi Parse che leggono JSON da Claude
(`ansible-release-watch`, `advisory-lead-qualification`,
`podcast-claude-producer`, `gmail-action-triage`): spoglia un eventuale
fence markdown iniziale/finale prima di cercare `{`, e usa
`lastIndexOf('}')` invece di prendere tutto fino alla fine della
stringa.

Nello stesso giro, `ansible-release-watch.json` aveva anche un
secondo problema collegato: il prompt vincolava `category` a
`fundamentals|collections|advanced`, ma Claude ha scritto `"News"` per
un annuncio di release (ragionevole, mai categoria concessa dal
prompt). La vera tassonomia del blog (`src/lib/constants.ts` in
`ansiblebyexample.com`) ha molte più categorie — ho aggiunto `news`
lì (era mancante anche per gli articoli scritti a mano) e allargato
sia il prompt che la validazione lato codice nel workflow a tutta la
tassonomia reale, con fallback a `'news'` invece di `'fundamentals'`
per un annuncio di versione.

### Setup Google Sheet (AI Prospect Scout)

Foglio con tab `Prospects`, prima riga con queste intestazioni:

```
name | company | role | linkedin_notes | website | status | score | reason | pain | opening | dm | error | processed_at
```

Aggiungi righe con `status = NEW`: il workflow le prende in carico (max 5
per esecuzione), le porta a `PROCESSING`, poi a `READY` o `ERROR`.

### Setup tabella Supabase (japow-*)

Tabella `japow_trips` — schema completo nel
[README originale](https://github.com/aaronparton2-sketch/japow-event#readme)
del repo di partenza. Colonne minime usate dai workflow: `status`,
`depart_date`, `return_date`, `flight_number`, `flight_date`,
`chalet_name`, `chalet_lat`, `chalet_lng`, `chalet_nightly`,
`beers_ordered_at`.

### Setup tabella Supabase (surfboard-sniper)

Tabella `surfboard_listings` — esegui lo schema SQL del
[repo originale](https://github.com/aaronparton2-sketch/surfboard-sniper/blob/main/supabase/schema.sql)
prima di attivare. Il "buy box" (marca, misura, prezzo, città, raggio) si
edita direttamente nel nodo Code **"Match buy box"** del workflow.

### Setup Garmin → Claude coach

Questo workflow ha due metà: uno **script Python** che fa il lavoro
pesante (login Garmin + scrittura su Supabase) e il **workflow n8n**
che legge da Supabase e chiede il piano a Claude.

```bash
cd garmin-claude-coach
pip install garminconnect requests
cp .env.example .env      # poi compilalo
python garmin_daily_pull.py --login     # una tantum, gestisce anche l'MFA
python garmin_daily_pull.py --dry-run --days 3   # verifica senza scrivere
```

Poi esegui `schema.sql` su Supabase per creare le tabelle
(`garmin_activities`, `garmin_sleep`, `garmin_daily_summary`,
`garmin_weigh_ins`, ecc.).

Il nodo **"Run daily pull"** nel workflow n8n (`executeCommand`) lancia
lo script con `python /path/to/garmin-claude-coach/garmin_daily_pull.py`
— il path è un placeholder, va aggiornato con dove hai clonato questo
repo. **Attenzione:** l'immagine `n8nio/n8n` di questo `docker-compose.yml`
non ha Python installato — o lo esegui con un cron esterno al container
(più semplice), o costruisci un'immagine n8n custom con Python +
`garminconnect` dentro. `PROMPTS.md` nella stessa cartella ha 18 prompt
di coaching pronti da usare nel nodo "Ask Claude — coach".

### Setup blog -> ConvertKit

1. Google Sheet, tab **BlogLog**, intestazioni: `guid | title | link | sent_to_convertkit_at`.
2. `CONVERTKIT_API_SECRET` in `.env` (ConvertKit → Account Settings →
   API Secret — non la API Key pubblica, quella non basta per creare
   broadcast).
3. Il workflow crea solo **draft** (`public: false`) — non manda niente
   da solo, li rivedi e li invii tu dalla dashboard ConvertKit.
4. Prima di attivarlo: esegui **Manual Test** una volta e controlla che
   `BlogLog` si popoli con i post attuali, così al primo giro
   automatico non ti ritrovi 50 draft insieme (o svuota/pre-popola il
   foglio con i guid che vuoi considerare "già visti").

### Setup lead qualification (advisory)

1. Google Sheet, tab **Leads**, intestazioni: `name | email | company | message | received_at | status | score | reason | suggested_reply | error`.
2. Chiama claude-bridge, non serve una chiave Anthropic — vedi la
   sezione "claude-bridge" più sopra per `CLAUDE_BRIDGE_KEY`.
3. Collega il form del sito all'URL webhook (dopo l'attivazione):
   `POST https://<tuo-n8n>/webhook/advisory-lead` con body JSON
   `{name, email, company, message}` — se il tuo form manda altri nomi
   di campo, rimappali nel nodo "Validate lead".
4. Non manda nessuna risposta automatica al lead: scrive score + bozza
   di risposta nel foglio, la mandi tu.

### Setup speaking pipeline

1. Google Sheet, tab **Speaking**, intestazioni: `conference | event_date | cfp_deadline | notes | status | logged_at` (date in `YYYY-MM-DD`).
2. `speaking-intake.json`: URL webhook (dopo l'attivazione)
   `POST https://<tuo-n8n>/webhook/speaking-invite` con body JSON
   `{conference, event_date, cfp_deadline, notes}` — utile con
   qualunque cosa sappia fare un POST (un form esterno, una automazione
   Notion, anche solo `curl` a mano quando ricevi un invito via email).
3. `speaking-reminders.json`: serve una credenziale **SMTP** in n8n
   (va bene una Gmail App Password). Gira una volta al giorno, manda
   un'email per ogni riga `status=NEW` con `cfp_deadline` entro 7
   giorni, poi marca la riga `REMINDED` così non te la rimanda ogni
   giorno.

### Setup Ansible release watch -> blog PR

**Cosa traccia (verificato con curl prima di scrivere il workflow, non
indovinato):**
- `ansible/ansible` su GitHub — **`ansible/ansible-core` non esiste come
  repo separato**: `ansible/ansible` è di fatto il sorgente di
  ansible-core, e le sue GitHub Releases sono quelle vere (es. `v2.21.3`).
- il pacchetto `ansible` su PyPI (quello versionato 11/12/13/14...) —
  **non ha GitHub Releases** (controllato `ansible-community/ansible-build-data`:
  zero release pubblicate lì), quindi l'unica fonte affidabile è
  `pypi.org/pypi/ansible/json` → `info.version`.

1. `GITHUB_TOKEN` in `.env` — Personal Access Token con permesso `repo`
   su **`lucab85/ansiblebyexample.com`** (deve poter creare branch, file
   e pull request).
2. Chiama claude-bridge, non serve una chiave Anthropic — vedi la
   sezione "claude-bridge" più sopra per `CLAUDE_BRIDGE_KEY`.
3. Lo stato (ultima versione vista per ciascuna fonte) vive in
   `automation/ansible-release-watch/state.json` **dentro il repo del
   blog stesso** — non serve nessun Google Sheet o database esterno, e
   ogni cambio di stato è un commit visibile.
4. Il contenuto vero (il post) arriva sempre via **pull request** — non
   viene mai mergiato in automatico. Solo l'aggiornamento del file di
   stato va dritto su `main` (non è contenuto editoriale, è il registro
   di cosa è già stato processato, altrimenti la stessa versione
   verrebbe riproposta ogni giorno finché la PR non è mergiata).
5. Frontmatter e struttura del post modellati su un articolo reale già
   pubblicato (`Ansible 14 Community Package RC1 — Whats New and How
   to Test.md`) — stesso schema YAML (`title/description/author/date/category/tags`),
   stessa struttura H1→H2/H3.
6. **Non testato end-to-end contro il repo vero** — avrebbe significato
   aprire branch/PR reali sul tuo blog senza permesso. Ho invece: (a)
   verificato con curl ogni endpoint GitHub/PyPI usato, (b) testato la
   logica di confronto-versioni e di costruzione file/branch fuori da
   n8n con dati reali (e trovato/corretto due bug così: un pezzo di URL
   che perdeva il segmento `tutorials/`, e i tag numerici tipo "2.22"
   che senza virgolette in YAML diventano numeri invece di stringhe),
   (c) importato la struttura in n8n per validarla. Guarda con
   attenzione la prima PR che apre prima di fidarti del resto.
7. **Espansione ai repo satellite (collection):** aggiungi altre coppie
   "HTTP Request → Combine current versions" per ogni
   `ansible-collections/<nome>` che vuoi seguire (quelle usano GitHub
   Releases normalmente, come `ansible/ansible`) — la logica di
   confronto/stato/PR sotto non cambia.

### Webhook da esporre (japow-2, japow-3, advisory-lead-qualification, speaking-intake)

Se vuoi che Telegram, il tracker di posizione (OwnTracks / iOS
Shortcuts) e il form del sito raggiungano l'istanza, `WEBHOOK_URL` in
`.env` deve puntare a un host pubblicamente raggiungibile in HTTPS (non
`localhost`) — path esposti dai workflow:

- `POST /webhook/japow-poll` — risposta al sondaggio Telegram
- `POST /webhook/japow-location` — ping di posizione durante il transfer
- `POST /webhook/advisory-lead` — nuovo lead dal form del sito
- `POST /webhook/speaking-invite` — nuovo invito/CFP

## Cosa NON fa questo repo

- Non configura Telegram/Supabase/Apify/OpenAI/Anthropic/RapidAPI/Bland.ai/Garmin
  per te — quelle sono chiavi e credenziali personali, vanno create e
  inserite a mano.
- Non attiva i workflow — restano `active: false` finché non li accendi
  tu dalla UI, dopo aver verificato che le credenziali siano a posto.
- `ai-prospect-scout.json` non fa scraping né invio automatico su
  LinkedIn — prepara solo il messaggio, l'invio resta manuale.
- `swell-event.json` non prenota voli né controlla la posta in automatico
  (vedi sopra) — si ferma all'invio delle opzioni di volo via email.
- `blog-to-convertkit.json` non invia mai newsletter da solo — crea solo
  draft, l'invio è sempre una tua decisione manuale.
- `advisory-lead-qualification.json` non risponde mai al lead — scrive
  solo score e bozza di risposta nel foglio.
- `ansible-release-watch.json` non merge mai il post da solo — apre
  sempre una PR, il merge (e la revisione dei fatti) restano tuoi.
  Solo l'aggiornamento del file di stato va dritto su `main`.
- Non c'è nessuna automazione per iscrizioni/recensioni sui corsi
  (Coursera/Udemy/Pluralsight/Educative) — quelle piattaforme non
  espongono un'API pubblica affidabile per un singolo instructor, quindi
  non ho costruito un'integrazione che si basa su un endpoint che non
  esiste davvero.

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

I tre workflow `japow-*` vengono da
[aaronparton2-sketch/japow-event](https://github.com/aaronparton2-sketch/japow-event)
— li ho controllati nodo per nodo prima di importarli (nessun codice
offuscato, nessun endpoint di exfiltrazione, i segreti passano tutti dal
sistema di credenziali di n8n) e integrati qui insieme a quello che già
girava sull'istanza.

**Nessun segreto è incluso in questo repo.** Ogni file `workflows/*.json`
è stato ripulito da `id` interni, project id, timestamp e riferimenti a
credenziali specifiche dell'istanza — è un export pulito, riutilizzabile
su qualunque installazione n8n.

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
docker compose exec n8n n8n import:workflow --separate --input=/tmp/import
```

Prima però devi copiare i file dentro il container, dato che il volume
non li monta di default:

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

Tutto quello che non è nella tabella qui sotto va nel file `.env`
(vedi `.env.example`): `APIFY_TOKEN` e `OPENAI_API_KEY` sono letti
direttamente dall'ambiente del container (`{{ $env.APIFY_TOKEN }}` nei
nodi HTTP Request), non da credenziali n8n.

Tutto il resto è una **credenziale n8n** da creare dalla UI
(*Credentials → New*) e selezionare nei nodi che la usano:

| Servizio | Usato da | Dove ottenerla |
|---|---|---|
| Google Sheets | AI Prospect Scout | OAuth2 o service account, Google Cloud Console |
| Telegram (bot) | tutti e 3 i `japow-*` | [@BotFather](https://t.me/BotFather) su Telegram |
| Supabase | tutti e 3 i `japow-*` | Project Settings → API, sul tuo progetto Supabase |
| RapidAPI (AeroDataBox) | `japow-3-arrival-sequence` | rapidapi.com, sottoscrivi AeroDataBox |
| Bland.ai | `japow-3-arrival-sequence` | dashboard Bland.ai → API keys |

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

### Webhook da esporre (japow-2, japow-3)

Se vuoi che Telegram e il tracker di posizione (OwnTracks / iOS
Shortcuts) raggiungano l'istanza, `WEBHOOK_URL` in `.env` deve puntare a
un host pubblicamente raggiungibile in HTTPS (non `localhost`) — path
esposti dai workflow:

- `POST /webhook/japow-poll` — risposta al sondaggio Telegram
- `POST /webhook/japow-location` — ping di posizione durante il transfer

## Cosa NON fa questo repo

- Non configura Telegram/Supabase/Apify/OpenAI/RapidAPI/Bland.ai per te —
  quelle sono chiavi personali, vanno create e inserite a mano.
- Non attiva i workflow — restano `active: false` finché non li accendi
  tu dalla UI, dopo aver verificato che le credenziali siano a posto.
- `ai-prospect-scout.json` non fa scraping né invio automatico su
  LinkedIn — prepara solo il messaggio, l'invio resta manuale.

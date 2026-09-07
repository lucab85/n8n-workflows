# Gmail AI Triage — Action Queues

Thread-level Gmail triage for Luca's action queues:

- `1 · Oggi`
- `2 · Rispondere`
- `3 · In attesa`
- `4 · Follow-up`

The workflow is stored in `workflows/gmail-ai-triage.json` and deploys to
`https://n8n.openempower.com` through
`.github/workflows/deploy-gmail-ai-triage.yml`.

## Behaviour

- Trigger: 08:00, 13:00 and 18:00 in `Europe/Amsterdam`, plus manual execution.
- Search: `in:inbox category:personal newer_than:7d -in:spam -in:trash`.
- Max: 60 recent threads per execution.
- Reads the full Gmail thread (up to the last 10 messages are sent to the model).
- Classifies the **current state of the conversation**, not the latest email in isolation.
- Only changes queue labels when model confidence is at least `0.72`.
- If the classification is uncertain, the existing manual queue is left untouched.
- Scheduled executions cache unchanged threads by Gmail `internalDate`, so the same thread is not re-scored three times per day.
- Manual execution bypasses that cache to support a full re-test.

## Safety boundaries

The workflow never:

- sends or replies to email;
- archives email;
- trashes or deletes email;
- snoozes email;
- marks messages read/unread.

It only adds or removes the four action-queue labels listed above.

## One-time n8n setup

1. Ensure `OPENAI_API_KEY` is available in the n8n container environment.
   The repository's Docker setup already exposes that variable.
2. Ensure the four Gmail labels exist with the exact names above.
3. Connect a Gmail OAuth2 credential to the Gmail nodes.
   - The deployment Action first tries to preserve a credential already bound
     to this workflow.
   - On first deployment it can also reuse the non-secret Gmail credential
     reference from another workflow on the same n8n instance.
   - If no Gmail credential reference exists anywhere, the Action deploys the
     workflow **inactive**. Bind Gmail once in the n8n UI and rerun the Action.
4. Run `Manual Test` once and inspect the classifications.
5. Publish/activate (the deploy Action does this automatically once Gmail is
   bound).

## Deployment

The Action uses the existing repository secret `N8N_API_KEY` and the n8n
public API. It creates or updates the workflow by name and then publishes /
activates it when Gmail credentials are available.

Manual deploy/retry:

1. Open GitHub Actions.
2. Select **Deploy Gmail AI triage to n8n**.
3. Run **workflow_dispatch**.

The workflow JSON intentionally contains no n8n credential IDs or secrets.

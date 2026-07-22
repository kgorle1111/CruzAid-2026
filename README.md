# CruzAid

[![CI](https://github.com/kgorle1111/CruzAid-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/kgorle1111/CruzAid-2026/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Stack:** Python · Flask · Twilio · Gemini (via OpenRouter) · MongoDB · flask-limiter

A student in Santa Cruz texts a symptom to a phone number. A few seconds later they get back the nearest relevant health resource: name, phone, address, and a Google Maps link. No app to install, no account, works on any phone that can send a text.

Built at CruzHacks 2026.

## Why SMS

Most campus health tools assume a smartphone, a login, and someone calm enough to navigate a menu. The moment I was designing for is the opposite: someone stressed, maybe at 2am, who just wants to know where to go. SMS has none of those barriers and reaches essentially every phone. The tradeoff is that you get one plain-text channel and no UI, so the routing logic has to be good enough that a single reply is actually useful.

## How it works

```
Text message  ->  Twilio  ->  POST /sms  (Flask)
                                  |
                                  |-- ask_gemini()  -- OpenRouter (Gemini) --> one category:
                                  |                    sexual, mental, dental, emergency, student
                                  |
                                  |-- MongoDB lookup by tag --> up to 3 matching resources
                                  |
                                  reply with names, phones, and map links  <--
```

The LLM does one job: read the message and pick one of five categories. That category is a tag lookup against a MongoDB collection of local resources. I kept the model on the smallest tier that classified reliably (`gemini-2.5-flash-lite`) because the task is classification, not reasoning, and a bigger model would cost more for no accuracy gain.

The part I care about most is that the bot never leaves someone hanging. If the LLM call fails, it defaults to `student` (the general-care bucket). If MongoDB is unreachable, it replies with hard-coded emergency numbers instead of an error. Someone in a crisis should never get a stack trace back.

## Setup

Needs Python 3.9+, a MongoDB Atlas cluster, an [OpenRouter](https://openrouter.ai) key, and a Twilio number.

```bash
poetry install
cp .env.example .env      # fill in OPENROUTER_API_KEY and MONGO_URI
poetry run python setup_data.py   # seeds resources into MongoDB
poetry run python app.py          # runs on :5000
```

Expose the local server (`ngrok http 5000`) and point your Twilio number's messaging webhook at `https://<your-tunnel>/sms` over HTTP POST.

### Docker

```bash
docker build -t cruzaid .
docker run -p 5000:5000 --env-file .env cruzaid
```

The container runs gunicorn with two workers rather than Flask's debug server, since debug mode is not safe to expose. Seed the database once before first use:

```bash
docker run --env-file .env cruzaid python setup_data.py
```

## Rate limiting

`/sms` is capped at 10 requests per minute per sender phone number, using `flask-limiter`.

The interesting decision here is the key. The obvious choice is to limit by IP, but every request arrives from Twilio's servers, so an IP limit would count all users as one person and throttle the whole system the moment traffic picked up. Keying on the `From` phone number instead limits an individual spammer without affecting anyone else.

The store defaults to in-memory, which is correct only for a single process. Since the Docker image runs two gunicorn workers, set `RATELIMIT_STORAGE_URI` to a Redis URL (for example `redis://localhost:6379`) so the workers share one limit. Leave it unset for local single-worker development.

## Environment variables

| Variable             | Purpose                                       |
|----------------------|-----------------------------------------------|
| `OPENROUTER_API_KEY`     | OpenRouter API key for the triage classifier      |
| `MONGO_URI`              | MongoDB Atlas connection string (`CruzAidDB`)     |
| `TWILIO_AUTH_TOKEN`      | Verifies each `/sms` request came from Twilio. Unset skips the check (dev only). |
| `RATELIMIT_STORAGE_URI`  | Optional. Redis URL to share rate limits across workers. Defaults to in-memory. |

## Data model

Resources live in the `resources` collection of the `CruzAidDB` database. Each document has `name`, `phone`, `address`, and a `tags` list. Re-running `setup_data.py` reseeds the collection after wiping it. One invariant holds the whole thing together: every category the classifier can return must have at least one resource tagged for it, or a user silently falls through to the default reply. The test suite checks exactly that.

## Tests and CI

```bash
poetry run pytest
```

The tests confirm that every triage category maps to a seeded resource and that no resource is missing a name, phone, or tags. GitHub Actions runs them on every push and pull request ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Security

Every request to `/sms` is verified against Twilio's signature. Twilio signs each webhook with the account auth token; the app recomputes that signature from the request URL and form body and rejects anything that doesn't match with a 403. This stops a stranger who finds the URL from draining the LLM and database quota. The check is skipped when `TWILIO_AUTH_TOKEN` is unset so local development and tests still run, which means a production deploy has to set the token to be protected.

## What I would add next

- Distance ranking instead of returning the first three matches, so "nearest" is literal rather than arbitrary.
- A short follow-up question when a message is ambiguous, instead of guessing a category.

## Files

| File              | Role                                     |
|-------------------|------------------------------------------|
| `app.py`          | Flask server, `/sms` webhook, triage     |
| `setup_data.py`   | Seeds health resources into MongoDB      |
| `test_cruzaid.py` | Data and routing checks                  |
| `Dockerfile`      | Container build, serves via gunicorn     |

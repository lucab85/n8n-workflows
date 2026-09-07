#!/usr/bin/env python3
"""
Garmin -> Claude daily pull.

Logs into Garmin Connect with python-garminconnect and pulls your data DIRECTLY
(no manual export, no email) - activities, sleep, daily stats, HRV, VO2 max,
race predictors and body-composition off the Index scale - then upserts it into
Supabase so your dashboard / Claude can read it. Run it once a day on a schedule.

This is Route B in the build guide: the thing that turns the pipeline into a live feed.

USAGE
  One-time login (do this first - handles MFA, caches a token for ~a year):
      python garmin_daily_pull.py --login

  Daily pull (yesterday + today) and write to Supabase:
      python garmin_daily_pull.py

  Backfill N days:
      python garmin_daily_pull.py --days 30

  Pull and PRINT a summary without writing anything (safe test):
      python garmin_daily_pull.py --dry-run --days 3

ENV (.env or shell)
  GARMIN_EMAIL, GARMIN_PASSWORD            your Garmin Connect login
  GARMIN_TOKENSTORE                        token cache dir (default ~/.garminconnect)
  GARMIN_SUPABASE_URL                      https://<ref>.supabase.co
  GARMIN_SUPABASE_SERVICE_KEY              service_role key (server-side only)

Notes
  - Garmin pulls from its CLOUD, not the watch. Sync your watch to the Garmin
    Connect app (your phone does this automatically) or there's nothing new to pull.
  - The first login may ask for an MFA code. After that the cached token is reused
    headless, so the daily schedule needs no interaction.
"""
import os, sys, argparse, datetime, json, time, traceback

TOKENSTORE = os.path.expanduser(os.environ.get("GARMIN_TOKENSTORE", "~/.garminconnect"))
STAMP = os.path.join(TOKENSTORE, ".last_success")   # wall-clock of the last good write (for --since-hours)


# ----------------------------------------------------------------------------- auth
def _mfa_prompt():
    return input("Garmin MFA code (check your email/authenticator): ").strip()


def _tune_timeout(g, seconds=30):
    """Give slow Garmin endpoints more room before timing out (best-effort, version-safe)."""
    try:
        g.garth.timeout = max(getattr(g.garth, "timeout", 0) or 0, seconds)
    except Exception:
        pass
    return g


def connect(force_login=False):
    """Return a logged-in Garmin client, resuming a cached token when possible."""
    from garminconnect import Garmin
    if not force_login:
        try:
            g = Garmin()
            g.login(TOKENSTORE)            # resume from cached token (loads from path)
            return _tune_timeout(g)
        except Exception:
            pass                            # fall through to full login
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not (email and password):
        sys.exit("GARMIN_EMAIL / GARMIN_PASSWORD not set - add them to .env, then run --login once.")
    os.makedirs(TOKENSTORE, exist_ok=True)
    g = Garmin(email=email, password=password, prompt_mfa=_mfa_prompt)
    g.login(TOKENSTORE)                     # fresh login; garminconnect persists the token to TOKENSTORE
    print(f"[auth] logged in + token cached to {TOKENSTORE}")
    return _tune_timeout(g)


def connect_with_retry(force_login=False, attempts=3):
    """connect(), but ride out a transient network blip on the initial login."""
    for n in range(1, attempts + 1):
        try:
            return connect(force_login=force_login)
        except SystemExit:
            raise                           # missing creds etc. - don't retry
        except Exception as e:
            if n == attempts:
                raise
            wait = n * 3
            print(f"[retry] login/connect failed (attempt {n}/{attempts}): {e} - retrying in {wait}s")
            time.sleep(wait)


# ----------------------------------------------------------------------------- helpers
def _safe(fn, *a, default=None, label=""):
    try:
        return fn(*a)
    except Exception as e:
        print(f"  [warn] {label or fn.__name__} failed: {e}")
        return default


def _i(x):
    """Coerce to int for integer columns (Garmin returns floats like 123.0)."""
    try:
        return int(round(float(x))) if x is not None else None
    except (TypeError, ValueError):
        return None


def _ms_to_iso(ms):
    try:
        # timezone-aware UTC (utcfromtimestamp is deprecated); strip tz so the
        # stored string stays the exact same "...Z" format the DB already holds.
        dt = datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)
        return dt.replace(tzinfo=None).isoformat() + "Z"
    except (TypeError, ValueError, OSError):
        return None


def _recent_success(hours):
    """True if a successful write finished < `hours` ago (so we can skip a re-pull)."""
    if not hours or hours <= 0:
        return False
    try:
        age_h = (time.time() - float(open(STAMP).read().strip())) / 3600
        return age_h < hours
    except Exception:
        return False


def _mark_success():
    try:
        os.makedirs(TOKENSTORE, exist_ok=True)
        with open(STAMP, "w") as f:
            f.write(str(time.time()))
    except Exception:
        pass


def daterange(days):
    today = datetime.date.today()
    return [today - datetime.timedelta(d) for d in range(days - 1, -1, -1)]


# ----------------------------------------------------------------------------- pull
def pull(g, days):
    """Pull the last `days` days into rows that match the live Supabase schema."""
    start = (datetime.date.today() - datetime.timedelta(days - 1)).isoformat()
    end = datetime.date.today().isoformat()
    out = {"activities": [], "sleep": [], "daily": [], "weigh_ins": [], "hrv": [], "race": []}

    # activities -> garmin_activities
    for a in (_safe(g.get_activities_by_date, start, end, label="activities") or []):
        out["activities"].append({
            "activity_id": a.get("activityId"),
            "activity_date": (a.get("startTimeLocal") or "")[:10] or None,
            "started_at": a.get("startTimeLocal"),
            "activity_type": (a.get("activityType") or {}).get("typeKey"),
            "name": a.get("activityName"),
            "duration_s": _i(a.get("duration")),
            "distance_m": _i(a.get("distance")),
            "avg_hr": _i(a.get("averageHR")),
            "max_hr": _i(a.get("maxHR")),
            "calories": _i(a.get("calories")),
            "elevation_gain_m": _i(a.get("elevationGain")),
            "aerobic_te": a.get("aerobicTrainingEffect"),
            "anaerobic_te": a.get("anaerobicTrainingEffect"),
            "training_load": a.get("activityTrainingLoad"),
            "moderate_min": _i(a.get("moderateIntensityMinutes")),
            "vigorous_min": _i(a.get("vigorousIntensityMinutes")),
        })

    # per-day: sleep -> garmin_sleep, summary -> garmin_daily_summary, hrv (pulled, no table yet)
    for d in daterange(days):
        ds = d.isoformat()

        sl = _safe(g.get_sleep_data, ds, label="sleep") or {}
        dto = sl.get("dailySleepDTO") or {}
        if dto.get("sleepTimeSeconds") is not None:
            out["sleep"].append({
                "sleep_date": ds,
                "started_at": _ms_to_iso(dto.get("sleepStartTimestampGMT")),
                "ended_at": _ms_to_iso(dto.get("sleepEndTimestampGMT")),
                "total_sleep_s": dto.get("sleepTimeSeconds"),
                "deep_s": dto.get("deepSleepSeconds"),
                "light_s": dto.get("lightSleepSeconds"),
                "rem_s": dto.get("remSleepSeconds"),
                "awake_s": dto.get("awakeSleepSeconds"),
                "sleep_score": _i((dto.get("sleepScores") or {}).get("overall", {}).get("value")),
                "avg_respiration": dto.get("averageRespirationValue"),
                "avg_stress": _i(dto.get("avgSleepStress")),
            })

        summ = _safe(g.get_user_summary, ds, label="daily") or {}
        if summ:
            out["daily"].append({
                "summary_date": ds,
                "total_steps": _i(summ.get("totalSteps")),
                "step_goal": _i(summ.get("dailyStepGoal")),
                "distance_m": _i(summ.get("totalDistanceMeters")),
                "total_calories": _i(summ.get("totalKilocalories")),
                "active_calories": _i(summ.get("activeKilocalories")),
                "resting_hr": _i(summ.get("restingHeartRate")),
                "min_hr": _i(summ.get("minHeartRate")),
                "max_hr": _i(summ.get("maxHeartRate")),
                "moderate_min": _i(summ.get("moderateIntensityMinutes")),
                "vigorous_min": _i(summ.get("vigorousIntensityMinutes")),
                "floors_ascended": _i(summ.get("floorsAscended")),
            })

        hrv = _safe(g.get_hrv_data, ds, label="hrv") or {}
        hs = hrv.get("hrvSummary") or {}
        if hs.get("lastNightAvg") is not None:
            out["hrv"].append({"date": ds, "hrv_avg": hs.get("lastNightAvg"), "hrv_status": hs.get("status")})

    # body-composition / weigh-ins (THE EDGE) -> garmin_weigh_ins
    bc = _safe(g.get_body_composition, start, end, label="body_composition") or {}
    for w in (bc.get("dateWeightList") or []):
        measured = _ms_to_iso(w.get("date"))
        out["weigh_ins"].append({
            "measured_at": measured,
            "measured_date": (measured or "")[:10] or None,
            "weight_kg": (w.get("weight") or 0) / 1000 if w.get("weight") else None,
            "bmi": w.get("bmi"),
            "body_fat_pct": w.get("bodyFat"),
            "body_water_pct": w.get("bodyWater"),
            "muscle_mass_kg": (w.get("muscleMass") or 0) / 1000 if w.get("muscleMass") else None,
            "bone_mass_kg": (w.get("boneMass") or 0) / 1000 if w.get("boneMass") else None,
            "source": w.get("sourceType") or "INDEX_SCALE",
        })

    # race predictors (pulled for the summary; no table yet)
    rp = _safe(g.get_race_predictions, label="race_predictions") or {}
    if rp:
        out["race"].append({"date": end, "time_5k_s": rp.get("time5K"), "time_10k_s": rp.get("time10K"),
                            "time_half_s": rp.get("timeHalfMarathon"), "time_full_s": rp.get("timeMarathon")})
    return out


# ----------------------------------------------------------------------------- store
# dataset -> (live table, on-conflict column). Datasets not listed are pulled but not written
# (no destination table yet: garmin_hrv / garmin_race_predictions - add them to store HRV + race).
TABLE_KEYS = {
    "activities": ("garmin_activities", "activity_id"),
    "sleep":      ("garmin_sleep", "sleep_date"),
    "daily":      ("garmin_daily_summary", "summary_date"),
    "weigh_ins":  ("garmin_weigh_ins", "measured_at"),
    "hrv":        ("garmin_hrv", "date"),
    "race":       ("garmin_race_predictions", "date"),
}


def upsert(dataset, rows):
    if dataset not in TABLE_KEYS:
        return
    import requests
    url = os.environ.get("GARMIN_SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("GARMIN_SUPABASE_SERVICE_KEY", "")
    if not (url and key):
        print("  [skip] GARMIN_SUPABASE_URL / _SERVICE_KEY not set - not writing.")
        return
    table, conflict = TABLE_KEYS[dataset]
    rows = [r for r in rows if r.get(conflict) is not None]
    if not rows:
        return
    r = requests.post(
        f"{url}/rest/v1/{table}?on_conflict={conflict}",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps(rows, default=str), timeout=60)
    status = "ok" if r.status_code < 300 else f"ERR {r.status_code}: {r.text[:200]}"
    print(f"  [{table}] upsert {len(rows)} rows -> {status}")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Garmin -> Supabase daily pull")
    ap.add_argument("--login", action="store_true", help="force interactive login (handles MFA) + cache token")
    ap.add_argument("--days", type=int, default=2, help="days back to pull (default 2)")
    ap.add_argument("--dry-run", action="store_true", help="pull + print summary, do not write to Supabase")
    ap.add_argument("--since-hours", type=float, default=0,
                    help="skip the pull if a successful one finished within this many hours "
                         "(lets you trigger on every startup without re-hitting Garmin; default 0 = always run)")
    args = ap.parse_args()

    # load .env if present (no dependency required) - works standalone or inside a monorepo
    for envp in (os.path.join(os.getcwd(), ".env"),
                 os.path.join(os.path.dirname(__file__), ".env"),
                 os.path.join(os.path.dirname(__file__), "..", "..", ".env")):
        if os.path.exists(envp):
            for line in open(envp, encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line and line.split("=", 1)[0].isupper():
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v.strip())
            break

    if not args.login and not args.dry_run and _recent_success(args.since_hours):
        print(f"[skip] a successful pull finished less than {args.since_hours:g}h ago - data is fresh, nothing to do.")
        return

    g = connect_with_retry(force_login=args.login)
    if args.login:
        who = _safe(g.get_full_name, label="get_full_name") if hasattr(g, "get_full_name") else None
        print(f"[auth] ready{(' as ' + who) if who else ''}. Token cached - daily pulls run headless now.")
        return

    data = pull(g, args.days)
    print("\n[pull summary]  " + "  ".join(f"{k}={len(v)}" for k, v in data.items()))
    if data["weigh_ins"]:
        w = data["weigh_ins"][-1]
        print(f"  latest weigh-in: {w['weight_kg']}kg  fat {w['body_fat_pct']}%  muscle {w['muscle_mass_kg']}kg")

    if args.dry_run:
        print("\n[dry-run] not writing. Sample rows:")
        for k, v in data.items():
            if v:
                print(f"  {k}: {json.dumps(v[0], default=str)[:220]}")
        return

    print("\n[write]")
    for k, rows in data.items():
        try:
            upsert(k, rows)
        except Exception as e:
            print(f"  [error] {k}: {e}")
    _mark_success()   # stamp so --since-hours can skip a redundant re-pull on the next startup
    print("[done]")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)

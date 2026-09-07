# The prompt pack

18 copy-paste prompts that turn a wall of Garmin metrics into a coach's read.

**How to use them:** swap the `[bracketed]` bits for your real numbers — or, once the daily
pull is running (see the README), just tell Claude *"read the last 14 days from my Supabase
`garmin_*` tables"* and let it pull the data itself. Then push back on the answer: "explain
that", "give me plan B". A coach is a conversation, not a one-shot.

> Not medical advice. For pain, injury or health concerns, see a professional.

---

## Read a session — *what just happened*

**01 · Read this session like a coach**
```
Here's my session from today: [paste splits, pace, heart rate, RPE].
Break it down like a coach, not a spreadsheet. Was this mostly aerobic or did I
redline it? What did it cost me, and what should tomorrow be?
```

**02 · Was I in the right zone?**
```
Here's my heart rate across [session]: [paste]. I was aiming for [zone/effort].
Was I actually there or drifting? Where did I lose it, and how do I pace it better
next time?
```

---

## Recovery & readiness — *should I go hard today*

**03 · Am I overtraining?**
```
My last 7 days: resting HR [..], HRV [..], sleep [..], training load [..].
Am I absorbing the work or digging a hole? One word first, then explain what
you're reading.
```

**04 · Hard session or swap it?**
```
Last 5 nights of sleep + HRV: [paste]. I've got [the hard session] planned today.
Green light, or swap it? Give me the call and a plan B.
```

**05 · When's my next deload?**
```
Here's my rolling training load and HRV trend: [paste].
When's my deload actually due, and what should it look like — full rest or just
lighter?
```

---

## The edge · body-comp — *the half nobody wires in*

**06 · Is my muscle holding?**
```
Body-comp over [period]: weight [..], body fat % [..], muscle mass [..].
Is my muscle holding while fat drops, or am I losing both? What does that say about
my deficit and training right now?
```

**07 · Is my intake matching the work?**
```
This week's training load: [paste]. My weight trend + body-comp: [paste]. I'm eating
roughly [intake].
Am I fuelling the work or under-eating it? What would you change to hold muscle
through this block?
```

---

## Plan & race — *what's next*

**08 · Build me the week**
```
Goal: [e.g. sub-45 10k in 8 weeks]. Current fitness: [VO2 max, recent long run,
weekly volume]. I train [days].
Write next week's sessions. Keep it to what my recovery can actually take.
```

**09 · Is my race predictor honest?**
```
Garmin predicts [time] for my [distance]. My actual recent sessions: [paste].
Realistic or optimistic? What pace should I actually go out at?
```

**10 · Build my taper**
```
Race in [X days]: [distance]. My last 3 weeks: [paste].
Build my taper — volume, intensity, and exactly what to do the 48 hours before.
```

**11 · Is the cross-training helping?**
```
My swim + run split this month: [paste].
Is the swimming helping my running or just adding fatigue? How should I balance them
for [goal]?
```

---

## Strength — *off the gym sessions*

**12 · Push or deload the lift?**
```
Last 4 weeks of [lift]: [sets x reps x load].
Estimate my current 1-rep max, and tell me straight — push next week or deload?
```

**13 · Is lifting stealing my legs?**
```
Here's my lifting + running this week: [paste].
Is the strength work leaving me flat for the key runs? How do I order the week so
both get what they need?
```

---

## Progress & patterns — *the long game*

**14 · This week vs last month**
```
Compare this week's training to my 4-week average: [paste both].
Trending up, holding, or quietly overreaching? Call it, and tell me what to change.
```

**15 · Am I actually consistent?**
```
My last 8 weeks of volume + sessions: [paste].
Consistent, or stop-start? Show me the pattern that's costing me and the one habit
that'd fix it.
```

**16 · 3 months on — what's changed?**
```
Compare my fitness now to 3 months ago: [VO2 max, race predictors, body-comp].
Where have I actually improved, where have I stalled, and what's the next lever to pull?
```

**17 · Read this niggle**
```
I've had [niggle] for [days]. Recent load + what aggravates it: [paste].
Train through, modify, or rest? Give me a 3-day plan. (Not medical advice — flag if
I should see someone.)
```

---

## Automate it — *the standing coach*

**18 · The morning coach (system prompt)**

Use this as the system prompt for the scheduled morning job (see `n8n/` for the workflow).
It runs after your overnight recovery syncs and the daily pull has landed.
```
You are my coach. Every morning you get my overnight recovery (sleep, HRV, resting
HR) and yesterday's session. Read how I actually pulled up and rewrite today's plan
for it. Be decisive: one clear session, one line on why. If I'm cooked, say so and
back it off.
```

---

Built by [aaronautomates](https://github.com/aaronparton2-sketch). MIT — do what you like with it.

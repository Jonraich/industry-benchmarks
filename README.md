# Industry Financial Benchmarks Tool

A self-serve web tool that generates a state/industry financial benchmark
report on demand — similar in spirit to a BizBuySell-style benchmark report,
but built independently from public U.S. Census Bureau data plus a
transparently-labeled financial model. No third-party proprietary content is
used or reproduced anywhere in this tool.

## What's real vs. modeled

**Real, sourced from the Census Bureau (live API calls):**
- Total firms, total revenue, employment, and payroll for the selected NAICS
  code + state (2022 Economic Census — the most recent year with real
  revenue data by industry/state; Census only publishes revenue every 5
  years, in years ending 2 and 7)
- Latest-year establishment/employment/payroll snapshot (County Business
  Patterns, published annually) — used to scale revenue forward

**Modeled (clearly labeled in the UI with a "Modeled" tag):**
- Income statement detail: cost of sales, officer compensation, wages,
  rent, D&A, etc. as % of revenue
- SDE (Seller's Discretionary Earnings) and EBITDA
- Balance sheet structure (% of total assets)
- Financial ratios (current ratio, quick ratio, ROA, turnover ratios,
  capital intensity, etc.)
- The 5-year trend line and revenue-size-class breakdown

The modeled figures come from industry-typical margin/structure profiles
per broad NAICS sector, defined in `backend/naics_sectors.py`. These are
reasonable, general-knowledge assumptions (informed by the kind of
public benchmarking data widely cited in small-business finance — e.g.
NYU Stern/Damodaran industry margins, IRS SOI corporate ratios) — **not**
measured figures, and not derived from any licensed/proprietary dataset.
Every report displays a methodology note saying exactly this.

## Setup

```bash
cd backend
pip install -r requirements.txt
export CENSUS_API_KEY=your_key_here   # https://api.census.gov/data/key_signup.html
python app.py
```

Open http://localhost:5000 — pick a state, search an industry, click
Generate Report.

## Notes on the Census API quirks discovered while building this

- The 2022 Economic Census (`ecnbasic` dataset) uses **NAICS2022** variable
  names (`NAICS2022`, `NAICS2022_LABEL`).
- County Business Patterns for 2023 still uses **NAICS2017** variable names
  (`NAICS2017`, `NAICS2017_LABEL`). Census hadn't migrated CBP to the 2022
  NAICS vintage as of the 2023 release. If you pull a newer CBP year and it
  errors on `NAICS2017`, check `.../cbp/variables.html` for that year to see
  which vintage it expects and update `census_client.fetch_cbp` accordingly.
- Use the `FIRM` variable for firm counts (distinct legal entities), not
  `ESTAB` (physical establishment locations) — they differ meaningfully.
  This tool uses `FIRM`.
- Small/rare NAICS + state combinations sometimes return no row at all —
  Census suppresses data to protect individual firm confidentiality. The
  tool surfaces a clear error message when this happens and suggests
  trying a broader code or larger state.
- All Census Data API calls now require a (free) API key.

## Extending this

- **NAICS list**: `backend/naics_codes.py` has a curated list of ~90 common
  industries. Swap in the Census Bureau's full NAICS reference file if you
  want the complete code set.
- **Sector profiles**: `backend/naics_sectors.py` covers the ~15 broad
  2-digit NAICS sectors. Refine these (or replace with a licensed ratio
  dataset if you acquire one) to improve accuracy.
- **Size-class breakdown**: currently modeled from the average revenue
  figure. Census's SUSB dataset has real size-class data, but bucketed by
  *employee* count rather than revenue — integrating it would improve
  accuracy over the current multiplier-based estimate.
- **PDF export**: the frontend is a single self-contained HTML page; adding
  a "download as PDF" button (e.g. via `window.print()` with print CSS, or
  a server-side PDF library) would round this out for client-facing use.

## Deployment (get a real public link, no local server needed)

This app is set up to deploy for free on [Render](https://render.com) —
no credit card required. Render builds from a GitHub repo, so you'll need a
free GitHub account too. Steps (all in the browser, no terminal required):

1. **Put the code on GitHub.**
   - Go to github.com, sign in (or create a free account), click the **+**
     in the top right → **New repository**. Name it e.g. `industry-benchmarks`,
     leave it public or private, click **Create repository**.
   - On the new repo's page, click **uploading an existing file**, then drag
     the whole `industry-benchmarks` folder (with `backend/`, `frontend/`,
     `render.yaml`, etc. inside it) into the upload box. Commit the files.

2. **Create a Render account and connect GitHub.**
   - Go to render.com → **Get Started** → sign up with GitHub (this lets
     Render see your repos without you copying any keys around).

3. **Create the web service.**
   - In the Render dashboard, click **New** → **Web Service**.
   - Pick the `industry-benchmarks` repo you just created.
   - Render should detect it's a Python app. Set these fields if it doesn't
     fill them in automatically:
     - **Root Directory:** `backend`
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:app`
     - **Instance Type:** Free
   - Under **Environment Variables**, add one:
     - Key: `CENSUS_API_KEY`, Value: your Census API key
   - Click **Create Web Service**.

4. **Wait for the build**, then open the `https://industry-benchmarks-xxxx.onrender.com`
   URL Render gives you — that's your live tool, shareable with anyone.

Note: on Render's free tier, the app "sleeps" after 15 minutes of no
traffic and takes ~30-60 seconds to wake back up on the next visit. That's
normal for the free tier, not a bug.

If you'd rather run it locally instead of deploying, see the **Setup**
section above.

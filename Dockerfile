# AGENTIC-ARBITER, one container that serves the whole product.
#
# WHY ONE CONTAINER AND NOT TWO. The page and the app both call the live agent with a RELATIVE url,
# `fetch('api/live/<site>')`. Same origin or it 404s. serve_live.py already serves the artefact folder
# statically AND answers /api/*, so one process is the whole deployment and no code changes to support
# it. Splitting the static files onto a CDN would mean inventing a configurable API base and adding
# CORS, which is two new ways for the live agent to break.
#
# WHAT ENDS UP INSIDE, and why it is large. About 890 MB:
#   AGENTIC-ARBITER/demo        the artefacts a judge reads, 250 sites, plus the built app at /app/
#   testing/results/fixtures    196 MB of SAVED FortyGuard responses. Not test data: this is what the
#                               agent perceives from in REPLAY, and it is why the demo runs with zero
#                               API calls. Removing it would break the product, not the tests.
#   AGENTIC-ARBITER/src         24 modules, including the local physics package
#
# NO GPU, DELIBERATELY. nvidia-warp solved the plume fields at build time and they ship as data. The
# server replays them and never solves, so this runs on the smallest CPU instance a host offers.

FROM python:3.12-slim

# Nothing to compile: numpy and psychrolib both ship wheels for this image.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Dependencies first, so a code change does not reinstall them.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 🔴 THE KEY IS NOT IN THIS IMAGE AND MUST NEVER BE. It arrives as the FORTYGUARD_API_KEY environment
# variable, which testing/common.py:load_key() reads first, before falling back to a local .env that
# does not exist here. .env is gitignored, so it is not in the build context either.
#
# THE LIVE AGENT IS OPEN, WHICH IS THE OWNER'S DECISION. serve_live.py has no authentication: with
# --allow-paid, anybody who reaches this URL can request a live run. MAX_LIVE_CALLS is the only
# ceiling, counted per day, and each call costs 4,220 credits.
ENV PORT=8000 \
    MAX_LIVE_CALLS=48

EXPOSE 8000

# --host 0.0.0.0 because the default 127.0.0.1 is unreachable from outside a container.
# Shell form on purpose: $PORT and $MAX_LIVE_CALLS are supplied by the host at run time.
CMD python AGENTIC-ARBITER/src/serve_live.py \
      --allow-paid \
      --host 0.0.0.0 \
      --port "$PORT" \
      --max-live-calls "$MAX_LIVE_CALLS"

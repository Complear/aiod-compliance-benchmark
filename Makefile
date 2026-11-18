PY ?= python3

test:
	$(PY) -m unittest discover -s tests -t .

dataset:
	$(PY) -m cdb.build_dataset --lint-against $(HOME)/jev-lab/data/mdr_aiact

# Engine self-check: gold facts in, must score 1.0 / 1.0 / 0.0.
gold:
	$(PY) -m cdb.run --reader gold --split all --out results/gold

# Needs a reader endpoint (READER_URL), e.g. `make serve` in another shell.
run:
	$(PY) -m cdb.run --reader llm --split test --out results/test
	$(PY) -m cdb.run --reader llm --split fresh --out results/fresh

# Track B, drafting with citations; needs a reader endpoint like `run`.
draft:
	$(PY) -m cdb.draft --split test --out results/test-draft
	$(PY) -m cdb.draft --split fresh --out results/fresh-draft

# Track C: the same cases through AIoD's TAI Scan; needs TAI_USER and TAI_PASS (an AIoD account).
# About 5 requests a minute: ~40 min for both splits; answers are cached, so a re-run resumes.
taiscan:
	$(PY) -m cdb.taiscan --split test --out results/test-taiscan
	$(PY) -m cdb.taiscan --split fresh --out results/fresh-taiscan

# All results in one page: results/SUMMARY.md
summary:
	$(PY) -m cdb.summary

# Everything: tracks A and B need `make serve` running; track C runs only when TAI_USER is set.
all: gold run draft
	@if [ -n "$$TAI_USER" ]; then $(MAKE) taiscan; else echo "TAI_USER not set: skipping TAI Scan"; fi
	$(MAKE) summary

scorecard:
	$(PY) collector/collector.py --evaluation results/test/evaluation.json \
	  --subject schema/examples/subject.example.json --mapping collector/mapping.json \
	  --out results/test/scorecard.json

MODEL = models/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf
$(MODEL):
	mkdir -p models && curl -fL -o $@ https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-GGUF/resolve/main/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf

serve: $(MODEL)
	llama-server -m $(MODEL) --alias ministral-3-3b -c 8192 --host 127.0.0.1 --port 8080 --jinja

images: $(MODEL)
	docker build -f docker/benchmark.Dockerfile -t compliance-draft-benchmark:0.1.0 .
	docker build -f docker/reader.Dockerfile -t compliance-draft-reader:0.1.0 .

.PHONY: test dataset gold run draft taiscan summary all scorecard serve images

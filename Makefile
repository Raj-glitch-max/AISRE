.PHONY: help reproduce eval heldout test check victim backend clean

help: ## show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

reproduce: ## re-derive every headline claim in README.md (no API key, no cloud)
	@python3 scripts/reproduce.py

eval: ## measure the current checker against the designed mutation classes
	@cd eval && python3 run_faithfulness_eval.py current

heldout: ## measure the current checker against held-out classes it was not designed for
	@cd eval && python3 -c "import sys; sys.path[:0]=['../backend','.']; \
	from faithfulness_eval import check_faithfulness as c; from heldout import generate_heldout as g; \
	cases=g(); caught=sum(1 for x in cases if c(x['rca'],x['transcript'])['flagged']); \
	print(f'held-out recall: {caught/len(cases):.1%} ({caught}/{len(cases)})')"

check: ## verify every module imports cleanly
	@cd backend && python3 -c "import main, agent, poller, remediation, tools, database, faithfulness_eval; print('all modules import')"

victim: ## build and run the victim service locally
	@cd victim-app && docker build -t victim-app . && \
	docker rm -f victim-app 2>/dev/null; \
	docker run -d -p 8000:8000 --name victim-app victim-app && echo "victim-app on :8000"

backend: ## run the backend locally on :9000
	@cd backend && uvicorn main:app --reload --port 9000

clean: ## remove generated eval output
	@rm -rf eval/results/*_current.json __pycache__ */__pycache__

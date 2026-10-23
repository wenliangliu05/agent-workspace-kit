.PHONY: help test lint check demo

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

test:            ## run the test suite
	python3 -m unittest discover -s tests -v

lint:            ## static checks (needs: pip install ruff)
	python3 -m ruff check .

check:           ## validate the shipped workspace (index <-> disk)
	python3 assets/tools/ws.py check

demo:            ## print a handoff for the bundled demo project
	python3 assets/tools/ws.py handoff demo-api

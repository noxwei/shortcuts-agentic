CHERRI := $(shell command -v cherri 2>/dev/null || echo ~/go/bin/cherri)
SHORTCUTS_DIR := shortcuts
SOURCES := $(wildcard $(SHORTCUTS_DIR)/*.cherri)

.PHONY: shortcuts dev test clean

## Compile and sign all .cherri files
shortcuts: $(SOURCES)
	@for src in $(SOURCES); do \
		echo "compiling $$src ..."; \
		$(CHERRI) $$src; \
	done
	@echo "done — compiled $$(ls $(SHORTCUTS_DIR)/*.shortcut 2>/dev/null | wc -l | tr -d ' ') shortcut(s)"

## Run the FastAPI dev server on port 8200
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload

## Run pytest
test:
	python -m pytest -v

## Remove compiled .shortcut files
clean:
	rm -f $(SHORTCUTS_DIR)/*.shortcut

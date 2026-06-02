PREFIX      ?= $(HOME)/.local
BINDIR      ?= $(PREFIX)/bin
PROFILE_DIR ?= $(HOME)/.config/tmux/profiles

PROFILES := $(wildcard profiles/*.toml)
SRC      := $(wildcard src/*.py)

.PHONY: help build deploy install install-profiles install-all uninstall clean \
	lint typecheck check

help:
	@echo "tmx — tmux session manager"
	@echo
	@echo "Targets:"
	@echo "  build             build the tmx executable from src/ (zipapp)"
	@echo "  deploy            build + install tmx to BINDIR ($(BINDIR))"
	@echo "  install           install tmx to BINDIR (builds first if needed)"
	@echo "  install-profiles  copy the example profile(s) to PROFILE_DIR"
	@echo "                    ($(PROFILE_DIR)) — overwrites existing files"
	@echo "  install-all       install + install-profiles"
	@echo "  uninstall         remove the tmx script from BINDIR"
	@echo "  clean             remove the built tmx executable"
	@echo
	@echo "Development (needs uv: https://docs.astral.sh/uv/):"
	@echo "  lint              ruff lint over src/"
	@echo "  typecheck         mypy + basedpyright over src/"
	@echo "  check             lint + typecheck + build (the CI gate)"
	@echo
	@echo "Override paths, e.g.: make install PREFIX=/usr/local"

# Bundle the src/ package into a single self-contained executable. zipapp
# prepends the shebang and marks the file executable; --compress keeps it small.
build: tmx

tmx: $(SRC)
	@rm -rf src/__pycache__ src/.mypy_cache src/.ruff_cache
	python3 -m zipapp src -p '/usr/bin/env python3' --compress -o $@
	@echo "Built tmx ($$(wc -c < tmx) bytes)"

# Build the executable, then install it.
deploy: build install

install: tmx
	install -Dm755 tmx $(BINDIR)/tmx
	@echo "Installed tmx -> $(BINDIR)/tmx"
	@case ":$$PATH:" in *":$(BINDIR):"*) ;; \
		*) echo "Note: $(BINDIR) is not on your PATH.";; esac

install-profiles:
	@mkdir -p $(PROFILE_DIR)
	@for f in $(PROFILES); do \
		install -m644 "$$f" "$(PROFILE_DIR)/"; \
		echo "Installed profile -> $(PROFILE_DIR)/$$(basename $$f)"; \
	done

install-all: install install-profiles

uninstall:
	rm -f $(BINDIR)/tmx
	@echo "Removed $(BINDIR)/tmx (profiles in $(PROFILE_DIR) left untouched)"

clean:
	rm -f tmx
	@rm -rf src/__pycache__ src/.mypy_cache src/.ruff_cache
	@echo "Removed built tmx"

# Dev-only quality gate. tmx itself stays stdlib-only at runtime; these tools are
# fetched on demand via uv (uvx), so nothing is added to what users install.
lint:
	uvx ruff check src/

typecheck:
	uvx mypy src/
	uvx basedpyright src/

# The same gate CI runs: lint, type-check, and prove the zipapp still builds.
check: lint typecheck build
	@echo "All checks passed."

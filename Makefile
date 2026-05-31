PREFIX      ?= $(HOME)/.local
BINDIR      ?= $(PREFIX)/bin
PROFILE_DIR ?= $(HOME)/.config/tmux/profiles

PROFILES := $(wildcard profiles/*.toml)

.PHONY: help install install-profiles install-all uninstall

help:
	@echo "tmx — tmux session manager"
	@echo
	@echo "Targets:"
	@echo "  install           install the tmx script to BINDIR ($(BINDIR))"
	@echo "  install-profiles  copy the example profile(s) to PROFILE_DIR"
	@echo "                    ($(PROFILE_DIR)) — overwrites existing files"
	@echo "  install-all       install + install-profiles"
	@echo "  uninstall         remove the tmx script from BINDIR"
	@echo
	@echo "Override paths, e.g.: make install PREFIX=/usr/local"

install:
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

SHELL := /bin/bash
PYTHON ?= $(shell which python3 2>/dev/null || which python 2>/dev/null || echo python3)

.PHONY: all branch publish build clean help

all: help

help:
	@echo "Usage:"
	@echo "  make branch [name=<branch_name>]"
	@echo "  make publish [repo=pypi|testpypi] [token=<pypi_token>]"
	@echo "  make build"
	@echo "  make clean"

clean:
	@rm -rf dist build omilang.egg-info

build: clean
	@$(PYTHON) -m pip install --upgrade build twine
	@$(PYTHON) -m build
	@$(PYTHON) -m twine check dist/*

branch:
	@BRANCH="$(name)"; \
	if [ -z "$$BRANCH" ]; then \
		BRANCH="$(branch)"; \
	fi; \
	if [ -z "$$BRANCH" ]; then \
		read -p "Введите имя ветки: " BRANCH; \
	fi; \
	if [ -z "$$BRANCH" ]; then \
		echo "Имя ветки не может быть пустым."; \
		exit 1; \
	fi; \
	echo "Создаю/переключаю ветку в корне репозитория..."; \
	if git checkout -b "$$BRANCH" 2>/dev/null; then \
		echo "Ветка \"$$BRANCH\" успешно создана и переключена в корне."; \
	elif git checkout "$$BRANCH" 2>/dev/null; then \
		echo "Переключился на существующую ветку \"$$BRANCH\" в корне."; \
	else \
		echo "Не удалось создать/переключиться на ветку \"$$BRANCH\" в корне."; \
	fi; \
	for d in docs vscode-extension; do \
		if [ -d "$$d" ]; then \
			if git -C "$$d" rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
				echo "Создаю/переключаю ветку в $$d..."; \
				if git -C "$$d" checkout -b "$$BRANCH" 2>/dev/null; then \
					echo "Ветка \"$$BRANCH\" успешно создана в $$d."; \
				elif git -C "$$d" checkout "$$BRANCH" 2>/dev/null; then \
					echo "Переключился на существующую ветку \"$$BRANCH\" в $$d."; \
				else \
					echo "Не удалось создать/переключиться на ветку \"$$BRANCH\" в $$d."; \
				fi; \
			else \
				echo "Папка $$d не является git-репозиторием, пропуск."; \
			fi; \
		else \
			echo "Папка $$d не найдена, пропуск."; \
		fi; \
	done; \
	echo "Готово."

publish:
	@TOKEN="$(token)"; \
	if [ -z "$$TOKEN" ]; then \
		TOKEN="$$PYPI_TOKEN"; \
	fi; \
	if [ -z "$$TOKEN" ]; then \
		echo "Error: PYPI_TOKEN environment variable is not set."; \
		echo "Set it with: export PYPI_TOKEN=pypi-... or pass token=pypi-..."; \
		exit 1; \
	fi; \
	REPO="$(repo)"; \
	if [ -z "$$REPO" ]; then \
		echo "Repository options:"; \
		echo "  1) pypi      (production)"; \
		echo "  2) testpypi  (test registry)"; \
		read -p "Select repository [1/2, default 1]: " REPO_CHOICE; \
		if [ "$$REPO_CHOICE" = "2" ]; then \
			REPO="testpypi"; \
		else \
			REPO="pypi"; \
		fi; \
	fi; \
	rm -rf dist build omilang.egg-info; \
	echo "Cleaning previous build artifacts..."; \
	echo "Installing/Updating build tools..."; \
	$(PYTHON) -m pip install --upgrade build twine || exit 1; \
	echo "Building package..."; \
	$(PYTHON) -m build || exit 1; \
	echo "Validating package..."; \
	$(PYTHON) -m twine check dist/* || exit 1; \
	echo "Uploading package..."; \
	export TWINE_USERNAME="__token__"; \
	export TWINE_PASSWORD="$$TOKEN"; \
	if [ "$$REPO" = "testpypi" ]; then \
		$(PYTHON) -m twine upload --repository-url https://test.pypi.org/legacy/ dist/* || exit 1; \
		echo ""; \
		echo "Upload completed successfully."; \
		echo "Open: https://test.pypi.org/"; \
	else \
		$(PYTHON) -m twine upload dist/* || exit 1; \
		echo ""; \
		echo "Upload completed successfully."; \
		echo "Open: https://pypi.org/"; \
	fi

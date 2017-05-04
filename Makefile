.PHONY= venv_create venv_create

venv:
	virtualenv -p /usr/bin/python3 venv

venv_install: venv
	pip install --upgrade pip
	pip install -r requirements.txt

test:
	python -m pytest 

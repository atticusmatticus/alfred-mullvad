all: clean build

build:
	cd src ; \
	zip ../MullvadVPN.alfredworkflow . -r --exclude=*.DS_Store* --exclude=*.pyc* --exclude=*.pyo*

clean:
	rm -f *.alfredworkflow

update-lib:
	/usr/bin/python -m pip install --target src --upgrade Alfred-Workflow
	rm -rf src/Alfred_Workflow-*-info/

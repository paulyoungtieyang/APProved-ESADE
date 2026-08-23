.PHONY: launch dev install clean help

help:
	@echo "APProved Medical Writing Platform"
	@echo ""
	@echo "Usage:"
	@echo "  make launch     Start the server and open the landing page"
	@echo "  make dev        Start the development server"
	@echo "  make install    Install dependencies"
	@echo "  make clean      Remove generated files and database"
	@echo "  make help       Show this help message"

install:
	python3 -m pip install flask sqlalchemy python-pptx markupsafe

dev:
	python3 app.py

launch:
	./launch-demo.sh

clean:
	rm -rf storage/*.db
	rm -rf storage/uploads/*
	rm -rf storage/exports/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

.DEFAULT_GOAL := help

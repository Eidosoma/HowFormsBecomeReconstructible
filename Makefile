.PHONY: check smoke review
check:
	python3 scripts/check_export.py
smoke:
	bash scripts/run_python.sh scripts/smoke_checks.py
review:
	python3 scripts/build_review.py

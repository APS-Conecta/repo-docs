# The local green bar — one command runs every selftest in scripts/ (the
# census round's "make/selftest green locally" outcome; no Makefile existed
# before).
.PHONY: selftest
selftest:
	python3 scripts/docs.py selftest
	python3 scripts/census.py selftest

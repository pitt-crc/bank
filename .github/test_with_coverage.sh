#!/bin/bash
coverage-$1 run -m unittest discover /app
coverage-$1 report --include="/app/bank/*"
coverage-$1 xml --include="/app/bank/*" -o app/coverage.xml
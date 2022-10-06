#!/bin/bash

# Run tests with coverage and catch the exit status
coverage-$1 run -m unittest discover /app
status=$?

# Generate a coverage report
coverage-$1 report --include="/app/bank/*"
coverage-$1 xml --include="/app/bank/*" -o app/coverage.xml

# Exit with the appropriate status
exit $status

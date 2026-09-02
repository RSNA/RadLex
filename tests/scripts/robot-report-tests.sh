#!/bin/bash
set -ex

#
# run SPARQL-query-based ontology integrity tests
#

robot report \
  --input RadLex.owl \
  --profile tests/robot-report-profile.txt \
  --labels true \
  --output robot-report.tsv \
  --limit 50
#!/bin/bash
set -ex

#
# run ROBOT reasoner-based ontology integrity tests
#

robot reason \
  --input RadLex.owl \
  --reasoner ELK \
  --equivalent-classes-allowed asserted-only \
  --dump-unsatisfiable unsatisfiable-explanation.owl \
  --output /tmp/RadLex-reasoned.owl

#
# check that RadLex.owl is in the OWL 2 DL profile. Among other things, this
# fails on a property or class that is used but not declared, which the
# SPARQL-query-based checks can't detect.
#

robot validate-profile \
  --input RadLex.owl \
  --profile DL \
  --output dl-profile-report.txt

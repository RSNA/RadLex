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

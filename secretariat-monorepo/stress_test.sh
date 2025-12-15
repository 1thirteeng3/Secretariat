#!/bin/bash
# RUST-04: Graph Stress Test Generator
# Generates 500 markdown files with random links.

# Handle Localized Documents folder (e.g., Documentos vs Documents)
DOCS_PATH=$(xdg-user-dir DOCUMENTS 2>/dev/null || echo "$HOME/Documents")
VAULT_DIR="$DOCS_PATH/SecretariatVault"
mkdir -p "$VAULT_DIR/stress-test"

echo "Generating 500 notes in $VAULT_DIR/stress-test..."

for i in {1..500}
do
   # Create a random link to another note (e.g., Note_123)
   TARGET=$((1 + $RANDOM % 500))
   
   CONTENT="---
id: stress-$i
title: Note $i
created_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
tags: [stress, test]
---

# Stress Note $i

This is a generated note to test the graph engine.
It links to [[Note $TARGET]] and maybe [[Note $((i+1))]].

Robustez Industrial.
"
   echo "$CONTENT" > "$VAULT_DIR/stress-test/Note_$i.md"
done

echo "Done. Restart Secretariat to test RUST-04."

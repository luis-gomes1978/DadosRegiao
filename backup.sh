#!/bin/bash
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp app.py config.yaml Dockerfile requirements.txt "$BACKUP_DIR/"
cp -r k8s/ "$BACKUP_DIR/"
echo "Backup criado em $BACKUP_DIR"

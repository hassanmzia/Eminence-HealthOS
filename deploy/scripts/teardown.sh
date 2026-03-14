#!/usr/bin/env bash
# HealthOS Clean Teardown Script
# Usage: ./teardown.sh [dev|staging|production] [--delete-namespace]
set -euo pipefail

ENVIRONMENT="${1:-dev}"
DELETE_NS="${2:-}"

RELEASE_NAME="healthos"

# ---------- Colors ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[HEALTHOS]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARNING]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
info()  { echo -e "${CYAN}[INFO]${NC} $*"; }

# ---------- Resolve Namespace ----------
resolve_namespace() {
    case "${ENVIRONMENT}" in
        dev|development)    NAMESPACE="healthos-dev" ;;
        production|prod)    NAMESPACE="healthos-production" ;;
        *)                  NAMESPACE="healthos" ;;
    esac
}

# ---------- Main ----------
main() {
    resolve_namespace

    echo ""
    log "=========================================="
    log "  HealthOS Teardown - ${ENVIRONMENT}"
    log "=========================================="
    echo ""
    warn "This will remove the HealthOS Helm release from namespace '${NAMESPACE}'."
    echo ""
    read -r -p "Are you sure? [y/N] " confirm
    if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
        log "Teardown cancelled."
        exit 0
    fi

    # Uninstall Helm release
    if helm status "${RELEASE_NAME}" -n "${NAMESPACE}" &>/dev/null; then
        log "Uninstalling Helm release '${RELEASE_NAME}'..."
        helm uninstall "${RELEASE_NAME}" -n "${NAMESPACE}"
        log "Helm release removed."
    else
        warn "Helm release '${RELEASE_NAME}' not found in namespace '${NAMESPACE}'."
    fi

    # Delete namespace if requested
    if [[ "${DELETE_NS}" == "--delete-namespace" ]]; then
        warn "Deleting namespace '${NAMESPACE}'..."
        kubectl delete namespace "${NAMESPACE}" --ignore-not-found
        log "Namespace '${NAMESPACE}' deleted."
    else
        info "Namespace '${NAMESPACE}' retained. Pass --delete-namespace to remove it."
    fi

    echo ""
    log "Teardown complete."
}

main

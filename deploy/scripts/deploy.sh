#!/usr/bin/env bash
# HealthOS One-Click Deploy Script
# Usage: ./deploy.sh [dev|staging|production] [--skip-build]
set -euo pipefail

# ---------- Configuration ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HELM_CHART_DIR="${PROJECT_ROOT}/deploy/helm/healthos"
DOCKER_DIR="${PROJECT_ROOT}/deploy/docker"

ENVIRONMENT="${1:-dev}"
SKIP_BUILD="${2:-}"

RELEASE_NAME="healthos"
IMAGE_TAG="${IMAGE_TAG:-latest}"
API_IMAGE="healthos/api:${IMAGE_TAG}"
DASHBOARD_IMAGE="healthos/dashboard:${IMAGE_TAG}"

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

# ---------- Prerequisite Checks ----------
check_prerequisites() {
    log "Checking prerequisites..."
    local missing=0

    for cmd in kubectl helm docker; do
        if ! command -v "$cmd" &>/dev/null; then
            error "$cmd is not installed or not in PATH"
            missing=1
        else
            info "$cmd: $(command -v "$cmd")"
        fi
    done

    if [[ $missing -ne 0 ]]; then
        error "Missing required tools. Please install them and retry."
        exit 1
    fi

    # Verify kubectl connectivity
    if ! kubectl cluster-info &>/dev/null; then
        error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
        exit 1
    fi

    log "All prerequisites satisfied."
}

# ---------- Resolve Environment Values ----------
resolve_values_file() {
    case "${ENVIRONMENT}" in
        dev|development)
            NAMESPACE="healthos-dev"
            VALUES_FILE="${HELM_CHART_DIR}/values-dev.yaml"
            ;;
        production|prod)
            NAMESPACE="healthos-production"
            VALUES_FILE="${HELM_CHART_DIR}/values-production.yaml"
            ;;
        *)
            NAMESPACE="healthos"
            VALUES_FILE=""
            ;;
    esac
    log "Environment: ${ENVIRONMENT} | Namespace: ${NAMESPACE}"
}

# ---------- Build Docker Images ----------
build_images() {
    if [[ "${SKIP_BUILD}" == "--skip-build" ]]; then
        warn "Skipping Docker image builds (--skip-build)"
        return
    fi

    log "Building API image: ${API_IMAGE}"
    docker build \
        -f "${DOCKER_DIR}/Dockerfile.api" \
        -t "${API_IMAGE}" \
        "${PROJECT_ROOT}"

    log "Building Dashboard image: ${DASHBOARD_IMAGE}"
    docker build \
        -f "${DOCKER_DIR}/Dockerfile.dashboard" \
        -t "${DASHBOARD_IMAGE}" \
        "${PROJECT_ROOT}/frontend"

    log "Docker images built successfully."
}

# ---------- Create Namespace ----------
create_namespace() {
    if kubectl get namespace "${NAMESPACE}" &>/dev/null; then
        info "Namespace '${NAMESPACE}' already exists."
    else
        log "Creating namespace '${NAMESPACE}'..."
        kubectl create namespace "${NAMESPACE}"
    fi
}

# ---------- Deploy Helm Chart ----------
deploy_helm() {
    log "Deploying HealthOS via Helm..."

    local helm_args=(
        upgrade --install "${RELEASE_NAME}" "${HELM_CHART_DIR}"
        --namespace "${NAMESPACE}"
        --set "api.image.tag=${IMAGE_TAG}"
        --set "dashboard.image.tag=${IMAGE_TAG}"
        --wait
        --timeout 5m
    )

    if [[ -n "${VALUES_FILE}" && -f "${VALUES_FILE}" ]]; then
        helm_args+=(-f "${VALUES_FILE}")
    fi

    helm "${helm_args[@]}"

    log "Helm deployment complete."
}

# ---------- Wait for Rollout ----------
wait_for_rollout() {
    log "Waiting for API deployment rollout..."
    kubectl rollout status deployment/healthos-api \
        -n "${NAMESPACE}" --timeout=300s

    log "Waiting for Dashboard deployment rollout..."
    kubectl rollout status deployment/healthos-dashboard \
        -n "${NAMESPACE}" --timeout=300s

    log "All deployments rolled out successfully."
}

# ---------- Print Access URLs ----------
print_access_info() {
    echo ""
    log "=========================================="
    log "  HealthOS Deployment Complete"
    log "=========================================="
    echo ""

    # Determine the host from values
    local host
    case "${ENVIRONMENT}" in
        dev|development)  host="healthos.dev.local" ;;
        production|prod)  host="healthos.example.com" ;;
        *)                host="healthos.local" ;;
    esac

    local scheme="https"
    if [[ "${ENVIRONMENT}" == "dev" || "${ENVIRONMENT}" == "development" ]]; then
        scheme="http"
    fi

    info "Dashboard:  ${scheme}://${host}/"
    info "API:        ${scheme}://${host}/api"
    info "Health:     ${scheme}://${host}/health"
    echo ""
    info "Namespace:  ${NAMESPACE}"
    info "Release:    ${RELEASE_NAME}"
    echo ""

    log "Pod status:"
    kubectl get pods -n "${NAMESPACE}" -o wide

    echo ""
    log "Services:"
    kubectl get svc -n "${NAMESPACE}"

    echo ""
    info "To access locally, add '127.0.0.1 ${host}' to /etc/hosts"
    info "and set up an ingress controller (e.g. nginx-ingress)."
    echo ""
}

# ---------- Main ----------
main() {
    echo ""
    log "=========================================="
    log "  HealthOS Deployment - ${ENVIRONMENT}"
    log "=========================================="
    echo ""

    check_prerequisites
    resolve_values_file
    build_images
    create_namespace
    deploy_helm
    wait_for_rollout
    print_access_info
}

main

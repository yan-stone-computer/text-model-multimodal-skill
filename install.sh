#!/usr/bin/env bash
# 让文本模型拥有多模态的技能 — Cross-Platform Installer
# Installs 让文本模型拥有多模态的技能 AI media generation toolkit for your AI coding agent.
#
# Usage:
#   ./install.sh                    # Auto-detect platform
#   ./install.sh --platform workbuddy
#   ./install.sh --platform claude
#   ./install.sh --platform cursor
#   ./install.sh --platform trae
#   ./install.sh --platform windsurf
#   ./install.sh --platform copilot
#   ./install.sh --platform opencode
#   ./install.sh --platform all      # Install for all detected platforms
#   ./install.sh --api-key sk-xxx    # Also save API key during install
#   ./install.sh --help

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory (where this installer lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default install target: ~/.agnes-forge
INSTALL_DIR="${HOME}/.agnes-forge"

PLATFORM=""
API_KEY=""

print_help() {
    cat << 'EOF'
让文本模型拥有多模态的技能 Installer
====================
Installs 让文本模型拥有多模态的技能 AI media generation toolkit for your AI coding agent.

Usage:
  ./install.sh [options]

Options:
  --platform <name>    Target platform: workbuddy, claude, cursor, trae,
                       windsurf, copilot, opencode, all (default: auto-detect)
  --api-key <key>      Save Agnes AI API key during install
  --dir <path>         Install directory (default: ~/.agnes-forge)
  --help               Show this help

Supported Platforms:
  workbuddy   WorkBuddy (SKILL.md in ~/.workbuddy/skills/agnes-forge/)
  claude      Claude Code (CLAUDE.md + claude/commands/ in project root)
  cursor      Cursor (cursorrules + cursor/rules/ in project root)
  trae        Trae (trae/rules/ in project root)
  windsurf    Windsurf (windsurfrules in project root)
  copilot     GitHub Copilot (github/copilot-instructions.md)
  opencode    OpenCode (AGENTS.md in project root)
  all         Install for all platforms above

Examples:
  ./install.sh --platform claude --api-key sk-xxx
  ./install.sh --platform all
  ./install.sh  # auto-detect
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --platform)
                PLATFORM="$2"
                shift 2
                ;;
            --api-key)
                API_KEY="$2"
                shift 2
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --help|-h)
                print_help
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_help
                exit 1
                ;;
        esac
    done
}

detect_platform() {
    if [[ -n "$PLATFORM" ]]; then
        return
    fi

    # Check for WorkBuddy
    if [[ -d "${HOME}/.workbuddy/skills" ]]; then
        PLATFORM="workbuddy"
        return
    fi

    # Check for Claude Code (project claude dir)
    if [[ -d "claude" ]] || command -v claude &>/dev/null; then
        PLATFORM="claude"
        return
    fi

    # Check for Cursor
    if [[ -f "cursorrules" ]] || [[ -d "cursor" ]]; then
        PLATFORM="cursor"
        return
    fi

    # Check for Trae
    if [[ -d "trae" ]]; then
        PLATFORM="trae"
        return
    fi

    # Check for Windsurf
    if [[ -f "windsurfrules" ]] || command -v windsurf &>/dev/null; then
        PLATFORM="windsurf"
        return
    fi

    # Check for GitHub Copilot
    if [[ -d "github/copilot-instructions.md" ]] || [[ -d "github" ]]; then
        PLATFORM="copilot"
        return
    fi

    # Default: opencode (AGENTS.md)
    PLATFORM="opencode"
}

install_core() {
    echo -e "${CYAN}[1/3] Installing core files to ${INSTALL_DIR}/${NC}"

    mkdir -p "${INSTALL_DIR}/scripts"
    mkdir -p "${INSTALL_DIR}/references"

    # Copy main script
    cp "${SCRIPT_DIR}/scripts/agnes_api.py" "${INSTALL_DIR}/scripts/agnes_api.py"
    chmod +x "${INSTALL_DIR}/scripts/agnes_api.py" 2>/dev/null || true

    # Copy API reference
    cp "${SCRIPT_DIR}/references/api-reference.md" "${INSTALL_DIR}/references/api-reference.md"

    # Copy AGENTS.md (universal instructions)
    cp "${SCRIPT_DIR}/AGENTS.md" "${INSTALL_DIR}/AGENTS.md"

    # Create .env template if not exists
    if [[ ! -f "${INSTALL_DIR}/scripts/.env" ]]; then
        cat > "${INSTALL_DIR}/scripts/.env" << 'ENVFILE'
# Agnes AI API Configuration
# Get your free key: https://platform.agnes-ai.com → Settings → API Keys
AGNES_API_KEY=
ENVFILE
    fi

    echo -e "${GREEN}  ✓ Core files installed${NC}"
}

save_api_key() {
    if [[ -z "$API_KEY" ]]; then
        return
    fi

    echo -e "${CYAN}Saving API key...${NC}"
    python3 "${INSTALL_DIR}/scripts/agnes_api.py" set-key "$API_KEY" 2>/dev/null || \
    python "${INSTALL_DIR}/scripts/agnes_api.py" set-key "$API_KEY" 2>/dev/null || \
    {
        # Fallback: write directly
        cat > "${INSTALL_DIR}/scripts/.env" << ENVEOF
# Agnes AI API Configuration
AGNES_API_KEY=${API_KEY}
ENVEOF
    }
    echo -e "${GREEN}  ✓ API key saved${NC}"
}

install_workbuddy() {
    local skill_dir="${HOME}/.workbuddy/skills/agnes-forge"
    echo -e "${CYAN}  → WorkBuddy: ${skill_dir}${NC}"
    mkdir -p "${skill_dir}/scripts" "${skill_dir}/references"
    cp "${SCRIPT_DIR}/scripts/agnes_api.py" "${skill_dir}/scripts/"
    cp "${SCRIPT_DIR}/references/api-reference.md" "${skill_dir}/references/"
    cp "${SCRIPT_DIR}/SKILL.md" "${skill_dir}/SKILL.md"

    # Copy .env if exists
    if [[ -f "${INSTALL_DIR}/scripts/.env" ]]; then
        cp "${INSTALL_DIR}/scripts/.env" "${skill_dir}/scripts/.env"
    fi

    echo -e "${GREEN}  ✓ WorkBuddy skill installed${NC}"
}

install_claude() {
    echo -e "${CYAN}  → Claude Code: CLAUDE.md + claude/commands/${NC}"
    cp "${SCRIPT_DIR}/CLAUDE.md" "./CLAUDE.md" 2>/dev/null || true
    mkdir -p ".claude/commands"
    cp "${SCRIPT_DIR}/claude/commands/agnes.md" ".claude/commands/agnes.md" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Claude Code configured${NC}"
}

install_cursor() {
    echo -e "${CYAN}  → Cursor: cursorrules + cursor/rules/${NC}"
    cp "${SCRIPT_DIR}/cursorrules" "./.cursorrules" 2>/dev/null || true
    mkdir -p ".cursor/rules"
    cp "${SCRIPT_DIR}/cursor/rules/agnes-forge.mdc" ".cursor/rules/agnes-forge.mdc" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Cursor configured${NC}"
}

install_trae() {
    # Project-level skill (Trae rules)
    echo -e "${CYAN}  → Trae (project): trae/rules/ + trae/skills/agnes-forge/${NC}"
    mkdir -p ".trae/rules" ".trae/skills/agnes-forge/scripts" ".trae/skills/agnes-forge/references"
    cp "${SCRIPT_DIR}/trae/rules/agnes-forge.md" ".trae/rules/agnes-forge.md" 2>/dev/null || true
    cp "${SCRIPT_DIR}/trae/skills/agnes-forge/SKILL.md" ".trae/skills/agnes-forge/SKILL.md" 2>/dev/null || true
    cp "${SCRIPT_DIR}/scripts/agnes_api.py" ".trae/skills/agnes-forge/scripts/agnes_api.py" 2>/dev/null || true
    cp "${SCRIPT_DIR}/references/api-reference.md" ".trae/skills/agnes-forge/references/api-reference.md" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Trae (project) configured${NC}"

    # Global-level skill (Trae user skills dir: ~/.trae/skills, Windows %USERPROFILE%/.trae/skills)
    local trae_global="${HOME}/.trae/skills/agnes-forge"
    if [[ -n "${USERPROFILE:-}" ]]; then
        trae_global="${USERPROFILE}/.trae/skills/agnes-forge"
    fi
    echo -e "${CYAN}  → Trae (global): ${trae_global}${NC}"
    mkdir -p "${trae_global}/scripts" "${trae_global}/references"
    cp "${SCRIPT_DIR}/trae/skills/agnes-forge/SKILL.md" "${trae_global}/SKILL.md" 2>/dev/null || true
    cp "${SCRIPT_DIR}/scripts/agnes_api.py" "${trae_global}/scripts/agnes_api.py" 2>/dev/null || true
    cp "${SCRIPT_DIR}/references/api-reference.md" "${trae_global}/references/api-reference.md" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Trae (global) configured${NC}"
}

install_windsurf() {
    echo -e "${CYAN}  → Windsurf: windsurfrules${NC}"
    cp "${SCRIPT_DIR}/windsurfrules" "./.windsurfrules" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Windsurf configured${NC}"
}

install_copilot() {
    echo -e "${CYAN}  → GitHub Copilot: github/copilot-instructions.md${NC}"
    mkdir -p ".github"
    cp "${SCRIPT_DIR}/github/copilot-instructions.md" ".github/copilot-instructions.md" 2>/dev/null || true
    echo -e "${GREEN}  ✓ GitHub Copilot configured${NC}"
}

install_opencode() {
    echo -e "${CYAN}  → OpenCode: AGENTS.md${NC}"
    cp "${SCRIPT_DIR}/AGENTS.md" "./AGENTS.md" 2>/dev/null || true
    echo -e "${GREEN}  ✓ OpenCode configured${NC}"
}

install_platform_files() {
    echo -e "${CYAN}[2/3] Installing platform config files...${NC}"

    if [[ "$PLATFORM" == "all" ]]; then
        install_workbuddy
        install_claude
        install_cursor
        install_trae
        install_windsurf
        install_copilot
        install_opencode
        return
    fi

    case "$PLATFORM" in
        workbuddy)  install_workbuddy ;;
        claude)     install_claude ;;
        cursor)     install_cursor ;;
        trae)       install_trae ;;
        windsurf)   install_windsurf ;;
        copilot)    install_copilot ;;
        opencode)   install_opencode ;;
        *)
            echo -e "${RED}Unknown platform: $PLATFORM${NC}"
            echo "Supported: workbuddy, claude, cursor, trae, windsurf, copilot, opencode, all"
            exit 1
            ;;
    esac
}

print_summary() {
    echo ""
    echo -e "${CYAN}[3/3] Installation Complete!${NC}"
    echo ""
    echo -e "  Install dir:  ${GREEN}${INSTALL_DIR}${NC}"
    echo -e "  Platform:     ${GREEN}${PLATFORM}${NC}"
    echo ""

    if [[ -z "$API_KEY" ]]; then
        echo -e "${YELLOW}  Next step: Save your API key${NC}"
        echo -e "    python ${INSTALL_DIR}/scripts/agnes_api.py set-key sk-xxxxx"
        echo -e "    Free key: https://platform.agnes-ai.com"
        echo ""
    fi

    echo -e "  Quick test:"
    echo -e "    python ${INSTALL_DIR}/scripts/agnes_api.py image --prompt \"a cute cat\" --size 1K --download"
    echo ""
    echo -e "${GREEN}让文本模型拥有多模态的技能 is ready!${NC}"
}

main() {
    parse_args "$@"
    detect_platform

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   让文本模型拥有多模态的技能 Installer                    ║${NC}"
    echo -e "${GREEN}║   AI Media Generation Toolkit              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""

    install_core
    save_api_key
    install_platform_files
    print_summary
}

main "$@"

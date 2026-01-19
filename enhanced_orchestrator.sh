#!/bin/bash
# Enhanced Claude Code MCP Orchestrator
# Integrates with Zotero, Google Scholar, Playwright for agentic workflows

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/orchestrator_config.json"

# Default configuration
DEFAULT_SESSION="claude-ai"
DEFAULT_RESEARCH_WINDOW="research"
DEFAULT_DEV_WINDOW="development"
DEFAULT_TEST_WINDOW="testing"
DEFAULT_MONITOR_WINDOW="monitor"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Initialize tmux session with specialized windows
init_session() {
    local session_name=${1:-$DEFAULT_SESSION}
    
    log "Initializing enhanced agentic session: $session_name"
    
    # Check if session already exists
    if tmux has-session -t "$session_name" 2>/dev/null; then
        warning "Session $session_name already exists. Attaching..."
        tmux attach-session -t "$session_name"
        return 0
    fi
    
    # Create new session with research window
    tmux new-session -d -s "$session_name" -n "$DEFAULT_RESEARCH_WINDOW"
    
    # Setup research window with Claude Code
    tmux send-keys -t "$session_name:$DEFAULT_RESEARCH_WINDOW" "claude" Enter
    tmux send-keys -t "$session_name:$DEFAULT_RESEARCH_WINDOW" "# Research Agent - Zotero & Google Scholar Integration" Enter
    tmux send-keys -t "$session_name:$DEFAULT_RESEARCH_WINDOW" "# Available tools: search_google_scholar_key_words, search_nodes (zotero)" Enter
    
    # Create development window
    tmux new-window -t "$session_name" -n "$DEFAULT_DEV_WINDOW"
    tmux send-keys -t "$session_name:$DEFAULT_DEV_WINDOW" "claude" Enter
    tmux send-keys -t "$session_name:$DEFAULT_DEV_WINDOW" "# Development Agent - Code Creation & Review" Enter
    
    # Create testing window
    tmux new-window -t "$session_name" -n "$DEFAULT_TEST_WINDOW"
    tmux send-keys -t "$session_name:$DEFAULT_TEST_WINDOW" "claude" Enter
    tmux send-keys -t "$session_name:$DEFAULT_TEST_WINDOW" "# Testing Agent - Playwright Automation" Enter
    tmux send-keys -t "$session_name:$DEFAULT_TEST_WINDOW" "# Available tools: playwright automation, web testing" Enter
    
    # Create monitoring window
    tmux new-window -t "$session_name" -n "$DEFAULT_MONITOR_WINDOW"
    tmux send-keys -t "$session_name:$DEFAULT_MONITOR_WINDOW" "# Agent Coordinator & Monitor" Enter
    
    success "Session initialized with 4 specialized agent windows"
    
    # Switch to research window
    tmux select-window -t "$session_name:$DEFAULT_RESEARCH_WINDOW"
    tmux attach-session -t "$session_name"
}

# Send coordinated message to specific agent
send_agent_message() {
    local agent_type="$1"
    local message="$2"
    local session_name="${3:-$DEFAULT_SESSION}"
    
    case $agent_type in
        "research"|"r")
            target_window="$session_name:$DEFAULT_RESEARCH_WINDOW"
            agent_name="Research Agent"
            ;;
        "dev"|"d")
            target_window="$session_name:$DEFAULT_DEV_WINDOW"  
            agent_name="Development Agent"
            ;;
        "test"|"t")
            target_window="$session_name:$DEFAULT_TEST_WINDOW"
            agent_name="Testing Agent"
            ;;
        "monitor"|"m")
            target_window="$session_name:$DEFAULT_MONITOR_WINDOW"
            agent_name="Monitor Agent"
            ;;
        *)
            error "Unknown agent type: $agent_type"
            echo "Available agents: research|r, dev|d, test|t, monitor|m"
            return 1
            ;;
    esac
    
    log "Sending message to $agent_name"
    tmux send-keys -t "$target_window" "$message"
    sleep 0.5
    tmux send-keys -t "$target_window" Enter
    
    success "Message sent to $agent_name: $message"
}

# Coordinate research task using MCP servers
research_task() {
    local query="$1"
    local session_name="${2:-$DEFAULT_SESSION}"
    
    log "Initiating research workflow for: $query"
    
    # Send to research agent
    send_agent_message "research" "Search for academic papers about '$query' using Google Scholar and Zotero integration. Provide a comprehensive summary with key findings." "$session_name"
    
    # Schedule follow-up coordination
    schedule_followup 5 "Review research results for '$query' and coordinate with development team" "$session_name:$DEFAULT_MONITOR_WINDOW"
}

# Coordinate development task
development_task() {
    local task="$1"
    local session_name="${2:-$DEFAULT_SESSION}"
    
    log "Initiating development workflow for: $task"
    
    send_agent_message "dev" "Implement: $task. Follow best practices and ensure comprehensive testing." "$session_name"
    
    # Auto-schedule testing phase
    schedule_followup 15 "Review development progress and initiate testing phase for '$task'" "$session_name:$DEFAULT_MONITOR_WINDOW"
}

# Coordinate testing with Playwright
testing_task() {
    local test_spec="$1"
    local session_name="${2:-$DEFAULT_SESSION}"
    
    log "Initiating testing workflow for: $test_spec"
    
    send_agent_message "test" "Create and execute automated tests for: $test_spec. Use Playwright MCP servers for web automation." "$session_name"
}

# Enhanced scheduling with task context
schedule_followup() {
    local minutes="$1"
    local task_note="$2"
    local target_window="$3"
    
    # Create detailed note file
    local note_file="$SCRIPT_DIR/orchestrator_notes_$(date +%Y%m%d_%H%M%S).txt"
    cat > "$note_file" << EOF
=== Orchestrator Follow-up Task ===
Scheduled: $(date)
Target: $target_window
Priority: High

TASK DETAILS:
$task_note

AGENT COORDINATION:
- Check all agent progress
- Review completed outputs  
- Coordinate next phase of work
- Update project status

=== End Note ===
EOF

    log "Scheduling follow-up in $minutes minutes"
    
    # Calculate exact time
    local seconds=$(echo "$minutes * 60" | bc)
    nohup bash -c "sleep $seconds && tmux send-keys -t '$target_window' 'ORCHESTRATOR ALERT: cat \"$note_file\"' && sleep 1 && tmux send-keys -t '$target_window' Enter" > /dev/null 2>&1 &
    
    success "Follow-up scheduled for $minutes minutes: $task_note"
}

# Status check across all agents
status_check() {
    local session_name="${1:-$DEFAULT_SESSION}"
    
    log "Performing system-wide agent status check"
    
    echo -e "\n${CYAN}=== Agent Status Report ===${NC}"
    
    # Check each window
    for window in "$DEFAULT_RESEARCH_WINDOW" "$DEFAULT_DEV_WINDOW" "$DEFAULT_TEST_WINDOW" "$DEFAULT_MONITOR_WINDOW"; do
        if tmux list-windows -t "$session_name" -F "#{window_name}" | grep -q "^$window$"; then
            echo -e "${GREEN}✓${NC} $window agent: Active"
        else
            echo -e "${RED}✗${NC} $window agent: Not found"
        fi
    done
    
    # Check MCP servers
    echo -e "\n${CYAN}=== MCP Server Status ===${NC}"
    claude mcp list
}

# Show usage help
usage() {
    cat << EOF
Enhanced Claude Code MCP Orchestrator

USAGE:
    $0 <command> [options]

COMMANDS:
    init [session_name]                    Initialize tmux session with agents
    send <agent> <message> [session]      Send message to specific agent
    research <query> [session]            Start research workflow  
    develop <task> [session]              Start development workflow
    test <spec> [session]                 Start testing workflow
    status [session]                      Check all agent status
    schedule <minutes> <note> <target>    Schedule follow-up task

AGENT TYPES:
    research, r    Research agent (Zotero + Google Scholar)
    dev, d         Development agent  
    test, t        Testing agent (Playwright)
    monitor, m     Coordination & monitoring

EXAMPLES:
    $0 init my-project
    $0 send research "Find papers on AI agents"  
    $0 research "machine learning optimization"
    $0 develop "implement user authentication"
    $0 test "login form validation"
    $0 status

FEATURES:
    - Multi-agent coordination with tmux
    - Integrated MCP servers (Zotero, Google Scholar, Playwright)
    - Automated task scheduling and follow-ups
    - Persistent session management
    - Real-time status monitoring

EOF
}

# Main command processing
main() {
    case "$1" in
        "init"|"initialize")
            init_session "$2"
            ;;
        "send"|"message")
            if [ $# -lt 3 ]; then
                error "Usage: $0 send <agent> <message> [session]"
                exit 1
            fi
            send_agent_message "$2" "$3" "$4"
            ;;
        "research")
            if [ -z "$2" ]; then
                error "Usage: $0 research <query> [session]"
                exit 1
            fi
            research_task "$2" "$3"
            ;;
        "develop"|"dev")
            if [ -z "$2" ]; then
                error "Usage: $0 develop <task> [session]"
                exit 1
            fi
            development_task "$2" "$3"
            ;;
        "test"|"testing")
            if [ -z "$2" ]; then
                error "Usage: $0 test <test_spec> [session]"
                exit 1
            fi
            testing_task "$2" "$3"
            ;;
        "status"|"check")
            status_check "$2"
            ;;
        "schedule")
            if [ $# -lt 4 ]; then
                error "Usage: $0 schedule <minutes> <note> <target>"
                exit 1
            fi
            schedule_followup "$2" "$3" "$4"
            ;;
        "help"|"-h"|"--help"|"")
            usage
            ;;
        *)
            error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
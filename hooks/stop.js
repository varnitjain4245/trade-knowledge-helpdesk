'use strict';

/**
 * stop.js — Stop Hook Entry Point
 *
 * Prevents the workflow from finishing prematurely.
 * Verifies that the current stage is approved, required artifacts exist,
 * no stale artifacts remain, and workflow state is consistent.
 *
 * Input:  JSON on stdin (Antigravity Stop payload)
 * Output: JSON on stdout { decision: 'continue'|'stop', reason: string }
 */

const fs = require('fs');
const path = require('path');
const {
  STAGES,
  STAGE_ARTIFACTS,
  ARTIFACT_DIR,
  WORKFLOW_STATE_PATH,
} = require('./utils/config');
const { readState } = require('./utils/state-manager');
const { log } = require('./utils/logger');

/**
 * Read all of stdin as a string.
 */
function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

/**
 * Respond to Antigravity runtime.
 */
function respond(decision, reason) {
  const response = { decision, reason: reason || '' };
  process.stdout.write(JSON.stringify(response) + '\n');
}

/**
 * Main hook logic.
 */
async function main() {
  const startTime = Date.now();
  let input;

  try {
    const raw = await readStdin();
    input = JSON.parse(raw);
  } catch (err) {
    // Can't parse — don't block termination
    log({
      hook: 'stop',
      action: 'parse_error',
      decision: 'stop',
      reason: `Failed to parse stdin: ${err.message}`,
    });
    respond('stop', 'Hook input parse error — allowing stop');
    return;
  }

  // -----------------------------------------------------------------------
  // If the termination reason is an error or max_steps, allow stop
  // -----------------------------------------------------------------------
  const terminationReason = input.terminationReason || '';
  if (terminationReason === 'error' || terminationReason === 'max_steps_exceeded') {
    log({
      hook: 'stop',
      action: 'allow_error_stop',
      decision: 'stop',
      reason: `Allowing stop due to: ${terminationReason}`,
      duration: Date.now() - startTime,
    });
    respond('stop', `Stopping due to: ${terminationReason}`);
    return;
  }

  // -----------------------------------------------------------------------
  // Read workflow state
  // -----------------------------------------------------------------------
  let state;
  try {
    state = readState();
  } catch (err) {
    log({
      hook: 'stop',
      action: 'state_read_error',
      decision: 'stop',
      reason: `Cannot read workflow state: ${err.message}`,
      duration: Date.now() - startTime,
    });
    respond('stop', 'Cannot read workflow state — allowing stop');
    return;
  }

  const currentStage = state.currentStage;
  const issues = [];

  // -----------------------------------------------------------------------
  // Check 1: If workflow hasn't started yet, allow stop
  // -----------------------------------------------------------------------
  if (!currentStage || state.workflowStatus === 'not_started') {
    log({
      hook: 'stop',
      action: 'allow_idle_stop',
      decision: 'stop',
      reason: 'Workflow has not started — allowing stop',
      duration: Date.now() - startTime,
    });
    respond('stop', 'Workflow has not started');
    return;
  }

  // -----------------------------------------------------------------------
  // Check 2: Is the current stage waiting for approval?
  // -----------------------------------------------------------------------
  if (state.waitingForApproval) {
    // This is fine — the agent presented the gate and is waiting for user input.
    // Allow stop so the user can interact.
    log({
      hook: 'stop',
      action: 'allow_approval_wait',
      decision: 'stop',
      reason: `Waiting for approval on: ${state.waitingForApproval}`,
      duration: Date.now() - startTime,
    });
    respond('stop', `Waiting for user approval on: ${state.waitingForApproval}`);
    return;
  }

  // -----------------------------------------------------------------------
  // Check 3: Required artifact for current stage exists on disk?
  // -----------------------------------------------------------------------
  const requiredArtifacts = STAGE_ARTIFACTS[currentStage] || [];
  for (const artifact of requiredArtifacts) {
    const artifactPath = path.join(ARTIFACT_DIR, artifact);
    if (!fs.existsSync(artifactPath)) {
      issues.push(`Missing required artifact: ${artifact} (for stage: ${currentStage})`);
    }
  }

  // -----------------------------------------------------------------------
  // Check 4: No stale artifacts?
  // -----------------------------------------------------------------------
  if (state.staleArtifacts && state.staleArtifacts.length > 0) {
    issues.push(`Stale artifacts detected: ${state.staleArtifacts.join(', ')}`);
  }

  // -----------------------------------------------------------------------
  // Check 5: Workflow state consistency
  // -----------------------------------------------------------------------
  if (!state.workflowStatus) {
    issues.push('workflowStatus is missing from workflow-state.json');
  }

  if (state.workflowStatus === 'in_progress' && !state.approvedStages?.includes(currentStage)) {
    issues.push(`Current stage "${currentStage}" is in_progress but not yet approved`);
  }

  // -----------------------------------------------------------------------
  // Decision
  // -----------------------------------------------------------------------
  if (issues.length > 0) {
    const reason = issues.join('; ');
    log({
      hook: 'stop',
      stage: currentStage,
      action: 'block_premature_stop',
      decision: 'continue',
      reason,
      duration: Date.now() - startTime,
    });
    respond('continue', reason);
  } else {
    log({
      hook: 'stop',
      stage: currentStage,
      action: 'allow_stop',
      decision: 'stop',
      reason: 'All completion checks passed',
      duration: Date.now() - startTime,
    });
    respond('stop', 'All completion checks passed');
  }
}

main().catch((err) => {
  log({
    hook: 'stop',
    action: 'fatal_error',
    decision: 'stop',
    reason: err.message,
  });
  // On error, allow stop to not trap the agent
  respond('stop', `Hook error: ${err.message}`);
  process.exit(0);
});

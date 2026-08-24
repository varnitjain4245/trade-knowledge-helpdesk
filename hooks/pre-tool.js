'use strict';

/**
 * pre-tool.js — PreToolUse Hook Entry Point
 *
 * Intercepts every write operation before it executes.
 * Validates artifact ownership, stage transitions, JSON/schema validity,
 * and skill lock enforcement.
 *
 * Input:  JSON on stdin (Antigravity PreToolUse payload)
 * Output: JSON on stdout { decision: 'allow'|'deny', reason: string }
 */

const path = require('path');
const {
  isProtectedPath,
  getArtifactName,
  ARTIFACT_OWNER,
  WORKSPACE_ROOT,
  PROJECT_JSON_PATH,
  WORKFLOW_STATE_PATH,
} = require('./utils/config');
const { readState } = require('./utils/state-manager');
const { log } = require('./utils/logger');

// Lazy-load validators (only when needed)
function getValidators() {
  return {
    validateJson: require('./validators/json-validator'),  // exports fn directly
    validateProjectJson: require('./validators/schema-validator').validateProjectJson,
    validateWorkflowState: require('./validators/schema-validator').validateWorkflowState,
    validateStatusTransition: require('./validators/transition-validator'),  // exports fn directly
    validateArtifactOwnership: require('./validators/artifact-validator').validateArtifactOwnership,
  };
}

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
 * Extract the target file path from tool arguments.
 */
function getTargetFile(toolName, toolArgs) {
  if (!toolArgs) return null;

  // write_to_file, replace_file_content, multi_replace_file_content
  if (toolArgs.TargetFile) return toolArgs.TargetFile;

  // run_command — we don't validate command writes
  return null;
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
    // Can't parse input — allow by default to not block the agent
    log({
      hook: 'preToolUse',
      action: 'parse_error',
      decision: 'allow',
      reason: `Failed to parse stdin: ${err.message}`,
    });
    respond('allow', 'Hook input parse error — allowing by default');
    return;
  }

  const toolName = input.toolCall?.name || input.toolName || 'unknown';
  const toolArgs = input.toolCall?.args || input.toolInput || {};

  // -----------------------------------------------------------------------
  // For run_command: we only log, don't block
  // -----------------------------------------------------------------------
  if (toolName === 'run_command') {
    log({
      hook: 'preToolUse',
      action: 'passthrough',
      decision: 'allow',
      reason: 'run_command is allowed (not a file write)',
      duration: Date.now() - startTime,
    });
    respond('allow');
    return;
  }

  // -----------------------------------------------------------------------
  // Get target file path
  // -----------------------------------------------------------------------
  const targetFile = getTargetFile(toolName, toolArgs);

  if (!targetFile) {
    log({
      hook: 'preToolUse',
      action: 'passthrough',
      decision: 'allow',
      reason: 'No target file detected',
      duration: Date.now() - startTime,
    });
    respond('allow');
    return;
  }

  const absolutePath = path.isAbsolute(targetFile)
    ? targetFile
    : path.resolve(WORKSPACE_ROOT, targetFile);

  // -----------------------------------------------------------------------
  // If NOT a protected path, allow freely
  // -----------------------------------------------------------------------
  if (!isProtectedPath(absolutePath)) {
    log({
      hook: 'preToolUse',
      artifact: path.basename(absolutePath),
      action: 'passthrough',
      decision: 'allow',
      reason: 'File is not in a protected path',
      duration: Date.now() - startTime,
    });
    respond('allow');
    return;
  }

  // -----------------------------------------------------------------------
  // Protected path — run validations
  // -----------------------------------------------------------------------
  const validators = getValidators();
  const state = readState();
  const currentStage = state.currentStage;
  const errors = [];

  // --- Check 1: JSON validity for .json files ---
  if (absolutePath.endsWith('.json') && toolArgs.CodeContent) {
    const jsonResult = validators.validateJson(toolArgs.CodeContent);
    if (!jsonResult.valid) {
      errors.push(...jsonResult.errors.map((e) => `JSON validation: ${e}`));
    }
  }

  // --- Check 2: Schema validation for project.json ---
  if (absolutePath === PROJECT_JSON_PATH && toolArgs.CodeContent) {
    try {
      const parsed = JSON.parse(toolArgs.CodeContent);
      const schemaResult = validators.validateProjectJson(parsed);
      if (!schemaResult.valid) {
        errors.push(...schemaResult.errors.map((e) => `Schema (project.json): ${e}`));
      }

      // Check status transitions
      if (currentStage && parsed.stages && parsed.stages[currentStage]) {
        const currentStatus = state.artifactVersions ? 'in_progress' : 'not_started';
        const newStatus = parsed.stages[currentStage].status;
        if (newStatus && newStatus !== currentStatus) {
          const transResult = validators.validateStatusTransition(currentStatus, newStatus);
          if (!transResult.valid) {
            errors.push(...transResult.errors.map((e) => `Transition: ${e}`));
          }
        }
      }
    } catch { /* JSON parse failure already caught above */ }
  }

  // --- Check 3: Schema validation for workflow-state.json ---
  if (absolutePath === WORKFLOW_STATE_PATH && toolArgs.CodeContent) {
    try {
      const parsed = JSON.parse(toolArgs.CodeContent);
      const wsResult = validators.validateWorkflowState(parsed);
      if (!wsResult.valid) {
        errors.push(...wsResult.errors.map((e) => `Schema (workflow-state): ${e}`));
      }
    } catch { /* JSON parse failure already caught above */ }
  }

  // --- Check 4: Artifact ownership ---
  const artifactName = getArtifactName(absolutePath);
  if (artifactName && currentStage) {
    const ownerResult = validators.validateArtifactOwnership(artifactName, currentStage);
    if (!ownerResult.valid) {
      errors.push(...ownerResult.errors.map((e) => `Ownership: ${e}`));
    }
  }

  // -----------------------------------------------------------------------
  // Decision
  // -----------------------------------------------------------------------
  if (errors.length > 0) {
    const reason = errors.join('; ');
    log({
      hook: 'preToolUse',
      stage: currentStage,
      artifact: artifactName || path.basename(absolutePath),
      action: 'deny',
      decision: 'deny',
      reason,
      duration: Date.now() - startTime,
    });
    respond('deny', reason);
  } else {
    log({
      hook: 'preToolUse',
      stage: currentStage,
      artifact: artifactName || path.basename(absolutePath),
      action: 'allow',
      decision: 'allow',
      reason: 'All validations passed',
      duration: Date.now() - startTime,
    });
    respond('allow', 'All validations passed');
  }
}

main().catch((err) => {
  log({
    hook: 'preToolUse',
    action: 'fatal_error',
    decision: 'allow',
    reason: err.message,
  });
  // On unhandled error, allow by default to avoid blocking the agent entirely
  respond('allow', `Hook error (allowing by default): ${err.message}`);
  process.exit(0);
});

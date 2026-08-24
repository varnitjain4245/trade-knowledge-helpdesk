'use strict';

/**
 * post-tool.js — PostToolUse Hook Entry Point
 *
 * Runs after every successful write operation.
 * Updates workflow-state.json with artifact metadata, checksums, versions,
 * and cascades staleness to downstream artifacts.
 *
 * Input:  JSON on stdin (Antigravity PostToolUse payload)
 * Output: JSON on stdout {} (PostToolUse hooks return empty object)
 */

const path = require('path');
const fs = require('fs');
const {
  isProtectedPath,
  getArtifactName,
  ARTIFACT_OWNER,
  ARTIFACT_DIR,
  getDownstreamArtifacts,
  WORKSPACE_ROOT,
} = require('./utils/config');
const { hashFile } = require('./utils/checksum');
const { readState, updateState } = require('./utils/state-manager');
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
 * Extract the target file path from tool arguments.
 */
function getTargetFile(toolArgs) {
  if (!toolArgs) return null;
  if (toolArgs.TargetFile) return toolArgs.TargetFile;
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
    log({
      hook: 'postToolUse',
      action: 'parse_error',
      decision: 'noop',
      reason: `Failed to parse stdin: ${err.message}`,
    });
    process.stdout.write(JSON.stringify({}) + '\n');
    return;
  }

  const toolName = input.toolCall?.name || input.toolName || 'unknown';
  const toolArgs = input.toolCall?.args || input.toolInput || {};
  const targetFile = getTargetFile(toolArgs);

  if (!targetFile) {
    process.stdout.write(JSON.stringify({}) + '\n');
    return;
  }

  const absolutePath = path.isAbsolute(targetFile)
    ? targetFile
    : path.resolve(WORKSPACE_ROOT, targetFile);

  // Only process artifact writes
  const artifactName = getArtifactName(absolutePath);

  if (!artifactName) {
    log({
      hook: 'postToolUse',
      action: 'passthrough',
      decision: 'noop',
      reason: 'Write is not to an artifact path',
      duration: Date.now() - startTime,
    });
    process.stdout.write(JSON.stringify({}) + '\n');
    return;
  }

  // -----------------------------------------------------------------------
  // Update artifact metadata in workflow-state.json
  // -----------------------------------------------------------------------
  const owningStage = ARTIFACT_OWNER[artifactName] || null;
  const checksum = hashFile(absolutePath);
  const now = new Date().toISOString();

  try {
    updateState((state) => {
      // Initialize artifactVersions if missing
      if (!state.artifactVersions) {
        state.artifactVersions = {};
      }

      const prev = state.artifactVersions[artifactName];
      const previousChecksum = prev ? prev.checksum : null;

      // Update artifact metadata
      state.artifactVersions[artifactName] = {
        version: prev ? prev.version + 1 : 1,
        createdAt: prev && prev.createdAt ? prev.createdAt : now,
        updatedAt: now,
        stage: owningStage,
        status: 'generated',
        checksum: checksum,
        lastModifiedBySkill: state.currentSkill || null,
        approvalStatus: 'pending',
      };

      // -----------------------------------------------------------------------
      // Dependency cascade: if checksum changed, mark downstream as STALE
      // -----------------------------------------------------------------------
      if (previousChecksum && checksum !== previousChecksum) {
        const downstream = getDownstreamArtifacts(artifactName);
        const newlyStale = [];

        for (const downArtifact of downstream) {
          if (state.artifactVersions[downArtifact]) {
            state.artifactVersions[downArtifact].status = 'stale';
            state.artifactVersions[downArtifact].approvalStatus = 'stale';
            state.artifactVersions[downArtifact].updatedAt = now;
            newlyStale.push(downArtifact);
          }
        }

        // Update staleArtifacts list (deduplicate)
        if (!state.staleArtifacts) state.staleArtifacts = [];
        const staleSet = new Set([...state.staleArtifacts, ...newlyStale]);
        state.staleArtifacts = [...staleSet];

        if (newlyStale.length > 0) {
          log({
            hook: 'postToolUse',
            stage: owningStage,
            artifact: artifactName,
            action: 'cascade_stale',
            decision: 'noop',
            reason: `Upstream change detected. Marked STALE: ${newlyStale.join(', ')}`,
            duration: Date.now() - startTime,
          });
        }
      }

      // Remove this artifact from staleArtifacts if it was regenerated
      if (state.staleArtifacts) {
        state.staleArtifacts = state.staleArtifacts.filter((a) => a !== artifactName);
      }
    });

    log({
      hook: 'postToolUse',
      stage: owningStage,
      artifact: artifactName,
      action: 'update_metadata',
      decision: 'noop',
      reason: `Artifact metadata updated. Checksum: ${checksum ? checksum.substring(0, 12) + '...' : 'null'}`,
      duration: Date.now() - startTime,
    });
  } catch (err) {
    log({
      hook: 'postToolUse',
      stage: owningStage,
      artifact: artifactName,
      action: 'state_update_error',
      decision: 'noop',
      reason: err.message,
      duration: Date.now() - startTime,
    });
  }

  process.stdout.write(JSON.stringify({}) + '\n');
}

main().catch((err) => {
  log({
    hook: 'postToolUse',
    action: 'fatal_error',
    decision: 'noop',
    reason: err.message,
  });
  process.stdout.write(JSON.stringify({}) + '\n');
  process.exit(0);
});

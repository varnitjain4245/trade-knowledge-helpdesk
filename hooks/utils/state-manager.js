'use strict';

/**
 * state-manager.js — Atomic read/write for workflow-state.json.
 *
 * Provides safe state mutations with backup/restore on failure to prevent
 * partial updates from corrupting workflow state.
 */

const fs = require('fs');
const path = require('path');
const { WORKFLOW_STATE_PATH, STATE_DIR, STAGES, DEPENDENCY_CHAIN } = require('./config');

/**
 * Default workflow state template.
 */
function createDefaultState() {
  const artifactVersions = {};
  for (const artifact of DEPENDENCY_CHAIN) {
    artifactVersions[artifact] = {
      version: 0,
      createdAt: null,
      updatedAt: null,
      stage: null,
      status: 'not_created',
      checksum: null,
      lastModifiedBySkill: null,
      approvalStatus: 'pending',
    };
  }

  return {
    currentStage: null,
    currentSkill: null,
    workflowStatus: 'not_started',
    iteration: 0,
    approvedStages: [],
    rejectedStages: [],
    staleArtifacts: [],
    waitingForApproval: null,
    lastUpdated: null,
    artifactVersions,
  };
}

/**
 * Read the workflow state from disk.
 * If the file doesn't exist, creates it with defaults and returns.
 *
 * @returns {Object} The parsed workflow state.
 */
function readState() {
  if (!fs.existsSync(WORKFLOW_STATE_PATH)) {
    const defaultState = createDefaultState();
    writeStateUnsafe(defaultState);
    return defaultState;
  }

  try {
    const raw = fs.readFileSync(WORKFLOW_STATE_PATH, 'utf8');
    return JSON.parse(raw);
  } catch (err) {
    // If the file is corrupted, back up and reset
    const backupPath = WORKFLOW_STATE_PATH + '.corrupted.' + Date.now();
    try {
      fs.copyFileSync(WORKFLOW_STATE_PATH, backupPath);
    } catch { /* ignore backup failure */ }
    const defaultState = createDefaultState();
    writeStateUnsafe(defaultState);
    return defaultState;
  }
}

/**
 * Write state to disk (no backup, used internally).
 * @param {Object} state
 */
function writeStateUnsafe(state) {
  if (!fs.existsSync(STATE_DIR)) {
    fs.mkdirSync(STATE_DIR, { recursive: true });
  }
  fs.writeFileSync(WORKFLOW_STATE_PATH, JSON.stringify(state, null, 2) + '\n', 'utf8');
}

/**
 * Atomically update the workflow state.
 *
 * Creates a backup before writing. On failure, restores the backup.
 * This prevents partial writes from corrupting state.
 *
 * @param {Function} mutator — A function that receives the current state
 *   object and mutates it in-place.
 * @returns {Object} The updated state.
 * @throws {Error} If the mutation or write fails.
 */
function updateState(mutator) {
  const state = readState();
  const backupPath = WORKFLOW_STATE_PATH + '.bak';

  // Back up current state
  try {
    fs.copyFileSync(WORKFLOW_STATE_PATH, backupPath);
  } catch {
    // First run — no file to back up
  }

  try {
    mutator(state);
    state.lastUpdated = new Date().toISOString();
    writeStateUnsafe(state);
    return state;
  } catch (err) {
    // Restore backup on failure
    try {
      if (fs.existsSync(backupPath)) {
        fs.copyFileSync(backupPath, WORKFLOW_STATE_PATH);
      }
    } catch { /* last resort — do nothing */ }
    throw err;
  }
}

module.exports = { readState, updateState, createDefaultState };

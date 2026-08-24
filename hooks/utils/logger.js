'use strict';

/**
 * logger.js — Structured JSON logging for workflow hooks.
 *
 * Writes one JSON object per line to hooks/logs/hook-events.jsonl.
 * Each log entry includes timestamp, hook type, stage, skill, artifact,
 * action, decision, reason, and duration.
 */

const fs = require('fs');
const path = require('path');
const { LOG_DIR, LOG_FILE } = require('./config');

/**
 * Ensure the log directory exists.
 */
function ensureLogDir() {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
}

/**
 * Write a structured log entry.
 *
 * @param {Object} entry
 * @param {string} entry.hook       — Hook type: 'preToolUse' | 'postToolUse' | 'stop'
 * @param {string} [entry.stage]    — Current workflow stage
 * @param {string} [entry.skill]    — Current skill being executed
 * @param {string} [entry.artifact] — Artifact being written/validated
 * @param {string} entry.action     — What the hook did: 'validate', 'deny', 'allow', 'update', etc.
 * @param {string} entry.decision   — Hook decision: 'allow', 'deny', 'continue', 'stop'
 * @param {string} [entry.reason]   — Human-readable reason for the decision
 * @param {number} [entry.duration] — Duration in milliseconds
 */
function log(entry) {
  ensureLogDir();
  const record = {
    timestamp: new Date().toISOString(),
    hook: entry.hook || 'unknown',
    stage: entry.stage || null,
    skill: entry.skill || null,
    artifact: entry.artifact || null,
    action: entry.action || 'unknown',
    decision: entry.decision || null,
    reason: entry.reason || null,
    duration: entry.duration || null,
  };
  try {
    fs.appendFileSync(LOG_FILE, JSON.stringify(record) + '\n', 'utf8');
  } catch (err) {
    // Logging should never crash the hook
    process.stderr.write(`[logger] Failed to write log: ${err.message}\n`);
  }
}

module.exports = { log, ensureLogDir };

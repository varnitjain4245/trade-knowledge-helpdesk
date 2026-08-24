'use strict';

/**
 * config.js — Central configuration for the workflow guard hooks.
 *
 * Contains all constants: stage definitions, skill locks, dependency graph,
 * artifact paths, and valid status transitions. Supports scope and sub-stages (3a, 3b, 5a, 5b, 5c).
 */

const path = require('path');

const WORKSPACE_ROOT = path.resolve(__dirname, '..', '..');

// Stage & sub-stage keys
const STAGES = [
  'requirement',
  'prd_review',
  'hld_backend',
  'hld_frontend',
  'hld_review',
  'lld_backend',
  'lld_frontend',
  'lld_consistency',
  'lld_review',
  'planning',
  'implementation',
  'review',
  'test',
];

const STAGE_INDEX = Object.fromEntries(STAGES.map((s, i) => [s, i]));

const STAGE_NAMES = {
  requirement:     'Stage 1 — Requirement Analysis',
  prd_review:      'Stage 2 — PRD Review',
  hld_backend:     'Stage 3a — High-Level Design (Backend)',
  hld_frontend:    'Stage 3b — High-Level Design (Frontend)',
  hld_review:      'Stage 4 — HLD Review',
  lld_backend:     'Stage 5a — Low-Level Design (Backend)',
  lld_frontend:    'Stage 5b — Low-Level Design (Frontend)',
  lld_consistency: 'Stage 5c — LLD Consistency Pass',
  lld_review:      'Stage 6 — LLD Review',
  planning:        'Stage 7 — Planning',
  implementation:  'Stage 8 — Implementation',
  review:          'Stage 9 — Code & Architecture Review',
  test:            'Stage 10 — QA Testing & Browser Validation',
};

// Skill mappings per sub-stage
const SKILL_MAP = {
  requirement:     ['prd-generator'],
  prd_review:      ['prd-reviewing'],
  hld_backend:     ['backend-hld-architect'],
  hld_frontend:    ['frontend-hld-designer'],
  hld_review:      ['hld-reviewer'],
  lld_backend:     ['backend-lld-architect'],
  lld_frontend:    ['frontend-lld-designer'],
  lld_consistency: [], // orchestrator pass
  lld_review:      ['frontend-lld-review', 'lld-reviewer'],
  planning:        ['edited-plan-skill'],
  implementation:  ['trading-platform-coding'],
  review:          ['code-reviewer'],
  test:            ['full-stack-test-suite'],
};

const ARTIFACT_DIR = path.join(WORKSPACE_ROOT, '.ai', 'artifacts');

const STAGE_ARTIFACTS = {
  requirement:     ['requirements.md'],
  prd_review:      ['prd-review.md'],
  hld_backend:     ['hld-backend.md', 'tech-stack.md'],
  hld_frontend:    ['hld-frontend.md', 'tech-stack.md'],
  hld_review:      ['hld-review.md'],
  lld_backend:     ['lld-backend.md'],
  lld_frontend:    ['lld-frontend.md'],
  lld_consistency: ['lld.md'],
  lld_review:      ['lld-review.md'],
  planning:        ['planning.md', 'tasks.json'],
  implementation:  [],
  review:          ['review.md'],
  test:            ['test-report.md', 'browser-report.md'],
};

const ARTIFACT_OWNER = {
  'requirements.md': 'requirement',
  'prd-review.md': 'prd_review',
  'hld-backend.md': 'hld_backend',
  'hld-frontend.md': 'hld_frontend',
  'tech-stack.md': 'hld_backend',
  'hld-review.md': 'hld_review',
  'lld-backend.md': 'lld_backend',
  'lld-frontend.md': 'lld_frontend',
  'lld.md': 'lld_consistency',
  'lld-review.md': 'lld_review',
  'planning.md': 'planning',
  'tasks.json': 'planning',
  'review.md': 'review',
  'test-report.md': 'test',
  'browser-report.md': 'test',
};

const DEPENDENCY_CHAIN = [
  'requirements.md',
  'prd-review.md',
  'hld-backend.md',
  'hld-frontend.md',
  'tech-stack.md',
  'hld-review.md',
  'lld-backend.md',
  'lld-frontend.md',
  'lld.md',
  'lld-review.md',
  'planning.md',
  'tasks.json',
  'review.md',
  'test-report.md',
  'browser-report.md',
];

function getDownstreamArtifacts(artifactName, scope = 'fullstack') {
  let chain = [...DEPENDENCY_CHAIN];
  
  if (artifactName === 'lld-backend.md' || artifactName === 'lld-frontend.md') {
    const idx = chain.indexOf(artifactName);
    return chain.slice(idx + 1);
  }

  const idx = chain.indexOf(artifactName);
  if (idx === -1) return [];
  return chain.slice(idx + 1);
}

const VALID_TRANSITIONS = {
  not_started: ['in_progress'],
  in_progress: ['completed', 'blocked', 'not_started'],
  completed:   ['stale', 'in_progress'],
  blocked:     ['in_progress', 'not_started'],
  stale:       ['in_progress', 'not_started'],
};

const VALID_APPROVAL_STATUSES = [
  'pending',
  'approved',
  'rejected',
  'stale',
];

const STATE_DIR = path.join(WORKSPACE_ROOT, '.ai', 'state');
const PROJECT_JSON_PATH = path.join(STATE_DIR, 'project.json');
const WORKFLOW_STATE_PATH = path.join(STATE_DIR, 'workflow-state.json');
const LOG_DIR = path.join(WORKSPACE_ROOT, 'hooks', 'logs');
const LOG_FILE = path.join(LOG_DIR, 'hook-events.jsonl');

const PROTECTED_PATHS = [
  ARTIFACT_DIR,
  STATE_DIR,
];

function isProtectedPath(absolutePath) {
  return PROTECTED_PATHS.some((p) => absolutePath.startsWith(p));
}

function getArtifactName(absolutePath) {
  if (!absolutePath.startsWith(ARTIFACT_DIR)) return null;
  return path.relative(ARTIFACT_DIR, absolutePath);
}

module.exports = {
  WORKSPACE_ROOT,
  STAGES,
  STAGE_INDEX,
  STAGE_NAMES,
  SKILL_MAP,
  ARTIFACT_DIR,
  STAGE_ARTIFACTS,
  ARTIFACT_OWNER,
  DEPENDENCY_CHAIN,
  getDownstreamArtifacts,
  VALID_TRANSITIONS,
  VALID_APPROVAL_STATUSES,
  STATE_DIR,
  PROJECT_JSON_PATH,
  WORKFLOW_STATE_PATH,
  LOG_DIR,
  LOG_FILE,
  PROTECTED_PATHS,
  isProtectedPath,
  getArtifactName,
};

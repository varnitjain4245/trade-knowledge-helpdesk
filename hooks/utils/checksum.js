'use strict';

/**
 * checksum.js — SHA-256 hashing utility for artifact integrity.
 *
 * Uses Node.js built-in crypto module. Zero external dependencies.
 */

const crypto = require('crypto');
const fs = require('fs');

/**
 * Compute SHA-256 hash of a string.
 * @param {string} content
 * @returns {string} Hex-encoded SHA-256 hash.
 */
function hashString(content) {
  return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
}

/**
 * Compute SHA-256 hash of a file on disk.
 * @param {string} filePath — Absolute path to the file.
 * @returns {string|null} Hex-encoded SHA-256 hash, or null if file doesn't exist.
 */
function hashFile(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return hashString(content);
  } catch {
    return null;
  }
}

module.exports = { hashString, hashFile };
